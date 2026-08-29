from __future__ import annotations
from app.intelligence.context import ExecutionContext

class PipelineOrchestrator:
    """Coordinates the execution of all pipelines."""

    def __init__(
        self,
        pipelines: list[Pipeline],
    ) -> None:
        self._pipelines = pipelines

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        for pipeline in self._pipelines:
            pipeline.execute(
                execution_context,
            )