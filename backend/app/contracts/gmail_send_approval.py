"""D87 immutable contracts for Gmail send proposal and owner approval.

D87 approval is local owner intent only. It grants no authorization, credential
access, provider/network access, execution claim, or Gmail send authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.contracts.gmail_send import (
    GMAIL_SEND_CONTRACT_VERSION,
    GMAIL_SEND_OPERATION,
    GmailSendDraft,
    GmailSendRequest,
)


GmailSendDecision = Literal["approved", "denied"]


def _trimmed_text(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _send_request(value: object) -> GmailSendRequest:
    if not isinstance(value, GmailSendRequest):
        raise TypeError("request must be a D86 GmailSendRequest.")
    return value


def _send_digest(value: object) -> str:
    digest = _trimmed_text(value, label="send_digest")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef"
        for character in digest
    ):
        raise ValueError(
            "send_digest must be a lowercase SHA-256 hex digest."
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
class GmailSendPreview:
    """Exact deterministic D86 projection shown to the owner."""

    contract_version: Literal["1"]
    operation: Literal["send_message"]
    recipient: str
    subject: str
    body: str

    def __post_init__(self) -> None:
        if self.contract_version != GMAIL_SEND_CONTRACT_VERSION:
            raise ValueError("gmail_send_preview_contract_version_invalid")
        if self.operation != GMAIL_SEND_OPERATION:
            raise ValueError("gmail_send_preview_operation_invalid")
        GmailSendDraft(
            recipient=self.recipient,
            subject=self.subject,
            body=self.body,
        )


@dataclass(frozen=True, slots=True)
class PendingGmailSendApproval:
    """One bounded process-local pending owner decision."""

    approval_id: str
    request: GmailSendRequest
    send_digest: str
    preview: GmailSendPreview
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _send_request(self.request)
        _send_digest(self.send_digest)
        if not isinstance(self.preview, GmailSendPreview):
            raise TypeError("preview must be a GmailSendPreview.")
        created_at = _aware(self.created_at, label="created_at")
        expires_at = _aware(self.expires_at, label="expires_at")
        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at.")


@dataclass(frozen=True, slots=True)
class ApprovedGmailSendApproval:
    """Exact owner-approved D86 snapshot; not send execution authority."""

    approval_id: str
    request: GmailSendRequest
    send_digest: str
    preview: GmailSendPreview
    approved_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _send_request(self.request)
        _send_digest(self.send_digest)
        if not isinstance(self.preview, GmailSendPreview):
            raise TypeError("preview must be a GmailSendPreview.")
        approved_at = _aware(self.approved_at, label="approved_at")
        expires_at = _aware(self.expires_at, label="expires_at")
        if expires_at <= approved_at:
            raise ValueError("expires_at must be later than approved_at.")


@dataclass(frozen=True, slots=True)
class GmailSendApprovalProposal:
    """Owner-reviewable preview bound to one exact D86 request digest."""

    approval_id: str
    send_digest: str
    preview: GmailSendPreview
    expires_at: datetime

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        _send_digest(self.send_digest)
        if not isinstance(self.preview, GmailSendPreview):
            raise TypeError("preview must be a GmailSendPreview.")
        _aware(self.expires_at, label="expires_at")


@dataclass(frozen=True, slots=True)
class GmailSendApprovalProposalOutcome:
    """D87 proposal result; pending grants no execution/send authority."""

    status: Literal["pending"]
    reason_code: str
    proposal: GmailSendApprovalProposal

    def __post_init__(self) -> None:
        if self.status != "pending":
            raise ValueError("Gmail send proposal status must be pending.")
        _trimmed_text(self.reason_code, label="reason_code")
        if not isinstance(self.proposal, GmailSendApprovalProposal):
            raise TypeError(
                "proposal must be a GmailSendApprovalProposal."
            )


@dataclass(frozen=True, slots=True)
class GmailSendApprovalDecisionOutcome:
    """Explicit owner decision with no execution/provider result."""

    approval_id: str
    decision: GmailSendDecision
    reason_code: str
    send_digest: str
    preview: GmailSendPreview
    expires_at: datetime
    approved: ApprovedGmailSendApproval | None = None

    def __post_init__(self) -> None:
        _trimmed_text(self.approval_id, label="approval_id")
        if self.decision not in {"approved", "denied"}:
            raise ValueError("decision must be approved or denied.")
        _trimmed_text(self.reason_code, label="reason_code")
        _send_digest(self.send_digest)
        if not isinstance(self.preview, GmailSendPreview):
            raise TypeError("preview must be a GmailSendPreview.")
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
    "ApprovedGmailSendApproval",
    "GmailSendApprovalDecisionOutcome",
    "GmailSendApprovalProposal",
    "GmailSendApprovalProposalOutcome",
    "GmailSendDecision",
    "GmailSendPreview",
    "PendingGmailSendApproval",
]
