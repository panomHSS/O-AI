"""D73 immutable contracts for Calendar write proposal and owner approval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarUpdateEventRequest,
)


CalendarWriteRequest: TypeAlias = (
    GoogleCalendarCreateEventRequest
    | GoogleCalendarUpdateEventRequest
    | GoogleCalendarDeleteEventRequest
)
CalendarWriteOperation: TypeAlias = Literal[
    "create_event",
    "update_event",
    "delete_event",
]
CalendarWriteDecision: TypeAlias = Literal["approved", "denied"]

_WRITE_REQUEST_TYPES = (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarUpdateEventRequest,
    GoogleCalendarDeleteEventRequest,
)


def _trimmed_text(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _write_request(value: object) -> CalendarWriteRequest:
    if not isinstance(value, _WRITE_REQUEST_TYPES):
        raise TypeError("request must be a D72 Calendar write request.")
    return value


def _write_digest(value: object) -> str:
    digest = _trimmed_text(value, label="write_digest")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef"
        for character in digest
    ):
        raise ValueError(
            "write_digest must be a lowercase SHA-256 hex digest."
        )
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
class CalendarWritePreview:
    """Structured deterministic projection shown to the owner."""

    contract_version: str
    operation: CalendarWriteOperation
    calendar_id: Literal["primary"]
    event_id: str | None = None
    summary: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None
    location: str | None = None
    changed_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _trimmed_text(self.contract_version, label="contract_version")
        if self.operation not in {
            "create_event",
            "update_event",
            "delete_event",
        }:
            raise ValueError("Unsupported Calendar write operation.")
        if self.calendar_id != "primary":
            raise ValueError("Calendar write preview must target primary.")
        if len(set(self.changed_fields)) != len(self.changed_fields):
            raise ValueError("changed_fields must be unique.")


@dataclass(frozen=True, slots=True)
class PendingCalendarWriteApproval:
    """One bounded process-local pending owner decision."""

    approval_id: str
    request: CalendarWriteRequest
    write_digest: str
    preview: CalendarWritePreview
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _write_request(self.request)
        _write_digest(self.write_digest)
        if not isinstance(self.preview, CalendarWritePreview):
            raise TypeError("preview must be a CalendarWritePreview.")
        created_at = _aware(self.created_at, label="created_at")
        expires_at = _aware(self.expires_at, label="expires_at")
        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at.")


@dataclass(frozen=True, slots=True)
class ApprovedCalendarWriteApproval:
    """Exact owner-approved D72 request snapshot; not execution authority."""

    approval_id: str
    request: CalendarWriteRequest
    write_digest: str
    preview: CalendarWritePreview
    approved_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _write_request(self.request)
        _write_digest(self.write_digest)
        if not isinstance(self.preview, CalendarWritePreview):
            raise TypeError("preview must be a CalendarWritePreview.")
        approved_at = _aware(self.approved_at, label="approved_at")
        expires_at = _aware(self.expires_at, label="expires_at")
        if expires_at <= approved_at:
            raise ValueError("expires_at must be later than approved_at.")


@dataclass(frozen=True, slots=True)
class CalendarWriteApprovalProposal:
    """Owner-reviewable preview bound to one exact write digest."""

    approval_id: str
    write_digest: str
    preview: CalendarWritePreview
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _write_digest(self.write_digest)
        if not isinstance(self.preview, CalendarWritePreview):
            raise TypeError("preview must be a CalendarWritePreview.")
        _aware(self.expires_at, label="expires_at")


@dataclass(frozen=True, slots=True)
class CalendarWriteApprovalProposalOutcome:
    """D73 proposal result; a pending proposal grants no execution authority."""

    status: Literal["pending"]
    reason_code: str
    proposal: CalendarWriteApprovalProposal

    def __post_init__(self) -> None:
        if self.status != "pending":
            raise ValueError("Calendar write proposal status must be pending.")
        _trimmed_text(self.reason_code, label="reason_code")
        if not isinstance(self.proposal, CalendarWriteApprovalProposal):
            raise TypeError(
                "proposal must be a CalendarWriteApprovalProposal."
            )


@dataclass(frozen=True, slots=True)
class CalendarWriteApprovalDecisionOutcome:
    """Explicit owner decision with no execution result."""

    approval_id: str
    decision: CalendarWriteDecision
    reason_code: str
    write_digest: str
    preview: CalendarWritePreview
    expires_at: datetime
    approved: ApprovedCalendarWriteApproval | None = None

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        if self.decision not in {"approved", "denied"}:
            raise ValueError("decision must be approved or denied.")
        _trimmed_text(self.reason_code, label="reason_code")
        _write_digest(self.write_digest)
        if not isinstance(self.preview, CalendarWritePreview):
            raise TypeError("preview must be a CalendarWritePreview.")
        _aware(self.expires_at, label="expires_at")
        if self.decision == "approved":
            if self.approved is None:
                raise ValueError(
                    "approved decisions require an approved snapshot."
                )
        elif self.approved is not None:
            raise ValueError(
                "denied decisions must not carry an approved snapshot."
            )


__all__ = [
    "ApprovedCalendarWriteApproval",
    "CalendarWriteApprovalDecisionOutcome",
    "CalendarWriteApprovalProposal",
    "CalendarWriteApprovalProposalOutcome",
    "CalendarWriteDecision",
    "CalendarWriteOperation",
    "CalendarWritePreview",
    "CalendarWriteRequest",
    "PendingCalendarWriteApproval",
]
