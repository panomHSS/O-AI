class PipelineOrchestrator:
    """Coordinates the execution of all pipelines."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError