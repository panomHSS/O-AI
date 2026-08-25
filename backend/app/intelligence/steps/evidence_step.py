from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep
from app.services.knowledge_intelligence import (
    ConflictDetector,
    ContextBuilder,
    Evidence,
    EvidenceRanker,
)

class EvidenceStep(DomainStep):
    """Ranks and prepares evidence."""

    def __init__(
        self,
        ranker: EvidenceRanker,
        conflict_detector: ConflictDetector,
        context_builder: ContextBuilder,
        selected_limit: int,
    ) -> None:
        self._ranker = ranker
        self._conflicts = conflict_detector
        self._context = context_builder
        self._selected_limit = selected_limit

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:          
        """Populate ranked evidence in the execution context."""

        intent = context.knowledge.intent

        if intent is None:
            return

        selected, duplicates, filtered = self._ranker.rank(
            intent.question,
            intent.important_terms,
            context.knowledge.records,
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

        context.knowledge.evidence = selected
        context.knowledge.duplicates_removed = duplicates
        context.knowledge.filtered_out = filtered

        conflicts = self._conflicts.detect(
            selected,
            intent.important_terms,
        )

        context.knowledge.conflicts = conflicts    

        built_context = self._context.build(
            selected,
        )

        context.knowledge.context = built_context    