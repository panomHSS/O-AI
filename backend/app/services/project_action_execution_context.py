"""Define trusted context for Project action execution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectActionExecutionContext:
    """Carry trusted proposal metadata with one execution step."""

    proposal_id: str
    project_id: str
    project_revision: int
    step: dict