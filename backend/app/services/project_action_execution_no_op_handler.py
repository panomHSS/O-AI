"""Handle NO_OP Project action execution steps."""


from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)

class ProjectActionExecutionNoOpHandler:
    """Execute a NO_OP action without producing side effects."""

    def execute(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        return None