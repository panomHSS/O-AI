"""Capability validation for Project action execution proposals."""

from collections.abc import Iterable


class ProjectActionExecutionCapabilityValidator:
    """Allow execution only when every step uses a supported capability."""

    def __init__(
        self,
        supported_capabilities: Iterable[str],
    ) -> None:
        self._supported_capabilities = frozenset(
            supported_capabilities
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

            if capability not in self._supported_capabilities:
                raise ValueError(
                    "Unsupported execution capability."
                )
        for step in proposal.steps:
            capability = step.get(
                "capability"
            )

            if capability not in self._supported_capabilities:
                raise ValueError(
                    "Unsupported execution capability."
                )