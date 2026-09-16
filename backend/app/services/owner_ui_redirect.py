"""D66 fixed loopback owner-UI redirect boundary."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL = "owner_ui_invalid_base_url"
OWNER_UI_INTEGRATIONS_PATH = "/settings/integrations"


class OwnerUIRedirectConfigError(ValueError):
    """Safe owner-UI redirect configuration error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OwnerUIRedirectConfig:
    """One deployment-controlled loopback UI origin; never caller-selected."""

    base_url: str = "http://localhost:3000"

    def __post_init__(self) -> None:
        self._validate_base_url(self.base_url)

    def google_calendar_connected_url(self) -> str:
        return self._url((("google_calendar", "connected"),))

    def google_calendar_error_url(self, reason_code: str) -> str:
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or reason_code != reason_code.strip()
            or len(reason_code) > 128
            or not reason_code.replace("_", "").isalnum()
        ):
            reason_code = "oauth_unavailable"
        return self._url(
            (
                ("google_calendar", "error"),
                ("reason", reason_code),
            )
        )

    def gmail_connected_url(self) -> str:
        return self._url((("gmail", "connected"),))

    def gmail_error_url(self, reason_code: str) -> str:
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or reason_code != reason_code.strip()
            or len(reason_code) > 128
            or not reason_code.replace("_", "").isalnum()
        ):
            reason_code = "oauth_unavailable"
        return self._url(
            (
                ("gmail", "error"),
                ("reason", reason_code),
            )
        )

    def _url(self, query: tuple[tuple[str, str], ...]) -> str:
        return (
            f"{self.base_url.rstrip('/')}{OWNER_UI_INTEGRATIONS_PATH}"
            f"?{urlencode(query)}"
        )

    @staticmethod
    def _validate_base_url(value: object) -> None:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value) > 2048
        ):
            raise OwnerUIRedirectConfigError(
                OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL
            )

        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError:
            raise OwnerUIRedirectConfigError(
                OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL
            ) from None

        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or port is None
            or not (1 <= port <= 65535)
        ):
            raise OwnerUIRedirectConfigError(
                OWNER_UI_REDIRECT_ERROR_INVALID_BASE_URL
            )
