import unittest
from unittest.mock import Mock

from app.adapters.standard_tool import StandardToolAdapter
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import ModuleAdapter, TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.tool_module_router import ToolModuleRouter


class StubModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        return Result(request_id=request.request_id, status="succeeded")


class UnsupportedVersionToolAdapter(StandardToolAdapter):
    contract_version = "2"


class ToolModuleRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = StandardToolAdapter()
        self.router = ToolModuleRouter((self.adapter,))
        self.request = CommandRequest(request_id="request-1", command="tool.echo")

    def plan(self, **kwargs: object) -> ExecutionPlan:
        fields: dict[str, object] = {
            "request_id": "request-1",
            "adapter_id": self.adapter.adapter_id,
            "owner_approval_required": False,
        }
        fields.update(kwargs)
        return ExecutionPlan(**fields)  # type: ignore[arg-type]

    def test_selected_route_never_executes_adapter(self) -> None:
        self.adapter.execute = Mock()  # type: ignore[method-assign]

        route = self.router.route(self.request, self.plan())

        self.assertEqual((route.status, route.adapter_id), ("selected", self.adapter.adapter_id))
        self.adapter.execute.assert_not_called()

    def test_unknown_adapter_is_unavailable(self) -> None:
        route = self.router.route(
            self.request,
            self.plan(adapter_id="tool.unknown"),
        )
        self.assertEqual((route.status, route.adapter_id), ("unavailable", "tool.unknown"))

    def test_request_plan_mismatch_is_rejected(self) -> None:
        route = self.router.route(
            self.request,
            self.plan(request_id="different"),
        )
        self.assertEqual((route.status, route.adapter_id), ("rejected", None))

    def test_approval_required_is_blocked(self) -> None:
        route = self.router.route(
            self.request,
            self.plan(owner_approval_required=True),
        )
        self.assertEqual((route.status, route.adapter_id), ("blocked", self.adapter.adapter_id))

    def test_constructor_rejects_duplicate_or_unsupported_adapters(self) -> None:
        with self.assertRaises(ValueError):
            ToolModuleRouter((self.adapter, StandardToolAdapter()))
        with self.assertRaises(ValueError):
            ToolModuleRouter((UnsupportedVersionToolAdapter(),))

    def test_module_adapter_routing_is_supported(self) -> None:
        module = StubModuleAdapter()
        self.assertIsInstance(module, ModuleAdapter)
        route = ToolModuleRouter((module,)).route(
            self.request,
            ExecutionPlan(
                request_id="request-1",
                adapter_id=module.adapter_id,
                owner_approval_required=False,
            ),
        )
        self.assertEqual((route.status, route.adapter_id), ("selected", module.adapter_id))


if __name__ == "__main__":
    unittest.main()
