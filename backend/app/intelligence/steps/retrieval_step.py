from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep
from app.repositories.knowledge import KnowledgeRepository
from app.services.knowledge_intelligence import (
    IntentAnalyzer,
    RetrievalPlanner,
)


class RetrievalStep(DomainStep):
    """Retrieves knowledge records for the execution context."""

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        """Populate retrieval information in the execution context."""

        question = context.request.question

        intent = self._analyzer.analyze(
            question,
        )

        queries = self._planner.plan(
            intent,
        )

        context.knowledge.queries = queries
        records = []
        seen = set()

        for query in queries:
            normalized_query = " ".join(
                query.split(),
            )

            if not normalized_query:
                continue

            for item in self._repository.search(
                normalized_query,
                self._candidates_per_query,
            ):
                if item["chunk_id"] not in seen:
                    records.append(item)
                    seen.add(item["chunk_id"])

        context.knowledge.records = records


    def __init__(
        self,
        repository: KnowledgeRepository,
        analyzer: IntentAnalyzer,
        planner: RetrievalPlanner,
        candidates_per_query: int,
    ) -> None:
        self._repository = repository
        self._analyzer = analyzer
        self._planner = planner
        self._candidates_per_query = candidates_per_query
    