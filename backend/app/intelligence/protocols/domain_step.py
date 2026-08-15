from typing import Protocol

from app.intelligence.context import ExecutionContext


class DomainStep(Protocol):
    """Contract implemented by every intelligence pipeline step."""

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        """Mutate the shared execution context."""