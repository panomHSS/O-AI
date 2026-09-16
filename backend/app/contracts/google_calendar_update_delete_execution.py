"""D75 private Calendar update/delete execution contracts and exact projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
    GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID,
    GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)

GOOGLE_CALENDAR_UPDATE_ADAPTER_ID = "module.google_calendar.update_event"
GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID = "exec.google_calendar.update_event"
GOOGLE_CALENDAR_UPDATE_MODULE_NAME = "Google Calendar Update Event"
GOOGLE_CALENDAR_DELETE_ADAPTER_ID = "module.google_calendar.delete_event"
GOOGLE_CALENDAR_DELETE_CAPABILITY_ID = "exec.google_calendar.delete_event"
GOOGLE_CALENDAR_DELETE_MODULE_NAME = "Google Calendar Delete Event"

CalendarMutationExecutionStatus: TypeAlias = Literal[
    "succeeded", "failed", "indeterminate"
]

_HEX = frozenset("0123456789abcdef")
_COMMON_REQUIRED_KEYS = frozenset(
    {"contract_version", "write_digest", "calendar_id", "event_id"}
)
_UPDATE_CHANGE_KEYS = frozenset(
    {"summary", "start", "end", "description", "location"}
)
_DELETE_KEYS = _COMMON_REQUIRED_KEYS


def _text(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(code)
    return value


def _write_digest(value: object, *, code: str) -> str:
    digest = _text(value, code=code)
    if len(digest) != 64 or any(character not in _HEX for character in digest):
        raise ValueError(code)
    return digest


def calendar_update_execution_parameters(
    request: GoogleCalendarUpdateEventRequest,
    write_digest: str,
) -> dict[str, object]:
    """Project one exact D72 update request into one private D75 plan payload."""
    if not isinstance(request, GoogleCalendarUpdateEventRequest):
        raise ValueError("calendar_update_request_invalid")
    payload: dict[str, object] = {
        "contract_version": request.contract_version,
        "write_digest": _write_digest(
            write_digest,
            code="calendar_update_write_digest_invalid",
        ),
        "calendar_id": request.target.calendar_id,
        "event_id": request.target.event_id,
    }
    changes = request.changes
    if changes.summary is not None:
        payload["summary"] = changes.summary
    if changes.start is not None:
        assert changes.end is not None
        payload["start"] = changes.start.isoformat(timespec="microseconds")
        payload["end"] = changes.end.isoformat(timespec="microseconds")
    if changes.description is not None:
        payload["description"] = changes.description
    if changes.location is not None:
        payload["location"] = changes.location
    return payload


def calendar_update_request_from_parameters(
    parameters: object,
) -> tuple[GoogleCalendarUpdateEventRequest, str]:
    """Reconstruct one exact D72 update request from D75 plan parameters."""
    code = "calendar_update_parameters_invalid"
    if not isinstance(parameters, Mapping):
        raise ValueError(code)
    keys = frozenset(parameters)
    if (
        not _COMMON_REQUIRED_KEYS.issubset(keys)
        or not keys.issubset(_COMMON_REQUIRED_KEYS | _UPDATE_CHANGE_KEYS)
        or not keys.intersection(_UPDATE_CHANGE_KEYS)
    ):
        raise ValueError(code)
    if parameters.get("contract_version") != GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION:
        raise ValueError(code)
    if parameters.get("calendar_id") != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID:
        raise ValueError(code)

    digest = _write_digest(
        parameters.get("write_digest"),
        code="calendar_update_write_digest_invalid",
    )
    if "summary" in parameters and not isinstance(parameters.get("summary"), str):
        raise ValueError(code)
    if "description" in parameters and not isinstance(parameters.get("description"), str):
        raise ValueError(code)
    if "location" in parameters and not isinstance(parameters.get("location"), str):
        raise ValueError(code)

    has_start = "start" in parameters
    has_end = "end" in parameters
    if has_start != has_end:
        raise ValueError(code)
    start = None
    end = None
    if has_start:
        start_raw = parameters.get("start")
        end_raw = parameters.get("end")
        if not isinstance(start_raw, str) or not isinstance(end_raw, str):
            raise ValueError(code)
        try:
            start = datetime.fromisoformat(start_raw)
            end = datetime.fromisoformat(end_raw)
        except ValueError:
            raise ValueError(code) from None

    try:
        target = GoogleCalendarEventTarget(
            event_id=parameters.get("event_id"),  # type: ignore[arg-type]
            calendar_id=parameters.get("calendar_id"),  # type: ignore[arg-type]
        )
        changes = GoogleCalendarEventPatch(
            summary=(parameters.get("summary") if "summary" in parameters else None),  # type: ignore[arg-type]
            start=start,
            end=end,
            description=(
                parameters.get("description")
                if "description" in parameters
                else None
            ),  # type: ignore[arg-type]
            location=(
                parameters.get("location")
                if "location" in parameters
                else None
            ),  # type: ignore[arg-type]
        )
        request = GoogleCalendarUpdateEventRequest(
            target=target,
            changes=changes,
        )
    except (TypeError, ValueError):
        raise ValueError(code) from None
    if request.operation != GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION:
        raise ValueError(code)
    if calendar_update_execution_parameters(request, digest) != dict(parameters):
        raise ValueError(code)
    return request, digest


def calendar_delete_execution_parameters(
    request: GoogleCalendarDeleteEventRequest,
    write_digest: str,
) -> dict[str, object]:
    """Project one exact D72 delete request into one private D75 plan payload."""
    if not isinstance(request, GoogleCalendarDeleteEventRequest):
        raise ValueError("calendar_delete_request_invalid")
    return {
        "contract_version": request.contract_version,
        "write_digest": _write_digest(
            write_digest,
            code="calendar_delete_write_digest_invalid",
        ),
        "calendar_id": request.target.calendar_id,
        "event_id": request.target.event_id,
    }


def calendar_delete_request_from_parameters(
    parameters: object,
) -> tuple[GoogleCalendarDeleteEventRequest, str]:
    """Reconstruct one exact D72 delete request from D75 plan parameters."""
    code = "calendar_delete_parameters_invalid"
    if not isinstance(parameters, Mapping) or frozenset(parameters) != _DELETE_KEYS:
        raise ValueError(code)
    if parameters.get("contract_version") != GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION:
        raise ValueError(code)
    if parameters.get("calendar_id") != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID:
        raise ValueError(code)
    digest = _write_digest(
        parameters.get("write_digest"),
        code="calendar_delete_write_digest_invalid",
    )
    try:
        target = GoogleCalendarEventTarget(
            event_id=parameters.get("event_id"),  # type: ignore[arg-type]
            calendar_id=parameters.get("calendar_id"),  # type: ignore[arg-type]
        )
        request = GoogleCalendarDeleteEventRequest(target=target)
    except (TypeError, ValueError):
        raise ValueError(code) from None
    if request.operation != GOOGLE_CALENDAR_DELETE_EVENT_OPERATION:
        raise ValueError(code)
    if calendar_delete_execution_parameters(request, digest) != dict(parameters):
        raise ValueError(code)
    return request, digest


@dataclass(frozen=True, slots=True)
class CalendarUpdateExecutionOutcome:
    approval_id: str
    write_digest: str
    status: CalendarMutationExecutionStatus
    reason_code: str
    event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approval_id",
            _text(self.approval_id, code="calendar_update_approval_id_invalid"),
        )
        object.__setattr__(
            self,
            "write_digest",
            _write_digest(
                self.write_digest,
                code="calendar_update_write_digest_invalid",
            ),
        )
        object.__setattr__(
            self,
            "reason_code",
            _text(self.reason_code, code="calendar_update_reason_code_invalid"),
        )
        if self.status not in {"succeeded", "failed", "indeterminate"}:
            raise ValueError("calendar_update_status_invalid")
        if self.status == "succeeded":
            if self.event_id is None:
                raise ValueError("calendar_update_event_id_invalid")
            GoogleCalendarEventTarget(event_id=self.event_id)
        elif self.event_id is not None:
            raise ValueError("calendar_update_event_id_unexpected")


@dataclass(frozen=True, slots=True)
class CalendarDeleteExecutionOutcome:
    approval_id: str
    write_digest: str
    status: CalendarMutationExecutionStatus
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approval_id",
            _text(self.approval_id, code="calendar_delete_approval_id_invalid"),
        )
        object.__setattr__(
            self,
            "write_digest",
            _write_digest(
                self.write_digest,
                code="calendar_delete_write_digest_invalid",
            ),
        )
        object.__setattr__(
            self,
            "reason_code",
            _text(self.reason_code, code="calendar_delete_reason_code_invalid"),
        )
        if self.status not in {"succeeded", "failed", "indeterminate"}:
            raise ValueError("calendar_delete_status_invalid")


__all__ = [
    "CalendarDeleteExecutionOutcome",
    "CalendarMutationExecutionStatus",
    "CalendarUpdateExecutionOutcome",
    "GOOGLE_CALENDAR_DELETE_ADAPTER_ID",
    "GOOGLE_CALENDAR_DELETE_CAPABILITY_ID",
    "GOOGLE_CALENDAR_DELETE_MODULE_NAME",
    "GOOGLE_CALENDAR_UPDATE_ADAPTER_ID",
    "GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID",
    "GOOGLE_CALENDAR_UPDATE_MODULE_NAME",
    "calendar_delete_execution_parameters",
    "calendar_delete_request_from_parameters",
    "calendar_update_execution_parameters",
    "calendar_update_request_from_parameters",
]
