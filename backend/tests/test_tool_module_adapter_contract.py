import unittest

from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    Result,
)
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
    ToolAdapter,
)


class StubToolAdapter:
    adapter_id = "stub-tool-adapter"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    tool_name = "stub-tool"

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        return Result(
            request_id=request.request_id,
            status="blocked",
            output={"step_count": len(plan.steps)},
        )


class StubModuleAdapter:
    adapter_id = "stub-module-adapter"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    module_name = "stub-module"

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        return Result(request_id=request.request_id, status="blocked")


class ToolModuleAdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = CommandRequest(
            request_id="request-1",
            command="inspect",
        )
        self.plan = ExecutionPlan(
            request_id="request-1",
            adapter_id="stub",
        )

    def test_tool_protocol_accepts_structural_implementation(self) -> None:
        adapter = StubToolAdapter()

        self.assertIsInstance(adapter, ToolAdapter)
        self.assertEqual(adapter.contract_version, "1")
        self.assertEqual(
            adapter.execute(self.request, self.plan).status,
            "blocked",
        )

    def test_module_protocol_accepts_structural_implementation(self) -> None:
        adapter = StubModuleAdapter()

        self.assertIsInstance(adapter, ModuleAdapter)
        self.assertEqual(adapter.contract_version, "1")
        self.assertEqual(
            adapter.execute(self.request, self.plan).status,
            "blocked",
        )

    def test_tool_and_module_protocols_are_distinct(self) -> None:
        self.assertNotIsInstance(StubToolAdapter(), ModuleAdapter)
        self.assertNotIsInstance(StubModuleAdapter(), ToolAdapter)


if __name__ == "__main__":
    unittest.main()
