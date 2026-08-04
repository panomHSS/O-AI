"""Action type validation for Project action execution proposals."""

from app.services.project_action_execution_action_types import (
    ProjectActionExecutionActionTypes,
)


class ProjectActionExecutionActionTypeValidator:
    """Allow execution only for officially supported action types."""

    def __init__(
        self,
        action_types: ProjectActionExecutionActionTypes | None = None,
    ) -> None:
        self._action_types = (
            action_types
            if action_types is not None
            else ProjectActionExecutionActionTypes()
        )

    def validate(
        self,
        proposal,
    ) -> None:
        if not proposal.steps:
            raise ValueError(
                "Execution proposal must contain at least one step."
            )

        for step in proposal.steps:
            action_type = step.get(
                "action_type"
            )

            if not self._action_types.is_supported(
                action_type
            ):
                raise ValueError(
                    "Unsupported execution action type."
                )