import unittest

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)

class ExecutionContextTests(unittest.TestCase):

    def test_create_execution_context(self) -> None:
        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="What is a centrifugal pump?",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        self.assertEqual(
            context.request.request_id,
            "req-001",
        )

        self.assertEqual(
            context.request.question,
            "What is a centrifugal pump?",
        )

        self.assertEqual(
            context.knowledge.evidence,
            [],
        )

        self.assertEqual(
            context.response.answer,
            "",
        )

    def test_model_dump(self) -> None:
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

        payload = context.model_dump()

        self.assertIn("request", payload)
        self.assertIn("knowledge", payload)
        self.assertIn("intelligence", payload)
        self.assertIn("response", payload)


if __name__ == "__main__":
    unittest.main()