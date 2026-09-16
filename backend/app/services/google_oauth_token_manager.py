"""D64 execution-time Google OAuth access-token manager."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.connectors.google_oauth import (
    GOOGLE_OAUTH_ERROR_INVALID_GRANT,
    GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH,
    GoogleOAuthClient,
    GoogleOAuthClientError,
)
from app.repositories.oauth_credentials import OAuthCredentialRepository
from app.services.google_oauth_config import (
    GoogleOAuthConfigError,
    GoogleOAuthRuntimeConfig,
)
from app.services.oauth_token_cipher import (
    OAuthTokenCipher,
    OAuthTokenCipherError,
)

GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED = "oauth_token_not_connected"
GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED = (
    "oauth_token_reauthorization_required"
)
GOOGLE_OAUTH_TOKEN_ERROR_REFRESH_FAILED = "oauth_token_refresh_failed"
GOOGLE_OAUTH_TOKEN_ERROR_DECRYPTION_FAILED = (
    "oauth_token_decryption_failed"
)
GOOGLE_OAUTH_TOKEN_ERROR_CONFIGURATION = "oauth_token_configuration_unavailable"

ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 60


class GoogleOAuthTokenManagerError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GoogleOAuthTokenManager:
    """Keep access tokens in memory and refresh only on credential resolution."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        config: GoogleOAuthRuntimeConfig,
        client: GoogleOAuthClient,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._config = config
        self._subject = config.subject
        self._client = client
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._cached_access_token: SecretStr | None = None
        self._cached_expires_at: datetime | None = None

    def resolve_access_token(self) -> SecretStr:
        with self._lock:
            now = self._now()
            cached = self._cached_access_token
            expires_at = self._cached_expires_at
            if (
                cached is not None
                and expires_at is not None
                and expires_at
                > now + timedelta(seconds=ACCESS_TOKEN_REFRESH_SKEW_SECONDS)
            ):
                return cached

            try:
                self._config.require_ready()
                cipher = OAuthTokenCipher.from_base64_key(
                    self._config.require_encryption_key()
                )
            except (GoogleOAuthConfigError, OAuthTokenCipherError):
                raise GoogleOAuthTokenManagerError(
                    GOOGLE_OAUTH_TOKEN_ERROR_CONFIGURATION
                ) from None

            session = self._session_factory()
            repository = OAuthCredentialRepository(session)
            try:
                record = repository.get(
                    self._subject.profile_id
                )
                if record is None:
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_NOT_CONNECTED
                    )
                if record.status != "active":
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED
                    )
                if not self._record_identity_matches(record):
                    repository.mark_reauthorization_required(
                        self._subject.profile_id,
                        now=now,
                    )
                    repository.commit()
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED
                    )

                refresh_expires = self._aware(
                    record.refresh_token_expires_at
                )
                if (
                    refresh_expires is not None
                    and refresh_expires <= now
                ):
                    repository.mark_reauthorization_required(
                        self._subject.profile_id,
                        now=now,
                    )
                    repository.commit()
                    self._clear_cache_unlocked()
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED
                    )

                try:
                    refresh_token = cipher.decrypt(
                        record.encrypted_refresh_token,
                        record.encryption_nonce,
                        aad=self._subject.aad,
                    )
                except OAuthTokenCipherError:
                    self._clear_cache_unlocked()
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_DECRYPTION_FAILED
                    ) from None

                try:
                    response = self._client.refresh_access_token(
                        self._config,
                        refresh_token=refresh_token,
                    )
                except GoogleOAuthClientError as error:
                    if error.code in {
                        GOOGLE_OAUTH_ERROR_INVALID_GRANT,
                        GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH,
                    }:
                        repository.mark_reauthorization_required(
                            self._subject.profile_id,
                            now=now,
                        )
                        repository.commit()
                        self._clear_cache_unlocked()
                        raise GoogleOAuthTokenManagerError(
                            GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED
                        ) from None
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_REFRESH_FAILED
                    ) from None

                if response.scopes not in {
                    (),
                    (self._subject.scope,),
                }:
                    repository.mark_reauthorization_required(
                        self._subject.profile_id,
                        now=now,
                    )
                    repository.commit()
                    self._clear_cache_unlocked()
                    raise GoogleOAuthTokenManagerError(
                        GOOGLE_OAUTH_TOKEN_ERROR_REAUTHORIZATION_REQUIRED
                    )

                if response.refresh_token is not None:
                    encrypted = cipher.encrypt(
                        response.refresh_token,
                        aad=self._subject.aad,
                    )
                    refresh_token_expires_at = (
                        now
                        + timedelta(
                            seconds=response.refresh_token_expires_in
                        )
                        if response.refresh_token_expires_in is not None
                        else None
                    )
                    repository.save_active(
                        profile_id=self._subject.profile_id,
                        provider_id=self._subject.provider_id,
                        plugin_id=self._subject.plugin_id,
                        plugin_version=self._subject.plugin_version,
                        capability_name=self._subject.capability_name,
                        encrypted_refresh_token=encrypted.ciphertext,
                        encryption_nonce=encrypted.nonce,
                        cipher_version=encrypted.cipher_version,
                        granted_scopes=self._subject.scope,
                        refresh_token_expires_at=refresh_token_expires_at,
                        now=now,
                    )
                    repository.commit()

                self._cached_access_token = response.access_token
                self._cached_expires_at = (
                    now + timedelta(seconds=response.expires_in)
                )
                return response.access_token
            except GoogleOAuthTokenManagerError:
                repository.rollback()
                raise
            except Exception:
                repository.rollback()
                raise GoogleOAuthTokenManagerError(
                    GOOGLE_OAUTH_TOKEN_ERROR_REFRESH_FAILED
                ) from None
            finally:
                session.close()

    def seed_access_token(
        self,
        token: SecretStr,
        *,
        expires_in: int,
    ) -> None:
        if (
            not isinstance(token, SecretStr)
            or not token.get_secret_value()
            or isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or expires_in < 1
        ):
            raise GoogleOAuthTokenManagerError(
                GOOGLE_OAUTH_TOKEN_ERROR_REFRESH_FAILED
            )
        with self._lock:
            now = self._now()
            self._cached_access_token = token
            self._cached_expires_at = now + timedelta(seconds=expires_in)

    def clear_cache(self) -> None:
        with self._lock:
            self._clear_cache_unlocked()

    def _clear_cache_unlocked(self) -> None:
        self._cached_access_token = None
        self._cached_expires_at = None

    def _now(self) -> datetime:
        value = self._clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise GoogleOAuthTokenManagerError(
                GOOGLE_OAUTH_TOKEN_ERROR_REFRESH_FAILED
            )
        return value.astimezone(timezone.utc)

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _record_identity_matches(self, record) -> bool:
        return (
            record.provider_id == self._subject.provider_id
            and record.plugin_id == self._subject.plugin_id
            and record.plugin_version
            == self._subject.plugin_version
            and record.capability_name
            == self._subject.capability_name
            and record.granted_scopes
            == self._subject.scope
            and record.cipher_version == "aesgcm-v1"
        )
