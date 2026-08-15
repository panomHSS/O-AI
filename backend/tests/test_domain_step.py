import unittest

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.protocols import DomainStep


class FakeStep:
    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        context.response.answer = "done"


class DomainStepTests(unittest.TestCase):

    def test_fake_step_satisfies_protocol(self) -> None:
        step: DomainStep = FakeStep()

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

        step.execute(context)

        self.assertEqual(
            context.response.answer,
            "done",
        )


if __name__ == "__main__":
    unittest.main()