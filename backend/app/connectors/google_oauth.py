"""D64 bounded Google OAuth 2.0 web-server transport."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr

from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SCOPE
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig

GOOGLE_OAUTH_AUTHORIZATION_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_REVOCATION_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_OAUTH_TIMEOUT_SECONDS = 5.0
GOOGLE_OAUTH_MAX_RESPONSE_BYTES = 64 * 1024

GOOGLE_OAUTH_ERROR_INVALID_INPUT = "google_oauth_invalid_input"
GOOGLE_OAUTH_ERROR_TIMEOUT = "google_oauth_timeout"
GOOGLE_OAUTH_ERROR_NETWORK = "google_oauth_network_error"
GOOGLE_OAUTH_ERROR_HTTP = "google_oauth_http_error"
GOOGLE_OAUTH_ERROR_INVALID_GRANT = "google_oauth_invalid_grant"
GOOGLE_OAUTH_ERROR_INVALID_JSON = "google_oauth_invalid_json"
GOOGLE_OAUTH_ERROR_INVALID_RESPONSE = "google_oauth_invalid_response"
GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH = "google_oauth_scope_mismatch"
GOOGLE_OAUTH_ERROR_RESPONSE_TOO_LARGE = "google_oauth_response_too_large"


class GoogleOAuthClientError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleOAuthTokenResponse:
    access_token: SecretStr
    expires_in: int
    token_type: str
    scopes: tuple[str, ...]
    refresh_token: SecretStr | None = None
    refresh_token_expires_in: int | None = None


class GoogleOAuthTransport(Protocol):
    def __call__(
        self,
        request: urllib.request.Request,
        timeout_seconds: float,
    ) -> object:
        ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects(
    request: urllib.request.Request,
    timeout_seconds: float,
):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


class GoogleOAuthClient:
    """Perform exact Google OAuth authorization/token/revocation operations."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GOOGLE_OAUTH_TIMEOUT_SECONDS,
        transport: GoogleOAuthTransport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or _open_without_redirects

    def build_authorization_url(
        self,
        config: GoogleOAuthRuntimeConfig,
        *,
        state: str,
    ) -> str:
        config.require_ready()
        state = self._bounded_text(state, max_bytes=512)
        query = urllib.parse.urlencode(
            (
                ("response_type", "code"),
                ("client_id", config.require_client_id()),
                ("redirect_uri", config.redirect_uri),
                ("scope", GOOGLE_CALENDAR_CREDENTIAL_SCOPE),
                ("access_type", "offline"),
                ("prompt", "consent"),
                ("state", state),
            )
        )
        return f"{GOOGLE_OAUTH_AUTHORIZATION_URL}?{query}"

    def exchange_authorization_code(
        self,
        config: GoogleOAuthRuntimeConfig,
        *,
        code: str,
    ) -> GoogleOAuthTokenResponse:
        code = self._bounded_text(code, max_bytes=8192)
        response = self._post_json(
            GOOGLE_OAUTH_TOKEN_URL,
            (
                ("code", code),
                ("client_id", config.require_client_id()),
                (
                    "client_secret",
                    config.require_client_secret().get_secret_value(),
                ),
                ("redirect_uri", config.redirect_uri),
                ("grant_type", "authorization_code"),
            ),
        )
        return self._token_response(
            response,
            require_scope=True,
        )

    def refresh_access_token(
        self,
        config: GoogleOAuthRuntimeConfig,
        *,
        refresh_token: SecretStr,
    ) -> GoogleOAuthTokenResponse:
        token = self._bounded_secret(refresh_token)
        response = self._post_json(
            GOOGLE_OAUTH_TOKEN_URL,
            (
                ("client_id", config.require_client_id()),
                (
                    "client_secret",
                    config.require_client_secret().get_secret_value(),
                ),
                ("refresh_token", token),
                ("grant_type", "refresh_token"),
            ),
        )
        return self._token_response(
            response,
            require_scope=False,
        )

    def revoke_refresh_token(
        self,
        *,
        refresh_token: SecretStr,
    ) -> None:
        token = self._bounded_secret(refresh_token)
        self._post_status(
            GOOGLE_OAUTH_REVOCATION_URL,
            (("token", token),),
        )

    def _post_json(
        self,
        url: str,
        fields: tuple[tuple[str, str], ...],
    ) -> dict[str, object]:
        body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "O-AI-D64-Google-OAuth",
            },
        )
        raw = self._perform(request, expect_json=True)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_JSON
            ) from None
        if not isinstance(payload, dict):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_RESPONSE
            )
        return payload

    def _post_status(
        self,
        url: str,
        fields: tuple[tuple[str, str], ...],
    ) -> None:
        body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "O-AI-D64-Google-OAuth",
            },
        )
        self._perform(request, expect_json=False)

    def _perform(
        self,
        request: urllib.request.Request,
        *,
        expect_json: bool,
    ) -> bytes:
        try:
            response_context = self._transport(
                request,
                self._timeout_seconds,
            )
            with response_context as response:
                status = getattr(response, "status", None)
                if status != 200:
                    raise GoogleOAuthClientError(
                        GOOGLE_OAUTH_ERROR_HTTP
                    )
                body = response.read(
                    GOOGLE_OAUTH_MAX_RESPONSE_BYTES + 1
                )
        except GoogleOAuthClientError:
            raise
        except urllib.error.HTTPError as error:
            self._raise_http_error(error)
        except (socket.timeout, TimeoutError):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_TIMEOUT
            ) from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise GoogleOAuthClientError(
                    GOOGLE_OAUTH_ERROR_TIMEOUT
                ) from None
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_NETWORK
            ) from None
        except Exception:
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_NETWORK
            ) from None

        if not isinstance(body, bytes):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_RESPONSE
            )
        if len(body) > GOOGLE_OAUTH_MAX_RESPONSE_BYTES:
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_RESPONSE_TOO_LARGE
            )
        if not expect_json and body:
            # Revocation response content is intentionally ignored.
            return b""
        return body

    def _raise_http_error(self, error: urllib.error.HTTPError) -> None:
        try:
            raw = error.read(GOOGLE_OAUTH_MAX_RESPONSE_BYTES + 1)
        except Exception:
            raw = b""
        if len(raw) <= GOOGLE_OAUTH_MAX_RESPONSE_BYTES:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = None
            if (
                isinstance(payload, dict)
                and payload.get("error") == "invalid_grant"
            ):
                raise GoogleOAuthClientError(
                    GOOGLE_OAUTH_ERROR_INVALID_GRANT
                ) from None
        raise GoogleOAuthClientError(
            GOOGLE_OAUTH_ERROR_HTTP
        ) from None

    def _token_response(
        self,
        payload: dict[str, object],
        *,
        require_scope: bool,
    ) -> GoogleOAuthTokenResponse:
        access_token = self._secret_field(payload.get("access_token"))
        expires_in = self._positive_int(
            payload.get("expires_in"),
            maximum=86_400,
        )
        if payload.get("token_type") != "Bearer":
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_RESPONSE
            )

        raw_scope = payload.get("scope")
        scopes: tuple[str, ...]
        if raw_scope is None and not require_scope:
            scopes = ()
        elif isinstance(raw_scope, str) and raw_scope:
            scopes = tuple(sorted(set(raw_scope.split())))
            if scopes != (GOOGLE_CALENDAR_CREDENTIAL_SCOPE,):
                raise GoogleOAuthClientError(
                    GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH
                )
        else:
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH
            )

        refresh_token = None
        if payload.get("refresh_token") is not None:
            refresh_token = self._secret_field(
                payload.get("refresh_token")
            )

        refresh_expires = None
        if payload.get("refresh_token_expires_in") is not None:
            refresh_expires = self._positive_int(
                payload.get("refresh_token_expires_in"),
                maximum=315_360_000,
            )

        return GoogleOAuthTokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            token_type="Bearer",
            scopes=scopes,
            refresh_token=refresh_token,
            refresh_token_expires_in=refresh_expires,
        )

    @staticmethod
    def _positive_int(value: object, *, maximum: int) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            or value > maximum
        ):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_RESPONSE
            )
        return value

    @classmethod
    def _secret_field(cls, value: object) -> SecretStr:
        if not isinstance(value, str):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_RESPONSE
            )
        cls._bounded_text(value, max_bytes=8192)
        return SecretStr(value)

    @staticmethod
    def _bounded_text(value: object, *, max_bytes: int) -> str:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value.encode("utf-8")) > max_bytes
            or "\r" in value
            or "\n" in value
        ):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_INPUT
            )
        return value

    @classmethod
    def _bounded_secret(cls, value: SecretStr) -> str:
        if not isinstance(value, SecretStr):
            raise GoogleOAuthClientError(
                GOOGLE_OAUTH_ERROR_INVALID_INPUT
            )
        return cls._bounded_text(
            value.get_secret_value(),
            max_bytes=8192,
        )
