"""D64 explicit owner-controlled Google OAuth lifecycle service."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.connectors.google_oauth import (
    GoogleOAuthClient,
    GoogleOAuthClientError,
)
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CAPABILITY_NAME,
    GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
    GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_PLUGIN_ID,
    GOOGLE_CALENDAR_PLUGIN_VERSION,
)
from app.repositories.oauth_credentials import OAuthCredentialRepository
from app.services.google_oauth_config import (
    GOOGLE_CALENDAR_OAUTH_AAD,
    GoogleOAuthConfigError,
    GoogleOAuthRuntimeConfig,
)
from app.services.google_oauth_token_manager import GoogleOAuthTokenManager
from app.services.oauth_flow_state import (
    OAuthFlowStateError,
    OAuthFlowStateStore,
)
from app.services.oauth_token_cipher import (
    EncryptedOAuthSecret,
    OAuthTokenCipher,
    OAuthTokenCipherError,
)

OAUTH_LIFECYCLE_ERROR_CONFIGURATION = "oauth_configuration_unavailable"
OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH = "oauth_state_mismatch"
OAUTH_LIFECYCLE_ERROR_STATE_INVALID = "oauth_state_invalid"
OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED = "oauth_consent_denied"
OAUTH_LIFECYCLE_ERROR_INVALID_CODE = "oauth_invalid_code"
OAUTH_LIFECYCLE_ERROR_EXCHANGE_FAILED = "oauth_exchange_failed"
OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING = (
    "oauth_refresh_token_missing"
)
OAUTH_LIFECYCLE_ERROR_PERSISTENCE = "oauth_persistence_failed"
OAUTH_LIFECYCLE_ERROR_REVOCATION = "oauth_revocation_failed"


class GoogleOAuthLifecycleError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleOAuthStatus:
    connected: bool
    status: str
    scope: str


class GoogleOAuthLifecycleService:
    """Explicit connect/status/disconnect lifecycle without execution authority."""

    def __init__(
        self,
        *,
        repository: OAuthCredentialRepository,
        config: GoogleOAuthRuntimeConfig,
        client: GoogleOAuthClient,
        flow_state_store: OAuthFlowStateStore,
        token_manager: GoogleOAuthTokenManager,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._config = config
        self._client = client
        self._flow_state_store = flow_state_store
        self._token_manager = token_manager
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def start_authorization(self) -> tuple[str, str]:
        try:
            self._config.require_ready()
            state = self._flow_state_store.issue()
            url = self._client.build_authorization_url(
                self._config,
                state=state,
            )
            return url, state
        except GoogleOAuthConfigError:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_CONFIGURATION
            ) from None
        except OAuthFlowStateError:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_STATE_INVALID
            ) from None

    def complete_authorization(
        self,
        *,
        query_state: str,
        cookie_state: str | None,
        code: str | None,
        oauth_error: str | None,
    ) -> GoogleOAuthStatus:
        if (
            not isinstance(cookie_state, str)
            or not isinstance(query_state, str)
            or not hmac.compare_digest(query_state, cookie_state)
        ):
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH
            )

        try:
            self._flow_state_store.consume(query_state)
        except OAuthFlowStateError:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_STATE_INVALID
            ) from None

        if oauth_error is not None:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED
            )
        if (
            not isinstance(code, str)
            or not code
            or code != code.strip()
            or len(code.encode("utf-8")) > 8192
            or "\r" in code
            or "\n" in code
        ):
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_INVALID_CODE
            )

        try:
            self._config.require_ready()
            cipher = OAuthTokenCipher.from_base64_key(
                self._config.require_encryption_key()
            )
            response = self._client.exchange_authorization_code(
                self._config,
                code=code,
            )
        except (GoogleOAuthConfigError, OAuthTokenCipherError):
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_CONFIGURATION
            ) from None
        except GoogleOAuthClientError:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_EXCHANGE_FAILED
            ) from None

        now = self._now()
        existing = self._repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )

        refresh_token = response.refresh_token
        refresh_token_expires_at = None
        if refresh_token is not None:
            try:
                encrypted = cipher.encrypt(
                    refresh_token,
                    aad=GOOGLE_CALENDAR_OAUTH_AAD,
                )
            except OAuthTokenCipherError:
                raise GoogleOAuthLifecycleError(
                    OAUTH_LIFECYCLE_ERROR_PERSISTENCE
                ) from None
            if response.refresh_token_expires_in is not None:
                refresh_token_expires_at = (
                    now
                    + timedelta(
                        seconds=response.refresh_token_expires_in
                    )
                )
        elif (
            existing is not None
            and existing.status == "active"
            and existing.provider_id == GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID
            and existing.plugin_id == GOOGLE_CALENDAR_PLUGIN_ID
            and existing.plugin_version == GOOGLE_CALENDAR_PLUGIN_VERSION
            and existing.capability_name == GOOGLE_CALENDAR_CAPABILITY_NAME
            and existing.granted_scopes == GOOGLE_CALENDAR_CREDENTIAL_SCOPE
            and existing.cipher_version == "aesgcm-v1"
        ):
            encrypted = EncryptedOAuthSecret(
                ciphertext=existing.encrypted_refresh_token,
                nonce=existing.encryption_nonce,
                cipher_version=existing.cipher_version,
            )
            refresh_token_expires_at = (
                existing.refresh_token_expires_at
            )
        else:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING
            )

        try:
            self._repository.save_active(
                profile_id=GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID,
                provider_id=GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID,
                plugin_id=GOOGLE_CALENDAR_PLUGIN_ID,
                plugin_version=GOOGLE_CALENDAR_PLUGIN_VERSION,
                capability_name=GOOGLE_CALENDAR_CAPABILITY_NAME,
                encrypted_refresh_token=encrypted.ciphertext,
                encryption_nonce=encrypted.nonce,
                cipher_version=encrypted.cipher_version,
                granted_scopes=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
                refresh_token_expires_at=refresh_token_expires_at,
                now=now,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_PERSISTENCE
            ) from None

        self._token_manager.seed_access_token(
            response.access_token,
            expires_in=response.expires_in,
        )
        return self.status()

    def status(self) -> GoogleOAuthStatus:
        record = self._repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        if record is None:
            return GoogleOAuthStatus(
                connected=False,
                status="disconnected",
                scope=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            )
        connected = record.status == "active"
        return GoogleOAuthStatus(
            connected=connected,
            status=record.status,
            scope=GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
        )

    def disconnect(self) -> GoogleOAuthStatus:
        record = self._repository.get(
            GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
        )
        if record is None:
            self._token_manager.clear_cache()
            return self.status()

        try:
            self._config.require_ready()
            cipher = OAuthTokenCipher.from_base64_key(
                self._config.require_encryption_key()
            )
            refresh_token = cipher.decrypt(
                record.encrypted_refresh_token,
                record.encryption_nonce,
                aad=GOOGLE_CALENDAR_OAUTH_AAD,
            )
            self._client.revoke_refresh_token(
                refresh_token=refresh_token
            )
        except (GoogleOAuthConfigError, OAuthTokenCipherError):
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_CONFIGURATION
            ) from None
        except GoogleOAuthClientError:
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_REVOCATION
            ) from None

        try:
            self._repository.delete(
                GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_PERSISTENCE
            ) from None

        self._token_manager.clear_cache()
        return self.status()

    def _now(self) -> datetime:
        value = self._clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise GoogleOAuthLifecycleError(
                OAUTH_LIFECYCLE_ERROR_PERSISTENCE
            )
        return value.astimezone(timezone.utc)
