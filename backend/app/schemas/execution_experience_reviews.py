from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ExecutionExperienceReviewState = Literal[
    "PENDING_REVIEW",
    "REVIEW_ACCEPTED",
    "REVIEW_REJECTED",
]
ExecutionExperienceReviewEventType = Literal[
    "PROPOSED",
    "OWNER_ACCEPTED",
    "OWNER_REJECTED",
]


class ExecutionExperienceReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_review_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ExecutionExperienceReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workspace_id: Literal["personal", "company"]
    contract_version: str
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
    record_fingerprint: str
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
    state: ExecutionExperienceReviewState
    current_revision: int
    created_at: datetime
    updated_at: datetime

    execution_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_owner_decision: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False


class ExecutionExperienceReviewListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ExecutionExperienceReviewResponse]
    page: int
    page_size: int
    total: int


class ExecutionExperienceReviewEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int
    event_type: ExecutionExperienceReviewEventType
    from_state: ExecutionExperienceReviewState | None
    to_state: ExecutionExperienceReviewState
    actor: Literal["SYSTEM", "OWNER"]
    created_at: datetime


class ExecutionExperienceReviewHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_experience_review_id: UUID
    items: list[ExecutionExperienceReviewEventResponse]
