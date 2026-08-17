from app.intelligence.context import ExecutionContext
from app.intelligence.pipeline.pipeline import Pipeline


class KnowledgeOrchestrator:
    """Coordinates the knowledge answer pipeline."""

    def __init__(
        self,
        pipeline: Pipeline,
    ) -> None:
        self._pipeline = pipeline

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        self._pipeline.run(context)