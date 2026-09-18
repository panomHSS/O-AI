"""D88 transport schemas for explicit local-owner Gmail send execution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.gmail_send_execution import GmailSendExecutionOutcome


class GmailSendExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1, max_length=128)
    send_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class GmailSendExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    send_digest: str
    status: Literal["succeeded", "failed", "indeterminate"]
    reason_code: str
    provider_attempted: bool
    message_id: str | None = None

    @classmethod
    def from_outcome(
        cls,
        outcome: GmailSendExecutionOutcome,
    ) -> "GmailSendExecutionResponse":
        return cls(
            approval_id=outcome.approval_id,
            send_digest=outcome.send_digest,
            status=outcome.status,
            reason_code=outcome.reason_code,
            provider_attempted=outcome.provider_attempted,
            message_id=outcome.message_id,
        )


__all__ = [
    "GmailSendExecutionRequest",
    "GmailSendExecutionResponse",
]
