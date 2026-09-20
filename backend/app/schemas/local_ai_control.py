"""Public D103 Local AI owner-control schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.contracts.local_ai_control import (
    LocalAIControlExecutionOutcome,
    LocalAIControlPreview,
    LocalAIControlProposalOutcome,
)


class LocalAIControlProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal[
        "load_configured_model",
        "unload_configured_model",
    ]


class LocalAIControlDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "denied"]
    control_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class LocalAIControlPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"]
    operation: Literal[
        "load_configured_model",
        "unload_configured_model",
    ]
    backend_id: str
    configured_model_id: str
    expected_loaded_state: StrictBool
    desired_loaded_state: StrictBool

    @classmethod
    def from_contract(
        cls,
        preview: LocalAIControlPreview,
    ) -> "LocalAIControlPreviewResponse":
        return cls(
            contract_version=preview.contract_version,
            operation=preview.operation,
            backend_id=preview.backend_id,
            configured_model_id=preview.configured_model_id,
            expected_loaded_state=preview.expected_loaded_state,
            desired_loaded_state=preview.desired_loaded_state,
        )


class LocalAIControlProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending"]
    reason_code: str
    proposal_id: str
    control_digest: str
    preview: LocalAIControlPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: LocalAIControlProposalOutcome,
    ) -> "LocalAIControlProposalResponse":
        proposal = outcome.proposal
        return cls(
            status=outcome.status,
            reason_code=outcome.reason_code,
            proposal_id=proposal.approval_id,
            control_digest=proposal.control_digest,
            preview=LocalAIControlPreviewResponse.from_contract(
                proposal.preview
            ),
            expires_at=proposal.expires_at,
        )


class LocalAIControlDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "denied"]
    status: Literal[
        "not_executed",
        "succeeded",
        "failed",
        "indeterminate",
    ]
    reason_code: str
    proposal_id: str
    control_digest: str
    preview: LocalAIControlPreviewResponse
    expires_at: datetime

    @classmethod
    def from_outcome(
        cls,
        outcome: LocalAIControlExecutionOutcome,
    ) -> "LocalAIControlDecisionResponse":
        return cls(
            decision=outcome.decision,
            status=outcome.status,
            reason_code=outcome.reason_code,
            proposal_id=outcome.approval_id,
            control_digest=outcome.control_digest,
            preview=LocalAIControlPreviewResponse.from_contract(
                outcome.preview
            ),
            expires_at=outcome.expires_at,
        )
