"""D74 private Calendar create execution contracts and exact plan projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID,
    GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
    GoogleCalendarCreateEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventTarget,
)

GOOGLE_CALENDAR_CREATE_ADAPTER_ID = "module.google_calendar.create_event"
GOOGLE_CALENDAR_CREATE_CAPABILITY_ID = "exec.google_calendar.create_event"
GOOGLE_CALENDAR_CREATE_MODULE_NAME = "Google Calendar Create Event"

CalendarCreateExecutionStatus: TypeAlias = Literal[
    "succeeded", "failed", "indeterminate"
]
_HEX = frozenset("0123456789abcdef")
_REQUIRED_KEYS = frozenset(
    {"contract_version", "write_digest", "calendar_id", "summary", "start", "end"}
)
_OPTIONAL_KEYS = frozenset({"description", "location"})


def _text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(code)
    return value


def validate_write_digest(value: object) -> str:
    value = _text(value, code="calendar_create_write_digest_invalid")
    if len(value) != 64 or any(ch not in _HEX for ch in value):
        raise ValueError("calendar_create_write_digest_invalid")
    return value


def calendar_create_execution_parameters(
    request: GoogleCalendarCreateEventRequest,
    write_digest: str,
) -> dict[str, object]:
    """Project one exact D72 create request into one private D74 plan payload."""
    if not isinstance(request, GoogleCalendarCreateEventRequest):
        raise ValueError("calendar_create_request_invalid")
    event = request.event
    payload: dict[str, object] = {
        "contract_version": request.contract_version,
        "write_digest": validate_write_digest(write_digest),
        "calendar_id": event.calendar_id,
        "summary": event.summary,
        "start": event.start.isoformat(timespec="microseconds"),
        "end": event.end.isoformat(timespec="microseconds"),
    }
    if event.description is not None:
        payload["description"] = event.description
    if event.location is not None:
        payload["location"] = event.location
    return payload


def calendar_create_request_from_parameters(
    parameters: object,
) -> tuple[GoogleCalendarCreateEventRequest, str]:
    """Reconstruct one exact D72 create request from D74 execution parameters."""
    if not isinstance(parameters, Mapping):
        raise ValueError("calendar_create_parameters_invalid")
    keys = frozenset(parameters)
    if not _REQUIRED_KEYS.issubset(keys) or not keys.issubset(_REQUIRED_KEYS | _OPTIONAL_KEYS):
        raise ValueError("calendar_create_parameters_invalid")
    if parameters.get("contract_version") != GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION:
        raise ValueError("calendar_create_parameters_invalid")
    if parameters.get("calendar_id") != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID:
        raise ValueError("calendar_create_parameters_invalid")
    digest = validate_write_digest(parameters.get("write_digest"))
    start_raw = parameters.get("start")
    end_raw = parameters.get("end")
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        raise ValueError("calendar_create_parameters_invalid")
    try:
        start = datetime.fromisoformat(start_raw)
        end = datetime.fromisoformat(end_raw)
        event = GoogleCalendarEventDraft(
            summary=parameters.get("summary"),  # type: ignore[arg-type]
            start=start,
            end=end,
            description=(parameters.get("description") if "description" in parameters else None),  # type: ignore[arg-type]
            location=(parameters.get("location") if "location" in parameters else None),  # type: ignore[arg-type]
        )
        request = GoogleCalendarCreateEventRequest(event=event)
    except (TypeError, ValueError):
        raise ValueError("calendar_create_parameters_invalid") from None
    if request.operation != GOOGLE_CALENDAR_CREATE_EVENT_OPERATION:
        raise ValueError("calendar_create_parameters_invalid")
    return request, digest


@dataclass(frozen=True, slots=True)
class CalendarCreateExecutionOutcome:
    approval_id: str
    write_digest: str
    status: CalendarCreateExecutionStatus
    reason_code: str
    event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "approval_id", _text(self.approval_id, code="calendar_create_approval_id_invalid"))
        object.__setattr__(self, "write_digest", validate_write_digest(self.write_digest))
        object.__setattr__(self, "reason_code", _text(self.reason_code, code="calendar_create_reason_code_invalid"))
        if self.status not in {"succeeded", "failed", "indeterminate"}:
            raise ValueError("calendar_create_status_invalid")
        if self.status == "succeeded":
            if self.event_id is None:
                raise ValueError("calendar_create_event_id_invalid")
            GoogleCalendarEventTarget(event_id=self.event_id)
        elif self.event_id is not None:
            raise ValueError("calendar_create_event_id_unexpected")


__all__ = [
    "CalendarCreateExecutionOutcome",
    "GOOGLE_CALENDAR_CREATE_ADAPTER_ID",
    "GOOGLE_CALENDAR_CREATE_CAPABILITY_ID",
    "GOOGLE_CALENDAR_CREATE_MODULE_NAME",
    "calendar_create_execution_parameters",
    "calendar_create_request_from_parameters",
    "validate_write_digest",
]
