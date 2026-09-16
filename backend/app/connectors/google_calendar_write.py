"""D74 bounded Google Calendar create-event transport."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr

from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID,
    GoogleCalendarEventDraft,
    GoogleCalendarEventTarget,
)

GOOGLE_CALENDAR_CREATE_EVENT_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_CALENDAR_WRITE_TIMEOUT_SECONDS = 5.0
GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES = 64 * 1024
GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST = "calendar_create_invalid_request"
GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED = "calendar_create_provider_rejected"
GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE = "calendar_create_indeterminate"


class GoogleCalendarWriteError(RuntimeError):
    def __init__(self, code: str, *, indeterminate: bool) -> None:
        self.code = code
        self.indeterminate = indeterminate
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleCalendarCreateResult:
    event_id: str


class GoogleCalendarEventCreator(Protocol):
    def create_event(self, credential: SecretStr, *, event: GoogleCalendarEventDraft) -> GoogleCalendarCreateResult: ...


class GoogleCalendarWriteTransport(Protocol):
    def __call__(self, request: urllib.request.Request, timeout_seconds: float) -> object: ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects_or_proxies(request: urllib.request.Request, timeout_seconds: float):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


class GoogleCalendarWriteClient:
    """Perform exactly one fixed primary-calendar Events.insert call."""

    def __init__(self, *, timeout_seconds: float = GOOGLE_CALENDAR_WRITE_TIMEOUT_SECONDS, transport: GoogleCalendarWriteTransport | None = None) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or _open_without_redirects_or_proxies

    def create_event(self, credential: SecretStr, *, event: GoogleCalendarEventDraft) -> GoogleCalendarCreateResult:
        if not isinstance(credential, SecretStr):
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST, indeterminate=False)
        token = credential.get_secret_value()
        if not token or "\r" in token or "\n" in token:
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST, indeterminate=False)
        if not isinstance(event, GoogleCalendarEventDraft) or event.calendar_id != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID:
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST, indeterminate=False)

        payload: dict[str, object] = {
            "summary": event.summary,
            "start": {"dateTime": event.start.isoformat(timespec="microseconds")},
            "end": {"dateTime": event.end.isoformat(timespec="microseconds")},
        }
        if event.description is not None:
            payload["description"] = event.description
        if event.location is not None:
            payload["location"] = event.location
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            GOOGLE_CALENDAR_CREATE_EVENT_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "O-AI-D74-Google-Calendar",
            },
        )
        raw = self._perform(request)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True) from None
        if not isinstance(payload, dict):
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True)
        try:
            target = GoogleCalendarEventTarget(event_id=payload.get("id"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True) from None
        return GoogleCalendarCreateResult(event_id=target.event_id)

    def _perform(self, request: urllib.request.Request) -> bytes:
        try:
            context = self._transport(request, self._timeout_seconds)
            with context as response:
                status = getattr(response, "status", None)
                if status != 200:
                    self._raise_status(status)
                body = response.read(GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES + 1)
        except GoogleCalendarWriteError:
            raise
        except urllib.error.HTTPError as error:
            self._raise_status(error.code)
        except (socket.timeout, TimeoutError, urllib.error.URLError):
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True) from None
        except Exception:
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True) from None
        if not isinstance(body, bytes) or len(body) > GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES:
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True)
        return body

    @staticmethod
    def _raise_status(status: object) -> None:
        if isinstance(status, int) and not isinstance(status, bool) and 400 <= status < 500 and status != 408:
            raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED, indeterminate=False)
        raise GoogleCalendarWriteError(GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE, indeterminate=True)


__all__ = [
    "GOOGLE_CALENDAR_CREATE_EVENT_URL",
    "GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE",
    "GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST",
    "GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED",
    "GoogleCalendarCreateResult",
    "GoogleCalendarEventCreator",
    "GoogleCalendarWriteClient",
    "GoogleCalendarWriteError",
]
