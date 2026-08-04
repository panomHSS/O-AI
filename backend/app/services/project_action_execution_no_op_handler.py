"""Handle NO_OP Project action execution steps."""


class ProjectActionExecutionNoOpHandler:
    """Execute a NO_OP action without producing side effects."""

    def execute(
        self,
        step: dict,
    ) -> None:
        return None