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
if __name__ == "__main__":
    unittest.main()