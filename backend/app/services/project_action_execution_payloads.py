"""Payload contracts for Project action execution."""


class ProjectActionExecutionPayloads:
    """Validate payload shapes for officially supported action types."""

    def is_valid(
        self,
        action_type: str,
        payload: object,
    ) -> bool:
        if action_type == "NO_OP":
            return (
                isinstance(payload, dict)
                and payload == {}
            )

        if action_type == "PROJECT_SET_OBJECTIVE":
            if not isinstance(payload, dict):
                return False

            if set(payload.keys()) != {
                "objective",
            }:
                return False

            objective = payload.get(
                "objective"
            )

            return (
                isinstance(objective, str)
                and bool(objective.strip())
            )

        return False