from .base import Pipeline

class PipelineOrchestrator:
    """Coordinates the execution of all pipelines."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        raise NotImplementedError

    def __init__(
            self,
            pipelines: list[Pipeline],
        ) -> None:
            self._pipelines = pipelines    