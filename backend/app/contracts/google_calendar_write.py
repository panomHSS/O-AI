"""D72 immutable provider-neutral Google Calendar write contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
import unicodedata


GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION = "1"

GOOGLE_CALENDAR_CREATE_EVENT_OPERATION = "create_event"
GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION = "update_event"
GOOGLE_CALENDAR_DELETE_EVENT_OPERATION = "delete_event"

GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID = "primary"
GOOGLE_CALENDAR_MAX_EVENT_DURATION_DAYS = 32

GOOGLE_CALENDAR_MAX_SUMMARY_BYTES = 1024
GOOGLE_CALENDAR_MAX_DESCRIPTION_BYTES = 8192
GOOGLE_CALENDAR_MAX_LOCATION_BYTES = 1024
GOOGLE_CALENDAR_MAX_EVENT_ID_BYTES = 1024


def _validate_bounded_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
    require_nonempty: bool = False,
    require_trimmed: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(code)
    if require_nonempty and not value:
        raise ValueError(code)
    if require_trimmed and value != value.strip():
        raise ValueError(code)
    if require_nonempty and not value.strip():
        raise ValueError(code)
    if len(value.encode("utf-8")) > max_bytes:
        raise ValueError(code)
    return value


def _validate_absolute_interval(
    start: object,
    end: object,
    *,
    code: str,
) -> tuple[datetime, datetime]:
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError(code)
    if (
        start.tzinfo is None
        or start.utcoffset() is None
        or end.tzinfo is None
        or end.utcoffset() is None
    ):
        raise ValueError(code)

    elapsed = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    if elapsed <= timedelta(0) or elapsed > timedelta(
        days=GOOGLE_CALENDAR_MAX_EVENT_DURATION_DAYS
    ):
        raise ValueError(code)
    return start, end


def _validate_primary_calendar(calendar_id: object) -> None:
    if calendar_id != GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID:
        raise ValueError("calendar_write_calendar_invalid")


def _validate_event_id(event_id: object) -> str:
    value = _validate_bounded_text(
        event_id,
        code="calendar_write_event_id_invalid",
        max_bytes=GOOGLE_CALENDAR_MAX_EVENT_ID_BYTES,
        require_nonempty=True,
        require_trimmed=True,
    )
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("calendar_write_event_id_invalid")
    return value


@dataclass(frozen=True, slots=True)
class GoogleCalendarEventDraft:
    """One exact timed event proposal; constructing it performs no write."""

    summary: str
    start: datetime
    end: datetime
    description: str | None = None
    location: str | None = None
    calendar_id: Literal["primary"] = GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID

    def __post_init__(self) -> None:
        _validate_primary_calendar(self.calendar_id)
        _validate_bounded_text(
            self.summary,
            code="calendar_write_summary_invalid",
            max_bytes=GOOGLE_CALENDAR_MAX_SUMMARY_BYTES,
            require_nonempty=True,
            require_trimmed=True,
        )
        _validate_absolute_interval(
            self.start,
            self.end,
            code="calendar_write_time_invalid",
        )
        if self.description is not None:
            _validate_bounded_text(
                self.description,
                code="calendar_write_description_invalid",
                max_bytes=GOOGLE_CALENDAR_MAX_DESCRIPTION_BYTES,
            )
        if self.location is not None:
            _validate_bounded_text(
                self.location,
                code="calendar_write_location_invalid",
                max_bytes=GOOGLE_CALENDAR_MAX_LOCATION_BYTES,
            )


@dataclass(frozen=True, slots=True)
class GoogleCalendarEventTarget:
    """Exact primary-calendar event identity for future update/delete."""

    event_id: str
    calendar_id: Literal["primary"] = GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID

    def __post_init__(self) -> None:
        _validate_primary_calendar(self.calendar_id)
        _validate_event_id(self.event_id)


@dataclass(frozen=True, slots=True)
class GoogleCalendarEventPatch:
    """Allowlisted future update fields with exact paired time boundaries."""

    summary: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    description: str | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        if (
            self.summary is None
            and self.start is None
            and self.end is None
            and self.description is None
            and self.location is None
        ):
            raise ValueError("calendar_write_patch_empty")

        if self.summary is not None:
            _validate_bounded_text(
                self.summary,
                code="calendar_write_summary_invalid",
                max_bytes=GOOGLE_CALENDAR_MAX_SUMMARY_BYTES,
                require_nonempty=True,
                require_trimmed=True,
            )

        if (self.start is None) != (self.end is None):
            raise ValueError("calendar_write_time_pair_required")
        if self.start is not None and self.end is not None:
            _validate_absolute_interval(
                self.start,
                self.end,
                code="calendar_write_time_invalid",
            )

        if self.description is not None:
            _validate_bounded_text(
                self.description,
                code="calendar_write_description_invalid",
                max_bytes=GOOGLE_CALENDAR_MAX_DESCRIPTION_BYTES,
            )
        if self.location is not None:
            _validate_bounded_text(
                self.location,
                code="calendar_write_location_invalid",
                max_bytes=GOOGLE_CALENDAR_MAX_LOCATION_BYTES,
            )


@dataclass(frozen=True, slots=True)
class GoogleCalendarCreateEventRequest:
    """Contract-only create request; not an execution or provider request."""

    event: GoogleCalendarEventDraft
    contract_version: Literal["1"] = field(
        default=GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
        init=False,
    )
    operation: Literal["create_event"] = field(
        default=GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.event, GoogleCalendarEventDraft):
            raise ValueError("calendar_write_event_invalid")


@dataclass(frozen=True, slots=True)
class GoogleCalendarUpdateEventRequest:
    """Contract-only exact-target update request."""

    target: GoogleCalendarEventTarget
    changes: GoogleCalendarEventPatch
    contract_version: Literal["1"] = field(
        default=GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
        init=False,
    )
    operation: Literal["update_event"] = field(
        default=GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.target, GoogleCalendarEventTarget):
            raise ValueError("calendar_write_target_invalid")
        if not isinstance(self.changes, GoogleCalendarEventPatch):
            raise ValueError("calendar_write_patch_invalid")


@dataclass(frozen=True, slots=True)
class GoogleCalendarDeleteEventRequest:
    """Contract-only exact-target delete request."""

    target: GoogleCalendarEventTarget
    contract_version: Literal["1"] = field(
        default=GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
        init=False,
    )
    operation: Literal["delete_event"] = field(
        default=GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.target, GoogleCalendarEventTarget):
            raise ValueError("calendar_write_target_invalid")


__all__ = [
    "GOOGLE_CALENDAR_CREATE_EVENT_OPERATION",
    "GOOGLE_CALENDAR_DELETE_EVENT_OPERATION",
    "GOOGLE_CALENDAR_MAX_DESCRIPTION_BYTES",
    "GOOGLE_CALENDAR_MAX_EVENT_DURATION_DAYS",
    "GOOGLE_CALENDAR_MAX_EVENT_ID_BYTES",
    "GOOGLE_CALENDAR_MAX_LOCATION_BYTES",
    "GOOGLE_CALENDAR_MAX_SUMMARY_BYTES",
    "GOOGLE_CALENDAR_PRIMARY_CALENDAR_ID",
    "GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION",
    "GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION",
    "GoogleCalendarCreateEventRequest",
    "GoogleCalendarDeleteEventRequest",
    "GoogleCalendarEventDraft",
    "GoogleCalendarEventPatch",
    "GoogleCalendarEventTarget",
    "GoogleCalendarUpdateEventRequest",
]
