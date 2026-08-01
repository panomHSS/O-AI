from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ProjectStatus = Literal["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"]
ProjectTitle = Annotated[str, Field(min_length=1, max_length=160)]
ProjectObjective = Annotated[str, Field(min_length=1, max_length=4000)]
ChangeNote = Annotated[str, Field(min_length=1, max_length=512)]


class ChangeNotedRequest(BaseModel):
    change_note: ChangeNote

    @field_validator("change_note")
    @classmethod
    def normalize_change_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("change_note must contain non-whitespace text.")
        return normalized


class CreateProjectRequest(ChangeNotedRequest):
    title: ProjectTitle
    objective: ProjectObjective
    change_note: ChangeNote = "Owner created project."


class UpdateProjectDetailsRequest(ChangeNotedRequest):
    expected_revision: int = Field(ge=1)
    title: ProjectTitle | None = None
    objective: ProjectObjective | None = None


class RecordProjectProgressRequest(ChangeNotedRequest):
    expected_revision: int = Field(ge=1)
    current_summary: str | None = Field(default=None, max_length=4000)


class ChangeNextActionRequest(ChangeNotedRequest):
    expected_revision: int = Field(ge=1)
    next_action: str | None = Field(default=None, max_length=512)
    @field_validator("next_action")
    @classmethod
    def reject_whitespace_next_action(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("next_action must be non-whitespace text or null.")
        return value.strip() if value is not None else None


class ChangeProjectStatusRequest(ChangeNotedRequest):
    expected_revision: int = Field(ge=1)
    status: ProjectStatus


class ProjectRevisionResponse(BaseModel):
    id: UUID
    revision_number: int
    title: str
    objective: str
    status: ProjectStatus
    current_summary: str | None
    next_action: str | None
    change_note: str
    created_at: datetime


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    objective: str
    status: ProjectStatus
    current_summary: str | None
    next_action: str | None
    current_revision: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    page: int
    page_size: int
    total: int


class ProjectHistoryResponse(BaseModel):
    items: list[ProjectRevisionResponse]


