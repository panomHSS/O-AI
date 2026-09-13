import unittest

from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Response,
    Result,
)


class CommandContractTests(unittest.TestCase):
    def test_command_contracts_form_the_v1_pipeline(self) -> None:
        request = CommandRequest(
            request_id="request-1",
            command="summarize",
            arguments={"document_id": "document-1"},
        )
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id="documents",
            steps=(
                ExecutionStep(sequence=1, operation="read"),
                ExecutionStep(sequence=2, operation="summarize"),
            ),
        )
        result = Result(
            request_id=plan.request_id,
            status="succeeded",
            output={"summary": "done"},
        )
        response = Response(
            request_id=result.request_id,
            message="Command completed.",
            result=result,
        )

        self.assertEqual(response.request_id, request.request_id)
        self.assertEqual(response.result.status, "succeeded")
        self.assertEqual(len(plan.steps), 2)
        self.assertTrue(plan.owner_approval_required)

    def test_execution_plan_requires_owner_approval_by_default(self) -> None:
        plan = ExecutionPlan(
            request_id="request-1",
            adapter_id="documents",
        )

        self.assertTrue(plan.owner_approval_required)
        self.assertEqual(plan.steps, ())

    def test_command_contracts_are_immutable(self) -> None:
        request = CommandRequest(request_id="request-1", command="inspect")

        with self.assertRaises(AttributeError):
            request.command = "execute"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
