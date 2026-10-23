from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TrustedExecutionExperienceState = Literal["TRUSTED", "REVOKED"]
TrustedExecutionExperienceEventType = Literal["OWNER_PROMOTED", "OWNER_REVOKED"]
ExecutionExperienceTrustEligibility = Literal[
    "eligible_for_owner_promotion",
    "ineligible",
    "invalid_evidence",
]


class ExecutionExperienceTrustPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_record_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    promotion_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class TrustedExecutionExperienceRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    promotion_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ExecutionExperienceTrustPromotionProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: Literal["personal", "company"]
    conversation_id: UUID
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    approval_id: str
    execution_request_id: str
    plan_digest: str
    source_feedback_fingerprint: str
    source_candidate_fingerprint: str
    source_review_fingerprint: str
    source_d186_record_fingerprint: str
    target_kind: Literal["tool", "module"]
    capability_id: str
    adapter_id: str
    operation: str
    effect: Literal["none", "read"]
    risk_class: Literal["R0"]
    source_classification: Literal["execution_succeeded"]
    experience_outcome_class: Literal["success"]
    experience_lesson_code: Literal["authorized_execution_succeeded"]
    review_reason_code: Literal["authorized_execution_succeeded"]
    promotion_fingerprint: str
    contract_version: Literal["o-ai.governed-execution-experience-trust.v1"]

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False


class ExecutionExperienceTrustEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID
    eligibility: ExecutionExperienceTrustEligibility
    reason_code: Literal[
        "review_accepted",
        "review_not_accepted",
        "invalid_evidence",
    ]
    proposal: ExecutionExperienceTrustPromotionProposalResponse | None


class TrustedExecutionExperienceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workspace_id: Literal["personal", "company"]
    source_review_id: UUID
    conversation_id: UUID
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    approval_id: str
    execution_request_id: str
    plan_digest: str
    source_feedback_fingerprint: str
    source_candidate_fingerprint: str
    source_review_fingerprint: str
    source_d186_record_fingerprint: str
    target_kind: Literal["tool", "module"]
    capability_id: str
    adapter_id: str
    operation: str
    effect: Literal["none", "read"]
    risk_class: Literal["R0"]
    source_classification: Literal["execution_succeeded"]
    experience_outcome_class: Literal["success"]
    experience_lesson_code: Literal["authorized_execution_succeeded"]
    review_reason_code: Literal["authorized_execution_succeeded"]
    promotion_fingerprint: str
    contract_version: Literal["o-ai.governed-execution-experience-trust.v1"]
    state: TrustedExecutionExperienceState
    current_revision: int
    created_at: datetime
    updated_at: datetime

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False


class TrustedExecutionExperienceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TrustedExecutionExperienceResponse]
    page: int
    page_size: int
    total: int


class TrustedExecutionExperienceEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int
    event_type: TrustedExecutionExperienceEventType
    from_state: TrustedExecutionExperienceState | None
    to_state: TrustedExecutionExperienceState
    actor: Literal["OWNER"]
    created_at: datetime


class TrustedExecutionExperienceHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trusted_execution_experience_id: UUID
    items: list[TrustedExecutionExperienceEventResponse]
