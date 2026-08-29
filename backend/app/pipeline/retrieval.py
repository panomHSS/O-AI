from app.intelligence.context import ExecutionContext

from .base import Pipeline

from .components import RetrievalComponents


class RetrievalPipeline(Pipeline):
    """Builds KnowledgeContext from the incoming request."""

    def __init__(
        self,
        components: RetrievalComponents,
        repository,
        candidates_per_query,
        selected_limit,
    ) -> None:
        self._analyzer = components.analyzer
        self._planner = components.planner
        self._repository = repository
        self._ranker = components.ranker
        self._conflicts = components.conflict_detector
        self._context = components.context_builder
        self._candidates_per_query = candidates_per_query
        self._selected_limit = selected_limit
                
    def execute(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Execute retrieval pipeline."""

        self._retrieve_records(
            execution_context,
        )
        self._build_evidence(
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

    def _build_evidence(
        self,
        execution_context: ExecutionContext,
    ) -> None:

        knowledge = execution_context.knowledge

        intent = knowledge.intent
        records = knowledge.records

        selected, duplicates, filtered = self._ranker.rank(
            intent.question,
            intent.important_terms,
            records,
        )

        selected = [
            Evidence(
                **{
                    **item.__dict__,
                    "citation_id": f"S{index}",
                }
            )
            for index, item in enumerate(
                selected[: self._selected_limit],
                1,
            )
        ]

        conflicts = self._conflicts.detect(
            selected,
            intent.important_terms,
        )

        context = self._context.build(selected)

        knowledge.evidence = selected
        knowledge.duplicates_removed = duplicates
        knowledge.filtered_out = filtered
        knowledge.conflicts = conflicts
        knowledge.context = context