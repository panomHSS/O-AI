class RetrievalPipeline:
    """Builds KnowledgeContext from the incoming request."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError