"""D84 Calendar Write Chat UX correlation and owner-decision contracts.

D84 binds a D73 Calendar write proposal to one Chat conversation.  The binding
is correlation metadata only: it is not D73 approval, D36 authorization, claim,
credential authority, or provider-write authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.google_calendar_write_approval import (
    CalendarWriteApprovalProposal,
)


CalendarWriteChatUXLanguage: TypeAlias = Literal["th", "en"]
CalendarWriteChatUXDecision: TypeAlias = Literal["approved", "denied"]
CalendarWriteChatUXTerminalStatus: TypeAlias = Literal[
    "denied",
    "succeeded",
    "failed",
    "indeterminate",
]

_HEX = frozenset("0123456789abcdef")


def _trimmed(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _digest(value: object) -> str:
    digest = _trimmed(value, label="write_digest")
    if len(digest) != 64 or any(ch not in _HEX for ch in digest):
        raise ValueError("write_digest must be lowercase SHA-256 hex.")
    return digest


def _aware(value: object, *, label: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{label} must be timezone-aware.")
    return value


@dataclass(frozen=True, slots=True)
class CalendarWriteChatBinding:
    """Non-authoritative D84 correlation between one D73 proposal and Chat."""

    approval_id: str
    write_digest: str
    conversation_id: UUID
    language: CalendarWriteChatUXLanguage
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed(self.approval_id, label="approval_id")
        _digest(self.write_digest)
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.language not in {"th", "en"}:
            raise ValueError("language must be th or en.")
        _aware(self.expires_at, label="expires_at")


@dataclass(frozen=True, slots=True)
class CalendarWriteChatProposalOutcome:
    """One owner-visible pending D84 Calendar write proposal."""

    conversation_id: UUID
    status: Literal["pending_approval"]
    reason_code: str
    proposal: CalendarWriteApprovalProposal
    reply: str

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.status != "pending_approval":
            raise ValueError("proposal status must be pending_approval.")
        _trimmed(self.reason_code, label="reason_code")
        if not isinstance(self.proposal, CalendarWriteApprovalProposal):
            raise TypeError("proposal must be CalendarWriteApprovalProposal.")
        _trimmed(self.reply, label="reply")


@dataclass(frozen=True, slots=True)
class CalendarWriteChatDecisionOutcome:
    """Terminal D84 structured owner-decision / execution projection."""

    conversation_id: UUID
    approval_id: str
    write_digest: str
    decision: CalendarWriteChatUXDecision
    status: CalendarWriteChatUXTerminalStatus
    reason_code: str
    reply: str
    event_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        _trimmed(self.approval_id, label="approval_id")
        _digest(self.write_digest)
        if self.decision not in {"approved", "denied"}:
            raise ValueError("decision must be approved or denied.")
        if self.status not in {
            "denied",
            "succeeded",
            "failed",
            "indeterminate",
        }:
            raise ValueError("unsupported D84 terminal status.")
        if self.decision == "denied":
            if self.status != "denied":
                raise ValueError("denied decision must have denied status.")
            if self.event_id is not None:
                raise ValueError("denied decision cannot carry event_id.")
        else:
            if self.status == "denied":
                raise ValueError("approved decision cannot have denied status.")
            if self.status == "succeeded":
                _trimmed(self.event_id, label="event_id")
            elif self.event_id is not None:
                raise ValueError(
                    "failed/indeterminate decision cannot carry event_id."
                )
        _trimmed(self.reason_code, label="reason_code")
        _trimmed(self.reply, label="reply")


__all__ = [
    "CalendarWriteChatBinding",
    "CalendarWriteChatDecisionOutcome",
    "CalendarWriteChatProposalOutcome",
    "CalendarWriteChatUXDecision",
    "CalendarWriteChatUXLanguage",
    "CalendarWriteChatUXTerminalStatus",
]
