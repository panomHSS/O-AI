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

        # D14 Bridge
        return
