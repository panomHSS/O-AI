from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep


class ReasoningStep(DomainStep):
    """Executes reasoning for an intelligence request."""

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        """Populate reasoning information in the execution context."""
        raise NotImplementedError