"""Capability validation for Project action execution proposals."""

from app.services.project_action_execution_capabilities import (
    ProjectActionExecutionCapabilities,
)


class ProjectActionExecutionCapabilityValidator:
    """Allow execution only for officially supported capabilities."""

    def __init__(
        self,
        capabilities: ProjectActionExecutionCapabilities | None = None,
    ) -> None:
        self._capabilities = (
            capabilities
            if capabilities is not None
            else ProjectActionExecutionCapabilities()
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
            capability = step.get(
                "capability"
            )

            if not self._capabilities.is_supported(
                capability
            ):
                raise ValueError(
                    "Unsupported execution capability."
                )