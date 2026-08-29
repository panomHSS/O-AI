from app.intelligence.context import ExecutionContext

from .base import Pipeline


class RetrievalPipeline(Pipeline):
    """Builds KnowledgeContext from the incoming request."""

    def __init__(
        self,
        analyzer,
        planner,
        repository,
        candidates_per_query,
    ) -> None:
        self._analyzer = analyzer
        self._planner = planner
        self._repository = repository
        self._candidates_per_query = candidates_per_query

    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Execute retrieval pipeline."""

        self._retrieve_records(
            execution_context,
        )

    def _retrieve_records(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Populate retrieval records into the execution context."""

        question = execution_context.request.question

        intent = self._analyzer.analyze(
            question,
        )

        queries = self._planner.plan(
            intent,
        )

        records = []
        seen = set()

        for query in queries:
            normalized_query = " ".join(query.split())

            if not normalized_query:
                continue

            for item in self._repository.search(
                normalized_query,
                self._candidates_per_query,
            ):
                if item["chunk_id"] not in seen:
                    records.append(item)
                    seen.add(item["chunk_id"])

        execution_context.knowledge.intent = intent
        execution_context.knowledge.queries = queries
        execution_context.knowledge.records = records