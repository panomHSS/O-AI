from .base import Pipeline

class RetrievalPipeline:
    """Builds KnowledgeContext from the incoming request."""
    def __init__(
            self,
            knowledge_service,
        ) -> None:
            self._knowledge = knowledge_service

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Execute retrieval pipeline."""

    def _retrieve_records(
        self,
        execution_context: ExecutionContext,
    ) -> None:
            """Populate retrieval records into the execution context."""
            return

            self._retrieve_records(
                execution_context,
            )