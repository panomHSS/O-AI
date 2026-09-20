"""D63/D67 bounded authenticated read-only Google Calendar connector."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from pydantic import SecretStr

from app.contracts.google_calendar import GOOGLE_CALENDAR_MAX_WINDOW_DAYS

GOOGLE_CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)
GOOGLE_CALENDAR_TIMEOUT_SECONDS = 5.0
GOOGLE_CALENDAR_MAX_RESPONSE_BYTES = 64 * 1024
GOOGLE_CALENDAR_MAX_RESULTS = 10
GOOGLE_CALENDAR_WINDOW_DAYS = 7  # D63 compatibility constant; not used for D67 execution.
GOOGLE_CALENDAR_FIELDS = "nextPageToken,items(id,summary,status,start,end)"

GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL = "calendar_invalid_credential"
GOOGLE_CALENDAR_ERROR_INVALID_CLOCK = "calendar_invalid_clock"
GOOGLE_CALENDAR_ERROR_TIMEOUT = "calendar_connector_timeout"
GOOGLE_CALENDAR_ERROR_NETWORK = "calendar_connector_network_error"
GOOGLE_CALENDAR_ERROR_HTTP = "calendar_connector_http_error"
GOOGLE_CALENDAR_ERROR_AUTHENTICATION = "calendar_authentication_failed"
GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE = "calendar_response_too_large"
GOOGLE_CALENDAR_ERROR_INVALID_JSON = "calendar_invalid_json"
GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE = "calendar_invalid_response"
GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE = "calendar_credential_unavailable"
GOOGLE_CALENDAR_ERROR_INVALID_REQUEST = "calendar_invalid_request"

_ALLOWED_EVENT_STATUSES = frozenset({"confirmed", "tentative", "cancelled"})


class GoogleCalendarConnectorError(ValueError):
    """Safe Calendar connector error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleCalendarEvent:
    """Bounded normalized event data returned by the connector."""

    event_id: str
    summary: str
    status: str
    start: str
    end: str
    all_day: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "all_day": self.all_day,
            "end": self.end,
            "event_id": self.event_id,
            "start": self.start,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class GoogleCalendarReadResult:
    """One bounded page plus a non-authoritative more-results signal."""

    events: tuple[GoogleCalendarEvent, ...]
    truncated: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.events, tuple)
            or len(self.events) > GOOGLE_CALENDAR_MAX_RESULTS
            or any(not isinstance(event, GoogleCalendarEvent) for event in self.events)
            or type(self.truncated) is not bool
        ):
            raise ValueError("Invalid Google Calendar read result.")


