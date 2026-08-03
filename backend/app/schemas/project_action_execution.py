"""Schemas for owner-controlled Project action execution proposals."""

from pydantic import BaseModel, Field

from app.schemas.project_action_planning import (
    ProjectActionPlanStep,
)


class ProjectActionExecutionProposal(BaseModel):
    """A proposed execution that remains blocked on explicit owner approval."""

    status: str
    project_revision: int = Field(ge=1)
    source_action: str
    owner_approval_required: bool
    approved: bool
    executed: bool
    steps: list[ProjectActionPlanStep] = Field(
        default_factory=list
    )