from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ProposalStatus = Literal["PENDING", "APPLIED", "REJECTED", "STALE"]
ProposalReason = Annotated[str, Field(min_length=1, max_length=512)]


class CreateProjectUpdateProposalRequest(BaseModel):
    project_id: UUID
    conversation_id: UUID
    base_revision: int = Field(ge=1)
    proposed_summary: str | None = Field(default=None, max_length=4000)
    proposed_next_action: str | None = Field(default=None, max_length=512)
    reason: ProposalReason

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must contain non-whitespace text.")
        return normalized

    @field_validator("proposed_summary")
    @classmethod
    def normalize_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("proposed_next_action")
    @classmethod
    def normalize_next_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProjectUpdateProposalResponse(BaseModel):
    id: UUID
    project_id: UUID
    conversation_id: UUID
    base_revision: int
    proposed_summary: str | None
    proposed_next_action: str | None
    reason: str
    status: ProposalStatus
    created_at: datetime
    decided_at: datetime | None
    applied_revision: int | None


class ProjectUpdateProposalListResponse(BaseModel):
    items: list[ProjectUpdateProposalResponse]