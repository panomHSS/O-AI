"""D87 API schemas for Gmail send proposal and explicit owner approval."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest
from app.contracts.gmail_send_approval import (
    GmailSendApprovalDecisionOutcome,
    GmailSendApprovalProposalOutcome,
    GmailSendPreview,
)


class GmailSendApprovalRequest(BaseModel):
    """Transport input converted into one authoritative D86 request."""

    model_config = ConfigDict(extra="forbid")

    recipient: str
    subject: str
    body: str


class GmailSendApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    send_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class GmailSendPreviewResponse(BaseModel):
    contract_version: Literal["1"]
    operation: Literal["send_message"]
    recipient: str
    subject: str
    body: str

    @classmethod
    def from_contract(
        cls,
        preview: GmailSendPreview,
    ) -> "GmailSendPreviewResponse":
        return cls(
            contract_version=preview.contract_version,
            operation=preview.operation,
            recipient=preview.recipient,
            subject=preview.subject,
            body=preview.body,
        )


class GmailSendApprovalProposalResponse(BaseModel):
    status: Literal["pending"]
    reason_code: str
    approval_id: str
    send_digest: str
    preview: GmailSendPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: GmailSendApprovalProposalOutcome,
    ) -> "GmailSendApprovalProposalResponse":
        proposal = outcome.proposal
        return cls(
            status=outcome.status,
            reason_code=outcome.reason_code,
            approval_id=proposal.approval_id,
            send_digest=proposal.send_digest,
            preview=GmailSendPreviewResponse.from_contract(
                proposal.preview
            ),
            expires_at=proposal.expires_at,
        )


class GmailSendApprovalDecisionResponse(BaseModel):
    status: Literal["approved", "denied"]
    reason_code: str
    approval_id: str
    send_digest: str
    preview: GmailSendPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: GmailSendApprovalDecisionOutcome,
    ) -> "GmailSendApprovalDecisionResponse":
        return cls(
            status=outcome.decision,
            reason_code=outcome.reason_code,
            approval_id=outcome.approval_id,
            send_digest=outcome.send_digest,
            preview=GmailSendPreviewResponse.from_contract(
                outcome.preview
            ),
            expires_at=outcome.expires_at,
        )


def to_gmail_send_request(
    payload: GmailSendApprovalRequest,
) -> GmailSendRequest:
    """Construct the authoritative immutable D86 request from transport input."""
    return GmailSendRequest(
        message=GmailSendDraft(
            recipient=payload.recipient,
            subject=payload.subject,
            body=payload.body,
        )
    )


__all__ = [
    "GmailSendApprovalDecisionRequest",
    "GmailSendApprovalDecisionResponse",
    "GmailSendApprovalProposalResponse",
    "GmailSendApprovalRequest",
    "GmailSendPreviewResponse",
    "to_gmail_send_request",
]
