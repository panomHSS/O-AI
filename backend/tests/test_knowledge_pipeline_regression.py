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


if __name__ == "__main__":
    unittest.main()