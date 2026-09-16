"""D74/D75 bounded Google Calendar event mutation transport."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr

from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
)

GOOGLE_CALENDAR_CREATE_EVENT_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)
_GOOGLE_CALENDAR_EVENT_URL_PREFIX = GOOGLE_CALENDAR_CREATE_EVENT_URL + "/"
GOOGLE_CALENDAR_WRITE_TIMEOUT_SECONDS = 5.0
GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES = 64 * 1024

GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST = "calendar_create_invalid_request"
GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED = "calendar_create_provider_rejected"
GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE = "calendar_create_indeterminate"

GOOGLE_CALENDAR_UPDATE_ERROR_INVALID_REQUEST = "calendar_update_invalid_request"
GOOGLE_CALENDAR_UPDATE_ERROR_PROVIDER_REJECTED = "calendar_update_provider_rejected"
GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE = "calendar_update_indeterminate"

GOOGLE_CALENDAR_DELETE_ERROR_INVALID_REQUEST = "calendar_delete_invalid_request"
GOOGLE_CALENDAR_DELETE_ERROR_PROVIDER_REJECTED = "calendar_delete_provider_rejected"
GOOGLE_CALENDAR_DELETE_ERROR_INDETERMINATE = "calendar_delete_indeterminate"


class GoogleCalendarWriteError(RuntimeError):
    def __init__(self, code: str, *, indeterminate: bool) -> None:
        self.code = code
        self.indeterminate = indeterminate
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GoogleCalendarCreateResult:
    event_id: str


@dataclass(frozen=True, slots=True)
class GoogleCalendarUpdateResult:
    event_id: str


@dataclass(frozen=True, slots=True)
class GoogleCalendarDeleteResult:
    event_id: str


class GoogleCalendarEventCreator(Protocol):
    def create_event(
        self,
        credential: SecretStr,
        *,
        event: GoogleCalendarEventDraft,
    ) -> GoogleCalendarCreateResult: ...


class GoogleCalendarEventUpdater(Protocol):
    def update_event(
        self,
        credential: SecretStr,
        *,
        target: GoogleCalendarEventTarget,
        changes: GoogleCalendarEventPatch,
    ) -> GoogleCalendarUpdateResult: ...


class GoogleCalendarEventDeleter(Protocol):
    def delete_event(
        self,
        credential: SecretStr,
        *,
        target: GoogleCalendarEventTarget,
    ) -> GoogleCalendarDeleteResult: ...


class GoogleCalendarWriteTransport(Protocol):
    def __call__(
        self,
        request: urllib.request.Request,
        timeout_seconds: float,
    ) -> object: ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects_or_proxies(
    request: urllib.request.Request,
    timeout_seconds: float,
):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


def _event_url(target: GoogleCalendarEventTarget) -> str:
    return _GOOGLE_CALENDAR_EVENT_URL_PREFIX + urllib.parse.quote(
        target.event_id,
        safe="",
    )


class GoogleCalendarWriteClient:
    """Perform one bounded primary-calendar mutation attempt per call."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GOOGLE_CALENDAR_WRITE_TIMEOUT_SECONDS,
        transport: GoogleCalendarWriteTransport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or _open_without_redirects_or_proxies

    def create_event(
        self,
        credential: SecretStr,
        *,
        event: GoogleCalendarEventDraft,
    ) -> GoogleCalendarCreateResult:
        token = self._token(
            credential,
            GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST,
        )
        if (
            not isinstance(event, GoogleCalendarEventDraft)
            or event.calendar_id != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID
        ):
            raise GoogleCalendarWriteError(
                GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST,
                indeterminate=False,
            )

        payload: dict[str, object] = {
            "summary": event.summary,
            "start": {"dateTime": event.start.isoformat(timespec="microseconds")},
            "end": {"dateTime": event.end.isoformat(timespec="microseconds")},
        }
        if event.description is not None:
            payload["description"] = event.description
        if event.location is not None:
            payload["location"] = event.location
        request = self._json_request(
            GOOGLE_CALENDAR_CREATE_EVENT_URL,
            method="POST",
            token=token,
            payload=payload,
            user_agent="O-AI-D74-Google-Calendar",
        )
        raw = self._perform(
            request,
            success_statuses=(200,),
            provider_rejected_code=GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED,
            indeterminate_code=GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE,
        )
        event_id = self._response_event_id(
            raw,
            indeterminate_code=GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE,
        )
        return GoogleCalendarCreateResult(event_id=event_id)

    def update_event(
        self,
        credential: SecretStr,
        *,
        target: GoogleCalendarEventTarget,
        changes: GoogleCalendarEventPatch,
    ) -> GoogleCalendarUpdateResult:
        token = self._token(
            credential,
            GOOGLE_CALENDAR_UPDATE_ERROR_INVALID_REQUEST,
        )
        if (
            not isinstance(target, GoogleCalendarEventTarget)
            or target.calendar_id != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID
            or not isinstance(changes, GoogleCalendarEventPatch)
        ):
            raise GoogleCalendarWriteError(
                GOOGLE_CALENDAR_UPDATE_ERROR_INVALID_REQUEST,
                indeterminate=False,
            )

        payload: dict[str, object] = {}
        if changes.summary is not None:
            payload["summary"] = changes.summary
        if changes.start is not None:
            assert changes.end is not None
            payload["start"] = {
                "dateTime": changes.start.isoformat(timespec="microseconds")
            }
            payload["end"] = {
                "dateTime": changes.end.isoformat(timespec="microseconds")
            }
        if changes.description is not None:
            payload["description"] = changes.description
        if changes.location is not None:
            payload["location"] = changes.location

        request = self._json_request(
            _event_url(target),
            method="PATCH",
            token=token,
            payload=payload,
            user_agent="O-AI-D75-Google-Calendar",
        )
        raw = self._perform(
            request,
            success_statuses=(200,),
            provider_rejected_code=GOOGLE_CALENDAR_UPDATE_ERROR_PROVIDER_REJECTED,
            indeterminate_code=GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
        )
        event_id = self._response_event_id(
            raw,
            indeterminate_code=GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
        )
        if event_id != target.event_id:
            raise GoogleCalendarWriteError(
                GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
                indeterminate=True,
            )
        return GoogleCalendarUpdateResult(event_id=event_id)

    def delete_event(
        self,
        credential: SecretStr,
        *,
        target: GoogleCalendarEventTarget,
    ) -> GoogleCalendarDeleteResult:
        token = self._token(
            credential,
            GOOGLE_CALENDAR_DELETE_ERROR_INVALID_REQUEST,
        )
        if (
            not isinstance(target, GoogleCalendarEventTarget)
            or target.calendar_id != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID
        ):
            raise GoogleCalendarWriteError(
                GOOGLE_CALENDAR_DELETE_ERROR_INVALID_REQUEST,
                indeterminate=False,
            )
        request = urllib.request.Request(
            _event_url(target),
            method="DELETE",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "O-AI-D75-Google-Calendar",
            },
        )
        raw = self._perform(
            request,
            success_statuses=(200, 204),
            provider_rejected_code=GOOGLE_CALENDAR_DELETE_ERROR_PROVIDER_REJECTED,
            indeterminate_code=GOOGLE_CALENDAR_DELETE_ERROR_INDETERMINATE,
        )
        if raw:
            raise GoogleCalendarWriteError(
                GOOGLE_CALENDAR_DELETE_ERROR_INDETERMINATE,
                indeterminate=True,
            )
        return GoogleCalendarDeleteResult(event_id=target.event_id)

    @staticmethod
    def _token(credential: SecretStr, invalid_code: str) -> str:
        if not isinstance(credential, SecretStr):
            raise GoogleCalendarWriteError(invalid_code, indeterminate=False)
        token = credential.get_secret_value()
        if not token or "\r" in token or "\n" in token:
            raise GoogleCalendarWriteError(invalid_code, indeterminate=False)
        return token

    @staticmethod
    def _json_request(
        url: str,
        *,
        method: str,
        token: str,
        payload: dict[str, object],
        user_agent: str,
    ) -> urllib.request.Request:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
            },
        )

    @staticmethod
    def _response_event_id(raw: bytes, *, indeterminate_code: str) -> str:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            ) from None
        if not isinstance(payload, dict):
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            )
        try:
            target = GoogleCalendarEventTarget(
                event_id=payload.get("id")  # type: ignore[arg-type]
            )
        except (TypeError, ValueError):
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            ) from None
        return target.event_id

    def _perform(
        self,
        request: urllib.request.Request,
        *,
        success_statuses: tuple[int, ...],
        provider_rejected_code: str,
        indeterminate_code: str,
    ) -> bytes:
        try:
            context = self._transport(request, self._timeout_seconds)
            with context as response:
                status = getattr(response, "status", None)
                if status not in success_statuses:
                    self._raise_status(
                        status,
                        provider_rejected_code=provider_rejected_code,
                        indeterminate_code=indeterminate_code,
                    )
                body = response.read(GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES + 1)
        except GoogleCalendarWriteError:
            raise
        except urllib.error.HTTPError as error:
            self._raise_status(
                error.code,
                provider_rejected_code=provider_rejected_code,
                indeterminate_code=indeterminate_code,
            )
        except (socket.timeout, TimeoutError, urllib.error.URLError):
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            ) from None
        except Exception:
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            ) from None
        if (
            not isinstance(body, bytes)
            or len(body) > GOOGLE_CALENDAR_WRITE_MAX_RESPONSE_BYTES
        ):
            raise GoogleCalendarWriteError(
                indeterminate_code,
                indeterminate=True,
            )
        return body

    @staticmethod
    def _raise_status(
        status: object,
        *,
        provider_rejected_code: str,
        indeterminate_code: str,
    ) -> None:
        if (
            isinstance(status, int)
            and not isinstance(status, bool)
            and 400 <= status < 500
            and status != 408
        ):
            raise GoogleCalendarWriteError(
                provider_rejected_code,
                indeterminate=False,
            )
        raise GoogleCalendarWriteError(
            indeterminate_code,
            indeterminate=True,
        )


__all__ = [
    "GOOGLE_CALENDAR_CREATE_EVENT_URL",
    "GOOGLE_CALENDAR_DELETE_ERROR_INDETERMINATE",
    "GOOGLE_CALENDAR_DELETE_ERROR_INVALID_REQUEST",
    "GOOGLE_CALENDAR_DELETE_ERROR_PROVIDER_REJECTED",
    "GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE",
    "GOOGLE_CALENDAR_UPDATE_ERROR_INVALID_REQUEST",
    "GOOGLE_CALENDAR_UPDATE_ERROR_PROVIDER_REJECTED",
    "GOOGLE_CALENDAR_WRITE_ERROR_INDETERMINATE",
    "GOOGLE_CALENDAR_WRITE_ERROR_INVALID_REQUEST",
    "GOOGLE_CALENDAR_WRITE_ERROR_PROVIDER_REJECTED",
    "GoogleCalendarCreateResult",
    "GoogleCalendarDeleteResult",
    "GoogleCalendarEventCreator",
    "GoogleCalendarEventDeleter",
    "GoogleCalendarEventUpdater",
    "GoogleCalendarUpdateResult",
    "GoogleCalendarWriteClient",
    "GoogleCalendarWriteError",
]
