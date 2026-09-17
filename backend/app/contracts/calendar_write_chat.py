"""D83 deterministic Calendar write Chat bridge contracts.

D83 constructs only a transient D72 create-event candidate.  These contracts
carry no D73 approval, D36 authorization, credential, connector, or execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
)


CalendarWriteChatDisposition: TypeAlias = Literal[
    "none",
    "supported_create",
    "invalid_create",
    "unsupported_update",
    "unsupported_delete",
]
CalendarWriteChatLanguage: TypeAlias = Literal["th", "en"]


@dataclass(frozen=True, slots=True)
class CalendarWriteChatParseOutcome:
    """One deterministic interpretation result; never an approval."""

    disposition: CalendarWriteChatDisposition
    reason_code: str
    language: CalendarWriteChatLanguage | None = None
    request: GoogleCalendarCreateEventRequest | None = None
    summary: str | None = None
    start_local: datetime | None = None
    end_local: datetime | None = None

    def __post_init__(self) -> None:
        if self.disposition not in {
            "none",
            "supported_create",
            "invalid_create",
            "unsupported_update",
            "unsupported_delete",
        }:
            raise ValueError("Unsupported Calendar write Chat disposition.")
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise ValueError("reason_code must be a non-empty string.")
        if self.language not in {None, "th", "en"}:
            raise ValueError("Unsupported Calendar write Chat language.")

        if self.disposition == "supported_create":
            if not isinstance(self.request, GoogleCalendarCreateEventRequest):
                raise TypeError(
                    "supported_create requires a D72 create request candidate."
                )
            if (
                not isinstance(self.summary, str)
                or not self.summary
                or self.summary != self.summary.strip()
            ):
                raise ValueError(
                    "supported_create requires a trimmed non-empty summary."
                )
            if (
                not isinstance(self.start_local, datetime)
                or self.start_local.tzinfo is None
                or self.start_local.utcoffset() is None
                or not isinstance(self.end_local, datetime)
                or self.end_local.tzinfo is None
                or self.end_local.utcoffset() is None
            ):
                raise ValueError(
                    "supported_create requires timezone-aware local boundaries."
                )
        elif any(
            value is not None
            for value in (
                self.request,
                self.summary,
                self.start_local,
                self.end_local,
            )
        ):
            raise ValueError(
                "Only supported_create may carry a D72 request candidate."
            )


@dataclass(frozen=True, slots=True)
class CalendarWriteChatTurnOutcome:
    """Owner-visible deterministic D83 turn result."""

    conversation_id: UUID
    disposition: CalendarWriteChatDisposition
    reason_code: str
    reply: str
    request: GoogleCalendarCreateEventRequest | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.disposition == "none":
            raise ValueError("A handled D83 turn cannot have disposition none.")
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise ValueError("reason_code must be a non-empty string.")
        if (
            not isinstance(self.reply, str)
            or not self.reply
            or self.reply != self.reply.strip()
        ):
            raise ValueError("reply must be a non-empty trimmed string.")
        if (
            self.disposition == "supported_create"
            and not isinstance(self.request, GoogleCalendarCreateEventRequest)
        ):
            raise TypeError(
                "supported_create turn requires a transient D72 candidate."
            )
        if self.disposition != "supported_create" and self.request is not None:
            raise ValueError(
                "Only supported_create may carry a transient D72 candidate."
            )


__all__ = [
    "CalendarWriteChatDisposition",
    "CalendarWriteChatLanguage",
    "CalendarWriteChatParseOutcome",
    "CalendarWriteChatTurnOutcome",
]
