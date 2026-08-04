"""Payload contracts for Project action execution."""


class ProjectActionExecutionPayloads:
    """Validate payload shapes for officially supported action types."""

    def is_valid(
        self,
        action_type: object,
        payload: object,
    ) -> bool:
        if action_type == "NO_OP":
            return (
                isinstance(payload, dict)
                and len(payload) == 0
            )