"""Closed vocabulary for Project action execution capabilities."""


class ProjectActionExecutionCapabilities:
    """Define the capability names recognized by Project execution."""

    _SUPPORTED = frozenset(
        {
            "PROJECT_ACTION",
        }
    )
    
    def is_supported(
        self,
        capability: object,
    ) -> bool:
        return capability in self._SUPPORTED