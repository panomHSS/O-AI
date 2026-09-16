"""D64 fail-closed Google OAuth deployment configuration."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import SecretStr

from app.contracts.google_oauth import GoogleOAuthCredentialSubject
from app.services.google_oauth_subjects import (
    GOOGLE_CALENDAR_OAUTH_AAD,
    GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH,
    GOOGLE_CALENDAR_OAUTH_SUBJECT,
)

GOOGLE_OAUTH_CONFIG_ERROR_MISSING_CLIENT_ID = "oauth_missing_client_id"
GOOGLE_OAUTH_CONFIG_ERROR_MISSING_CLIENT_SECRET = "oauth_missing_client_secret"
GOOGLE_OAUTH_CONFIG_ERROR_INVALID_REDIRECT_URI = "oauth_invalid_redirect_uri"
GOOGLE_OAUTH_CONFIG_ERROR_MISSING_ENCRYPTION_KEY = (
    "oauth_missing_encryption_key"
)
GOOGLE_OAUTH_CONFIG_ERROR_INVALID_ENCRYPTION_KEY = (
    "oauth_invalid_encryption_key"
)


class GoogleOAuthConfigError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleOAuthRuntimeConfig:
    client_id: str | None
    client_secret: SecretStr | None
    redirect_uri: str
    token_encryption_key: SecretStr | None
    subject: GoogleOAuthCredentialSubject = GOOGLE_CALENDAR_OAUTH_SUBJECT

    def __post_init__(self) -> None:
        if not isinstance(self.subject, GoogleOAuthCredentialSubject):
            raise TypeError("subject must be GoogleOAuthCredentialSubject.")
        self._validate_redirect_uri(
            self.redirect_uri,
            callback_path=self.subject.callback_path,
        )

    def require_client_id(self) -> str:
        value = self.client_id
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value) > 2048
        ):
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_MISSING_CLIENT_ID
            )
        return value

    def require_client_secret(self) -> SecretStr:
        value = self.client_secret
        if not isinstance(value, SecretStr):
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_MISSING_CLIENT_SECRET
            )
        raw = value.get_secret_value()
        if (
            not raw
            or len(raw.encode("utf-8")) > 8192
            or "\r" in raw
            or "\n" in raw
        ):
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_MISSING_CLIENT_SECRET
            )
        return value

    def require_encryption_key(self) -> SecretStr:
        value = self.token_encryption_key
        if not isinstance(value, SecretStr):
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_MISSING_ENCRYPTION_KEY
            )
        raw = value.get_secret_value()
        if not raw:
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_MISSING_ENCRYPTION_KEY
            )
        try:
            decoded = base64.b64decode(raw, validate=True)
        except Exception:
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_INVALID_ENCRYPTION_KEY
            ) from None
        if len(decoded) != 32:
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_INVALID_ENCRYPTION_KEY
            )
        return value

    @property
    def configuration_present(self) -> bool:
        """Report deployment provisioning without reading secret values."""
        return (
            isinstance(self.client_id, str)
            and bool(self.client_id.strip())
            and isinstance(self.client_secret, SecretStr)
            and isinstance(self.token_encryption_key, SecretStr)
        )

    def require_ready(self) -> None:
        self.require_client_id()
        self.require_client_secret()
        self.require_encryption_key()

    @staticmethod
    def _validate_redirect_uri(
        value: object,
        *,
        callback_path: str,
    ) -> None:
        if not isinstance(value, str) or not value or value != value.strip():
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_INVALID_REDIRECT_URI
            )
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.path != callback_path
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise GoogleOAuthConfigError(
                GOOGLE_OAUTH_CONFIG_ERROR_INVALID_REDIRECT_URI
            )
