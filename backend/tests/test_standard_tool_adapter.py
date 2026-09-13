import unittest

from app.adapters.standard_tool import StandardToolAdapter
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION, ToolAdapter


class StandardToolAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = StandardToolAdapter()
        self.request = CommandRequest(request_id="request-1", command="tool.echo")

    def plan(self, **kwargs: object) -> ExecutionPlan:
        fields: dict[str, object] = {
            "request_id": "request-1",
            "adapter_id": self.adapter.adapter_id,
            "steps": (
                ExecutionStep(
                    sequence=1,
                    operation="echo",
                    parameters={"value": "hello"},
                ),
            ),
            "owner_approval_required": False,
        }
        fields.update(kwargs)
        return ExecutionPlan(**fields)  # type: ignore[arg-type]

    def test_conforms_with_stable_identity(self) -> None:
        self.assertIsInstance(self.adapter, ToolAdapter)
        self.assertEqual(self.adapter.adapter_id, "tool.standard.echo")
        self.assertEqual(self.adapter.tool_name, "standard.echo")
        self.assertEqual(self.adapter.contract_version, TOOL_MODULE_ADAPTER_CONTRACT_VERSION)

    def test_safe_echo_returns_structured_result(self) -> None:
        result = self.adapter.execute(self.request, self.plan())

        self.assertEqual(
            result,
            Result(request_id="request-1", status="succeeded", output={"value": "hello"}),
        )

    def test_unsupported_operation_or_shape_fails_safely(self) -> None:
        plans = (
            self.plan(steps=(ExecutionStep(sequence=1, operation="write"),)),
            self.plan(steps=(ExecutionStep(sequence=1, operation="echo", parameters={}),)),
            self.plan(steps=()),
        )
        for plan in plans:
            with self.subTest(plan=plan):
                result = self.adapter.execute(self.request, plan)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.request_id, "request-1")


if __name__ == "__main__":
    unittest.main()
