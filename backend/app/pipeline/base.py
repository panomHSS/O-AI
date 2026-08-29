from abc import ABC, abstractmethod

from app.intelligence.context import ExecutionContext


class Pipeline(ABC):
    """Base contract for all execution pipelines."""

    @abstractmethod
    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Execute the pipeline and update the shared execution context."""
        ...