"""Structured, owner-controlled Project action planning contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProjectActionPlanStep(BaseModel):
    """One ordered planning step; it does not represent execution."""

    sequence: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=300)


class ProjectActionPlan(BaseModel):
    """Ephemeral plan derived from the current Project action."""

    status: Literal[
        "plan_available",
        "no_plan_available",
    ]
    project_revision: int = Field(ge=1)
    source_action: str | None = Field(
        default=None,
        max_length=300,
    )
    owner_approval_required: bool
    steps: list[ProjectActionPlanStep] = Field(
        default_factory=list
    )