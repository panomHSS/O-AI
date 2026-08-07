"""Execute a Project objective update action."""

from typing import Protocol

from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectObjectiveWriter(Protocol):
    """Persist a Project objective change."""

    def set_objective(
        self,
        project_id: str,
        objective: str,
    ) -> None:
        ...


class ProjectActionExecutionSetObjectiveHandler:
    """Execute a validated PROJECT_SET_OBJECTIVE action."""

    def __init__(
        self,
        *,
        projects: ProjectObjectiveWriter,
    ) -> None:
        self._projects = projects

    def execute(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        payload = context.step[
            "payload"
        ]

        objective = payload[
            "objective"
        ]

        self._projects.set_objective(
            context.project_id,
            objective,
        )