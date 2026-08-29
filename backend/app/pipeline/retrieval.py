class RetrievalPipeline:
    """Builds KnowledgeContext from the incoming request."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError

    def __init__(
            self,
            knowledge_service,
        ) -> None:
            self._knowledge = knowledge_service