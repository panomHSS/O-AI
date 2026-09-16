"""D78 immutable bounded cross-connector context contracts."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, TypeAlias
from uuid import UUID


CROSS_CONNECTOR_CONTEXT_TTL = timedelta(minutes=10)
CROSS_CONNECTOR_CONTEXT_MAX_BYTES = 24 * 1024
CROSS_CONNECTOR_GMAIL_MAX_MESSAGES = 5
CROSS_CONNECTOR_CALENDAR_MAX_EVENTS = 10
CROSS_CONNECTOR_GMAIL_MAX_TEXT_CHARS = 2048
CROSS_CONNECTOR_MAX_SENDER_CHARS = 1024
CROSS_CONNECTOR_MAX_SUBJECT_CHARS = 1024
CROSS_CONNECTOR_MAX_CALENDAR_SUMMARY_CHARS = 1024
CROSS_CONNECTOR_MAX_TIMESTAMP_BYTES = 128

CrossConnectorContextSource: TypeAlias = Literal["gmail", "google_calendar"]
CrossConnectorContextMode: TypeAlias = Literal["summarize", "compare"]

_ALLOWED_CALENDAR_STATUSES = frozenset(
    {"confirmed", "tentative", "cancelled"}
)


def _contains_disallowed_control(value: str, *, multiline: bool) -> bool:
    for character in value:
        if multiline and character in "\r\n\t":
            continue
        if unicodedata.category(character) == "Cc":
            return True
    return False


def _bounded_text(
    value: object,
    *,
    max_chars: int,
    code: str,
    allow_empty: bool = True,
    multiline: bool = False,
) -> str:
    if (
        not isinstance(value, str)
        or (not allow_empty and not value)
        or len(value) > max_chars
        or _contains_disallowed_control(value, multiline=multiline)
    ):
        raise ValueError(code)
    return value


def _aware(value: object, *, code: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(code)
    return value


def _utc_z_timestamp(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.endswith("Z")
        or len(value.encode("utf-8")) > CROSS_CONNECTOR_MAX_TIMESTAMP_BYTES
    ):
        raise ValueError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(code) from None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class CrossConnectorContextIntent:
    """Explicit D78 answer-only request; grants no execution authority."""
    mode: CrossConnectorContextMode
    def __post_init__(self) -> None:
        if self.mode not in {"summarize", "compare"}:
            raise ValueError("cross_connector_intent_mode_invalid")


@dataclass(frozen=True, slots=True)
class GmailContextMessage:
    """D78 Gmail projection with no provider identity or message id."""

    sender: str
    subject: str
    received_at: str
    unread: bool
    text: str

    def __post_init__(self) -> None:
        _bounded_text(
            self.sender,
            max_chars=CROSS_CONNECTOR_MAX_SENDER_CHARS,
            code="cross_connector_gmail_sender_invalid",
        )
        _bounded_text(
            self.subject,
            max_chars=CROSS_CONNECTOR_MAX_SUBJECT_CHARS,
            code="cross_connector_gmail_subject_invalid",
        )
        _utc_z_timestamp(
            self.received_at,
            code="cross_connector_gmail_received_at_invalid",
        )
        if type(self.unread) is not bool:
            raise ValueError("cross_connector_gmail_unread_invalid")
        _bounded_text(
            self.text,
            max_chars=CROSS_CONNECTOR_GMAIL_MAX_TEXT_CHARS,
            code="cross_connector_gmail_text_invalid",
            multiline=True,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "from": self.sender,
            "received_at": self.received_at,
            "subject": self.subject,
            "text": self.text,
            "unread": self.unread,
        }


@dataclass(frozen=True, slots=True)
class CalendarContextEvent:
    """D78 Calendar projection containing only validated display fields."""

    summary: str
    status: str
    start: str
    end: str
    all_day: bool

    def __post_init__(self) -> None:
        _bounded_text(
            self.summary,
            max_chars=CROSS_CONNECTOR_MAX_CALENDAR_SUMMARY_CHARS,
            code="cross_connector_calendar_summary_invalid",
            allow_empty=False,
        )
        if self.status not in _ALLOWED_CALENDAR_STATUSES:
            raise ValueError("cross_connector_calendar_status_invalid")
        if type(self.all_day) is not bool:
            raise ValueError("cross_connector_calendar_all_day_invalid")
        if (
            not isinstance(self.start, str)
            or not isinstance(self.end, str)
            or len(self.start.encode("utf-8")) > CROSS_CONNECTOR_MAX_TIMESTAMP_BYTES
            or len(self.end.encode("utf-8")) > CROSS_CONNECTOR_MAX_TIMESTAMP_BYTES
        ):
            raise ValueError("cross_connector_calendar_time_invalid")

        try:
            if self.all_day:
                start_value = date.fromisoformat(self.start)
                end_value = date.fromisoformat(self.end)
            else:
                start_value = datetime.fromisoformat(
                    self.start.replace("Z", "+00:00")
                )
                end_value = datetime.fromisoformat(
                    self.end.replace("Z", "+00:00")
                )
                if (
                    start_value.tzinfo is None
                    or start_value.utcoffset() is None
                    or end_value.tzinfo is None
                    or end_value.utcoffset() is None
                ):
                    raise ValueError
        except ValueError:
            raise ValueError("cross_connector_calendar_time_invalid") from None

        if end_value <= start_value:
            raise ValueError("cross_connector_calendar_time_invalid")

    def as_dict(self) -> dict[str, object]:
        return {
            "all_day": self.all_day,
            "end": self.end,
            "start": self.start,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class GmailContextSnapshot:
    conversation_id: UUID
    captured_at: datetime
    expires_at: datetime
    messages: tuple[GmailContextMessage, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        captured = _aware(
            self.captured_at,
            code="cross_connector_captured_at_invalid",
        )
        expires = _aware(
            self.expires_at,
            code="cross_connector_expires_at_invalid",
        )
        if expires - captured != CROSS_CONNECTOR_CONTEXT_TTL:
            raise ValueError("cross_connector_ttl_invalid")
        if (
            not isinstance(self.messages, tuple)
            or len(self.messages) > CROSS_CONNECTOR_GMAIL_MAX_MESSAGES
            or any(
                not isinstance(message, GmailContextMessage)
                for message in self.messages
            )
        ):
            raise ValueError("cross_connector_gmail_snapshot_invalid")

    def as_payload(self) -> list[dict[str, object]]:
        return [message.as_dict() for message in self.messages]


@dataclass(frozen=True, slots=True)
class CalendarContextSnapshot:
    conversation_id: UUID
    captured_at: datetime
    expires_at: datetime
    events: tuple[CalendarContextEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        captured = _aware(
            self.captured_at,
            code="cross_connector_captured_at_invalid",
        )
        expires = _aware(
            self.expires_at,
            code="cross_connector_expires_at_invalid",
        )
        if expires - captured != CROSS_CONNECTOR_CONTEXT_TTL:
            raise ValueError("cross_connector_ttl_invalid")
        if (
            not isinstance(self.events, tuple)
            or len(self.events) > CROSS_CONNECTOR_CALENDAR_MAX_EVENTS
            or any(
                not isinstance(event, CalendarContextEvent)
                for event in self.events
            )
        ):
            raise ValueError("cross_connector_calendar_snapshot_invalid")

    def as_payload(self) -> list[dict[str, object]]:
        return [event.as_dict() for event in self.events]


@dataclass(frozen=True, slots=True)
class CrossConnectorContextBundle:
    gmail: GmailContextSnapshot
    calendar: CalendarContextSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.gmail, GmailContextSnapshot):
            raise TypeError("gmail must be a GmailContextSnapshot.")
        if not isinstance(self.calendar, CalendarContextSnapshot):
            raise TypeError("calendar must be a CalendarContextSnapshot.")
        if self.gmail.conversation_id != self.calendar.conversation_id:
            raise ValueError("cross_connector_conversation_mismatch")
        if self.serialized_size_bytes > CROSS_CONNECTOR_CONTEXT_MAX_BYTES:
            raise ValueError("cross_connector_context_too_large")

    @property
    def conversation_id(self) -> UUID:
        return self.gmail.conversation_id

    def as_payload(self) -> dict[str, object]:
        return {
            "gmail": self.gmail.as_payload(),
            "google_calendar": self.calendar.as_payload(),
        }

    @property
    def serialized_size_bytes(self) -> int:
        return len(
            json.dumps(
                self.as_payload(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )


__all__ = [
    "CROSS_CONNECTOR_CALENDAR_MAX_EVENTS",
    "CROSS_CONNECTOR_CONTEXT_MAX_BYTES",
    "CROSS_CONNECTOR_CONTEXT_TTL",
    "CROSS_CONNECTOR_GMAIL_MAX_MESSAGES",
    "CROSS_CONNECTOR_GMAIL_MAX_TEXT_CHARS",
    "CalendarContextEvent",
    "CrossConnectorContextIntent",
    "CrossConnectorContextMode",
    "CrossConnectorContextSource",
    "CalendarContextSnapshot",
    "CrossConnectorContextBundle",
    "GmailContextMessage",
    "GmailContextSnapshot",
]
