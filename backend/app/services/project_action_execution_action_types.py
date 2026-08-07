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

"""Define supported Project action execution action types."""


class ProjectActionExecutionActionTypes:
    """Define the official Project action execution action types."""

    _SUPPORTED = frozenset(
        {
            "NO_OP",
            "PROJECT_SET_OBJECTIVE",
        }
    )

    def is_supported(
        self,
        action_type: str,
    ) -> bool:
        return action_type in self._SUPPORTED