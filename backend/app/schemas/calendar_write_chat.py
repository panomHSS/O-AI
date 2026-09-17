from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.calendar_write_chat_ux import (
    CalendarWriteChatDecisionOutcome,
    CalendarWriteChatProposalOutcome,
)
from app.schemas.calendar_write_approvals import CalendarWritePreviewResponse


class CalendarWriteChatProposalResponse(BaseModel):
    'Non-authoritative D84 proposal projection for normal Chat.'

    model_config = ConfigDict(extra="forbid")

    status: Literal["pending_approval"]
    reason_code: str
    approval_id: str
    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    preview: CalendarWritePreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarWriteChatProposalOutcome,
    ) -> "CalendarWriteChatProposalResponse":
        proposal = outcome.proposal
        return cls(
            status=outcome.status,
            reason_code=outcome.reason_code,
            approval_id=proposal.approval_id,
            write_digest=proposal.write_digest,
            preview=CalendarWritePreviewResponse.from_contract(proposal.preview),
            expires_at=proposal.expires_at,
        )


class CalendarWriteChatDecisionRequest(BaseModel):
    'Structured D84 owner decision input; conversation is server-bound.'

    model_config = ConfigDict(extra="forbid")

    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class CalendarWriteChatDecisionResponse(BaseModel):
    'Terminal D84 projection of the existing D73/D74 path.'

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    approval_id: str
    write_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    decision: Literal["approved", "denied"]
    status: Literal["denied", "succeeded", "failed", "indeterminate"]
    reason_code: str
    reply: str
    event_id: str | None = None

    @classmethod
    def from_outcome(
        cls,
        outcome: CalendarWriteChatDecisionOutcome,
    ) -> "CalendarWriteChatDecisionResponse":
        return cls(
            conversation_id=outcome.conversation_id,
            approval_id=outcome.approval_id,
            write_digest=outcome.write_digest,
            decision=outcome.decision,
            status=outcome.status,
            reason_code=outcome.reason_code,
            reply=outcome.reply,
            event_id=outcome.event_id,
        )
