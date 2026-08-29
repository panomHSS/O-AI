class PipelineOrchestrator:
    """Coordinates the execution of all pipelines."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError

    def __init__(
            self,
            retrieval: RetrievalPipeline,
            intelligence: IntelligencePipeline,
            response: ResponsePipeline,
        ) -> None:
            self._retrieval = retrieval
            self._intelligence = intelligence
            self._response = response

    