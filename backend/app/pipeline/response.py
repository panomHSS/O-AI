class ResponsePipeline:
    """Builds the final API response."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError