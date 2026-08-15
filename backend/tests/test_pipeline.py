import unittest

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.pipeline.pipeline import Pipeline


class FirstStep:
    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        context.response.answer += "A"


class SecondStep:
    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        context.response.answer += "B"


class PipelineTests(unittest.TestCase):

    def test_pipeline_executes_steps_in_order(self) -> None:
        pipeline = Pipeline(
            [
                FirstStep(),
                SecondStep(),
            ]
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

        pipeline.run(context)

        self.assertEqual(
            context.response.answer,
            "AB",
        )


if __name__ == "__main__":
    unittest.main()