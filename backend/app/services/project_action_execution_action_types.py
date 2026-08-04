"""Closed vocabulary for Project action execution action types."""


class ProjectActionExecutionActionTypes:
    """Define the action type names recognized by Project execution."""

    _SUPPORTED = frozenset(
        {
            "NO_OP",
        }
    )
    def is_supported(
        self,
        action_type: object,
    ) -> bool:
        return action_type in self._SUPPORTED