from .base import Pipeline

class PipelineOrchestrator:
    """Coordinates the execution of all pipelines."""

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        for pipeline in self._pipelines:
            pipeline.execute(
                execution_context,
            )

    def __init__(
            self,
            pipelines: list[Pipeline],
        ) -> None:
            self._pipelines = pipelines    