class GoogleCalendarReader(Protocol):
    def list_upcoming_events(
        self,
        access_token: SecretStr,
        *,
        time_min: datetime,
        time_max: datetime,
    ) -> GoogleCalendarReadResult:
        ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects instead of granting a second network hop."""

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


Transport = Callable[[urllib.request.Request, float], object]


class GoogleCalendarClient:
    """Read exactly one approved bounded window from the primary calendar."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GOOGLE_CALENDAR_TIMEOUT_SECONDS,
        transport: Transport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = _open_without_redirects if transport is None else transport

    def list_upcoming_events(
        self,
        access_token: SecretStr,
        *,
        time_min: datetime,
        time_max: datetime,
    ) -> GoogleCalendarReadResult:
        if not isinstance(access_token, SecretStr):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL)
        token = access_token.get_secret_value()
        if (
            not token
            or len(token.encode("utf-8")) > 8192
            or "\r" in token
            or "\n" in token
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL)

        start, end = self._validated_window(time_min, time_max)
        query = urllib.parse.urlencode(
            (
                ("timeMin", self._rfc3339(start)),
                ("timeMax", self._rfc3339(end)),
                ("maxResults", str(GOOGLE_CALENDAR_MAX_RESULTS)),
                ("singleEvents", "true"),
                ("orderBy", "startTime"),
                ("showDeleted", "false"),
                ("fields", GOOGLE_CALENDAR_FIELDS),
            )
        )
        request = urllib.request.Request(
            f"{GOOGLE_CALENDAR_EVENTS_URL}?{query}",
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "O-AI-D67-Google-Calendar-Connector",
            },
        )

        try:
            response_context = self._transport(request, self._timeout_seconds)
            with response_context as response:
                status = getattr(response, "status", None)
                if status in (401, 403):
                    raise GoogleCalendarConnectorError(
                        GOOGLE_CALENDAR_ERROR_AUTHENTICATION
                    )
                if status != 200:
                    raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_HTTP)
                body = response.read(GOOGLE_CALENDAR_MAX_RESPONSE_BYTES + 1)
        except GoogleCalendarConnectorError:
            raise
        except (socket.timeout, TimeoutError):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_TIMEOUT) from None
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise GoogleCalendarConnectorError(
                    GOOGLE_CALENDAR_ERROR_AUTHENTICATION
                ) from None
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_HTTP) from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise GoogleCalendarConnectorError(
                    GOOGLE_CALENDAR_ERROR_TIMEOUT
                ) from None
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_NETWORK) from None
        except Exception:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_NETWORK) from None

        if not isinstance(body, bytes):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        if len(body) > GOOGLE_CALENDAR_MAX_RESPONSE_BYTES:
            raise GoogleCalendarConnectorError(
                GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_JSON) from None
        if not isinstance(payload, dict):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        items = payload.get("items", [])
        if not isinstance(items, list) or len(items) > GOOGLE_CALENDAR_MAX_RESULTS:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        next_page_token = payload.get("nextPageToken")
        if next_page_token is not None and (
            not isinstance(next_page_token, str)
            or not next_page_token
            or len(next_page_token.encode("utf-8")) > 4096
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        return GoogleCalendarReadResult(
            events=tuple(self._normalize_event(item) for item in items),
            truncated=next_page_token is not None,
        )

    @staticmethod
    def _validated_window(
        time_min: object,
        time_max: object,
    ) -> tuple[datetime, datetime]:
        if (
            not isinstance(time_min, datetime)
            or not isinstance(time_max, datetime)
            or time_min.tzinfo is None
            or time_min.utcoffset() is None
            or time_max.tzinfo is None
            or time_max.utcoffset() is None
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        start = time_min.astimezone(timezone.utc)
        end = time_max.astimezone(timezone.utc)
        elapsed = end - start
        if elapsed <= timedelta(0) or elapsed > timedelta(
            days=GOOGLE_CALENDAR_MAX_WINDOW_DAYS
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        return start, end

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")

    @classmethod
    def _normalize_event(cls, payload: object) -> GoogleCalendarEvent:
        if not isinstance(payload, dict):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        event_id = cls._bounded_string(payload.get("id"), max_bytes=1024)
        summary = cls._bounded_string(payload.get("summary"), max_bytes=1024)
        status = payload.get("status")
        if status not in _ALLOWED_EVENT_STATUSES:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        start, start_all_day, start_value = cls._normalize_boundary(payload.get("start"))
        end, end_all_day, end_value = cls._normalize_boundary(payload.get("end"))
        if start_all_day != end_all_day or end_value <= start_value:
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        return GoogleCalendarEvent(
            event_id=event_id,
            summary=summary,
            status=status,
            start=start,
            end=end,
            all_day=start_all_day,
        )

    @classmethod
    def _normalize_boundary(
        cls,
        value: object,
    ) -> tuple[str, bool, date | datetime]:
        if not isinstance(value, dict):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        date_value = value.get("date")
        datetime_value = value.get("dateTime")
        if (date_value is None) == (datetime_value is None):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

        if datetime_value is not None:
            raw = cls._bounded_string(datetime_value, max_bytes=128)
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                raise GoogleCalendarConnectorError(
                    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE
                ) from None
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
            return raw, False, parsed

        raw = cls._bounded_string(date_value, max_bytes=32)
        try:
            parsed_date = date.fromisoformat(raw)
        except ValueError:
            raise GoogleCalendarConnectorError(
                GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE
            ) from None
        return raw, True, parsed_date

    @staticmethod
    def _bounded_string(value: object, *, max_bytes: int) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > max_bytes
        ):
            raise GoogleCalendarConnectorError(GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        return value
