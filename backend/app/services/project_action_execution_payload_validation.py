"""Payload validation for Project action execution proposals."""

from app.services.project_action_execution_payloads import (
    ProjectActionExecutionPayloads,
)


class ProjectActionExecutionPayloadValidator:
    """Allow execution only when every step has a valid action payload."""

    def __init__(
        self,
        payloads: ProjectActionExecutionPayloads | None = None,
    ) -> None:
        self._payloads = (
            payloads
            if payloads is not None
            else ProjectActionExecutionPayloads()
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
            payload = step.get(
                "payload"
            )

            if not self._payloads.is_valid(
                action_type,
                payload,
            ):
                raise ValueError(
                    "Invalid execution action payload."
                )