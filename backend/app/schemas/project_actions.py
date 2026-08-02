from typing import Literal

from pydantic import BaseModel, Field


ProjectActionStatus = Literal[
    "suggestion_available",
    "no_explicit_action",
]


class SuggestedProjectAction(BaseModel):
    """An owner-reviewable Project action; never an execution command."""

    description: str = Field(min_length=1, max_length=300)


class ProjectActionAnalysis(BaseModel):
    """Read-only analysis of the Project's explicit next action."""

    status: ProjectActionStatus
    project_revision: int = Field(ge=1)
    owner_approval_required: bool
    suggested_actions: list[SuggestedProjectAction] = Field(
        default_factory=list
    )