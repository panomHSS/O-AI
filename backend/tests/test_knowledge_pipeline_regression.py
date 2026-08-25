import unittest

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.orchestrator import KnowledgeOrchestrator
from app.intelligence.steps.retrieval_step import RetrievalStep
from app.intelligence.steps.evidence_step import EvidenceStep


class FakePipeline:
    def __init__(self) -> None:
        self.called = False

    def run(
        self,
        context: ExecutionContext,
    ) -> None:
        self.called = True
        context.response.answer = "pipeline"


class KnowledgeOrchestratorTests(unittest.TestCase):

    def test_execute_runs_pipeline(self) -> None:
        pipeline = FakePipeline()

        orchestrator = KnowledgeOrchestrator(
            pipeline,
        )

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="Hello",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        orchestrator.execute(
            context,
        )

        self.assertTrue(
            pipeline.called,
        )

        self.assertEqual(
            context.response.answer,
            "pipeline",
        )
class FakeIntent:
    def __init__(self) -> None:
        self.question = "boiler"
        self.important_terms = ["boiler"]


class FakeAnalyzer:
    def analyze(self, question: str):
        return FakeIntent()


class FakePlanner:
    def plan(self, intent):
        return ["boiler"]


class FakeRepository:
    def search(self, query: str, limit: int):
        return [
            {
                "chunk_id": "1",
                "content": "Boiler efficiency",
            }
        ]
class RetrievalStepTests(unittest.TestCase):

    def test_execute_populates_execution_context(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="How does a boiler work?",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        step = RetrievalStep(
            repository=FakeRepository(),
            analyzer=FakeAnalyzer(),
            planner=FakePlanner(),
            candidates_per_query=5,
        )

        step.execute(context)

        self.assertIsNotNone(
            context.knowledge.intent,
        )

        self.assertEqual(
            context.knowledge.queries,
            ["boiler"],
        )

        self.assertEqual(
            len(context.knowledge.records),
            1,
        )
class FakeEvidence:
    def __init__(self) -> None:
        self.document_id = "doc-001"
        self.chunk_id = "chunk-001"
        self.file_name = "manual.pdf"
        self.source_path = "/manual.pdf"
        self.source_locator = "P1"
        self.content = "Boiler efficiency"

        self.fts_score = 0.80
        self.file_extension = ".pdf"

        self.score = 0.95

class FakeRanker:
    def rank(
        self,
        question,
        terms,
        records,
    ):
        return (
            [FakeEvidence()],
            2,
            3,
        )


class FakeConflictDetector:
    def detect(
        self,
        selected,
        important_terms,
    ):
        return []


class FakeContextBuilder:
    def build(
        self,
        selected,
    ):
        return selected
class EvidenceStepTests(unittest.TestCase):

    def test_execute_stores_rank_results(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="boiler",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        context.knowledge.intent = FakeIntent()
        context.knowledge.records = [
            {
                "chunk_id": "1",
            }
        ]

        step = EvidenceStep(
            ranker=FakeRanker(),
            conflict_detector=FakeConflictDetector(),
            context_builder=FakeContextBuilder(),
            selected_limit=5,
        )

        step.execute(context)

        self.assertEqual(
            context.knowledge.duplicates_removed,
            2,
        )

        self.assertEqual(
            context.knowledge.filtered_out,
            3,
        )

        self.assertEqual(
            len(context.knowledge.evidence),
            1,
        )
       
if __name__ == "__main__":
    unittest.main()