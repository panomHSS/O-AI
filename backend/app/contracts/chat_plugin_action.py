"""D61/D65 immutable contracts for Chat-to-Plugin action correlation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.gmail import GmailReadQuery


ChatPluginIntentStatus: TypeAlias = Literal["none", "matched", "invalid"]
CalendarChatWindow: TypeAlias = Literal[
    "today",
    "tomorrow",
    "next_7_days",
    "this_week",
    "next_week",
    "this_month",
    "today_morning",
    "today_afternoon",
    "today_evening",
    "tomorrow_morning",
    "tomorrow_afternoon",
    "tomorrow_evening",
    "upcoming_weekend",
    "next_weekend",
    "exact_date",
]

_CALENDAR_WINDOWS = frozenset(
    {
        "today",
        "tomorrow",
        "next_7_days",
        "this_week",
        "next_week",
        "this_month",
        "today_morning",
        "today_afternoon",
        "today_evening",
        "tomorrow_morning",
        "tomorrow_afternoon",
        "tomorrow_evening",
        "upcoming_weekend",
        "next_weekend",
        "exact_date",
    }
)


@dataclass(frozen=True, slots=True)
class ChatPluginIntentOutcome:
    """Deterministic classification only; carries no execution authority."""

    status: ChatPluginIntentStatus
    repository_reference: str | None = None
    calendar_window: CalendarChatWindow | None = None
    calendar_date: date | None = None
    calendar_intent: bool = False
    gmail_query: GmailReadQuery | None = None

    def __post_init__(self) -> None:
        if self.status not in {"none", "matched", "invalid"}:
            raise ValueError("Unsupported Chat Plugin intent status.")
        if type(self.calendar_intent) is not bool:
            raise ValueError("calendar_intent must be an exact bool.")
        if self.gmail_query is not None and not isinstance(
            self.gmail_query, GmailReadQuery
        ):
            raise TypeError("gmail_query must be a GmailReadQuery.")

        if self.status == "none":
            if (
                self.repository_reference is not None
                or self.calendar_window is not None
                or self.calendar_date is not None
                or self.calendar_intent
                or self.gmail_query is not None
            ):
                raise ValueError("none intent must not carry target metadata.")
            return

        if self.status == "invalid":
            if (
                self.repository_reference is not None
                or self.calendar_window is not None
                or self.calendar_date is not None
                or self.gmail_query is not None
            ):
                raise ValueError("invalid intent must not carry target metadata.")
            return

        repository = self.repository_reference
        calendar_window = self.calendar_window
        gmail_query = self.gmail_query
        target_count = sum(
            (
                repository is not None,
                self.calendar_intent,
                gmail_query is not None,
            )
        )
        if target_count != 1:
            raise ValueError(
                "matched intent requires exactly one connector target."
            )

        if gmail_query is not None:
            if (
                calendar_window is not None
                or self.calendar_date is not None
                or self.calendar_intent
            ):
                raise ValueError(
                    "matched Gmail intent must not carry Calendar metadata."
                )
            return

        if self.calendar_intent:
            if repository is not None or calendar_window not in _CALENDAR_WINDOWS:
                raise ValueError(
                    "matched Calendar intent requires one supported calendar_window."
                )
            if calendar_window == "exact_date":
                if type(self.calendar_date) is not date:
                    raise ValueError(
                        "exact-date Calendar intent requires one Gregorian date."
                    )
            elif self.calendar_date is not None:
                raise ValueError(
                    "relative Calendar intent must not carry calendar_date."
                )
            return

        if (
            not isinstance(repository, str)
            or not repository
            or repository != repository.strip()
            or calendar_window is not None
            or self.calendar_date is not None
        ):
            raise ValueError(
                "matched GitHub intent requires one repository_reference."
            )


@dataclass(frozen=True, slots=True)
class ChatPluginActionBinding:
    """Non-authoritative correlation from one D45 ticket to one chat turn."""

    approval_id: str
    conversation_id: UUID
    repository_reference: str | None
    expires_at: datetime
    calendar_window: CalendarChatWindow | None = None
    calendar_date: date | None = None
    calendar_window_start: datetime | None = None
    calendar_window_end: datetime | None = None
    gmail_query: GmailReadQuery | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.approval_id, str)
            or not self.approval_id
            or self.approval_id != self.approval_id.strip()
        ):
            raise ValueError("approval_id must be a non-empty trimmed string.")
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware.")
        if self.gmail_query is not None and not isinstance(
            self.gmail_query, GmailReadQuery
        ):
            raise TypeError("gmail_query must be a GmailReadQuery.")

        repository = self.repository_reference
        calendar = self.calendar_window is not None
        gmail = self.gmail_query is not None
        if sum((repository is not None, calendar, gmail)) != 1:
            raise ValueError(
                "Plugin binding requires exactly one connector target."
            )

        if repository is not None:
            if (
                not isinstance(repository, str)
                or not repository
                or repository != repository.strip()
            ):
                raise ValueError(
                    "repository_reference must be a non-empty trimmed string."
                )
            if (
                self.calendar_window is not None
                or self.calendar_date is not None
                or self.calendar_window_start is not None
                or self.calendar_window_end is not None
                or self.gmail_query is not None
            ):
                raise ValueError(
                    "GitHub bindings must not carry Calendar or Gmail metadata."
                )
            return

        if gmail:
            if (
                self.calendar_window is not None
                or self.calendar_date is not None
                or self.calendar_window_start is not None
                or self.calendar_window_end is not None
            ):
                raise ValueError(
                    "Gmail bindings must not carry Calendar window metadata."
                )
            return

        if self.calendar_window not in _CALENDAR_WINDOWS:
            raise ValueError(
                "Calendar bindings require one supported calendar_window."
            )
        if self.calendar_window == "exact_date":
            if type(self.calendar_date) is not date:
                raise ValueError(
                    "exact-date Calendar bindings require one Gregorian date."
                )
        elif self.calendar_date is not None:
            raise ValueError(
                "relative Calendar bindings must not carry calendar_date."
            )
        if (
            not isinstance(self.calendar_window_start, datetime)
            or not isinstance(self.calendar_window_end, datetime)
            or self.calendar_window_start.tzinfo is None
            or self.calendar_window_start.utcoffset() is None
            or self.calendar_window_end.tzinfo is None
            or self.calendar_window_end.utcoffset() is None
            or self.calendar_window_end <= self.calendar_window_start
        ):
            raise ValueError(
                "Calendar bindings require one valid timezone-aware window."
            )


@dataclass(frozen=True, slots=True)
class ChatPluginActionCompletion:
    """Safe final Chat message derived from an already-decided D45 outcome."""

    conversation_id: UUID
    reply: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if (
            not isinstance(self.reply, str)
            or not self.reply
            or self.reply != self.reply.strip()
        ):
            raise ValueError("reply must be a non-empty trimmed string.")
