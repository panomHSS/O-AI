from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


TrustedExperienceState = Literal[
    "PENDING_REVIEW",
    "TRUSTED",
    "REJECTED",
    "REVOKED",
]
TrustedExperienceEventType = Literal[
    "PROPOSED",
    "APPROVED",
    "REJECTED",
    "REVOKED",
]


class TrustedExperienceDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_comment: str = Field(min_length=1, max_length=2000)

    @field_validator("decision_comment")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("decision_comment must contain non-whitespace text")
        return normalized


class TrustedExperienceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workspace_id: Literal["personal", "company"]
    contract_version: Literal["1"]

    source_candidate_fingerprint: str
    source_feedback_fingerprint: str
    proposal_fingerprint: str

    quality_classification: Literal["verified_success"]
    quality_reason_code: Literal["verified_success"]
    lesson_code: Literal["verified_success"]

    interaction_intent: str
    cognitive_intent: str
    authoritative_ai_task_kind: str
    observed_confidence_class: str

    authorized_adapter_id: str | None
    authorized_model_id: str | None
    authorized_profile_id: str | None
    source_revision_count: int

    state: TrustedExperienceState
    current_revision: int
    created_at: datetime
    updated_at: datetime

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False


class TrustedExperienceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TrustedExperienceResponse]
    page: int
    page_size: int
    total: int


class TrustedExperienceEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int
    event_type: TrustedExperienceEventType
    from_state: TrustedExperienceState | None
    to_state: TrustedExperienceState
    actor: Literal["SYSTEM", "OWNER"]
    decision_comment: str | None
    created_at: datetime


class TrustedExperienceHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trusted_experience_id: UUID
    items: list[TrustedExperienceEventResponse]
