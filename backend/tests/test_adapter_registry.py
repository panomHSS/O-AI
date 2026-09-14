import unittest
from unittest.mock import Mock

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_adapter_registry import AIAdapterRegistry
from app.services.tool_module_router import ToolModuleRouter


class StubAIAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.generate = Mock(return_value=AIResult(content="unused"))


class StubToolAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    tool_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.execute = Mock(return_value=Result(request_id="request-1", status="succeeded"))


class StubModuleAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    module_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.execute = Mock(return_value=Result(request_id="request-1", status="succeeded"))


class WrongVersionAIAdapter(StubAIAdapter):
    contract_version = "2"


class AmbiguousAdapter(StubToolAdapter):
    module_name = "also-module"


class AdapterRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ai = StubAIAdapter("ai.stub")
        self.tool = StubToolAdapter("tool.stub")
        self.module = StubModuleAdapter("module.stub")
        self.registry = AdapterRegistry((self.module, self.tool, self.ai))

    def test_resolves_each_boundary_without_invocation(self) -> None:
        self.assertIs(self.registry.resolve_ai("ai.stub"), self.ai)
        self.assertIs(self.registry.resolve_tool("tool.stub"), self.tool)
        self.assertIs(self.registry.resolve_module("module.stub"), self.module)
        self.assertIs(self.registry.resolve_executable("tool.stub"), self.tool)
        self.assertIs(self.registry.resolve_executable("module.stub"), self.module)
        self.ai.generate.assert_not_called()
        self.tool.execute.assert_not_called()
        self.module.execute.assert_not_called()

    def test_discovery_is_deterministic_and_kind_scoped(self) -> None:
        self.assertEqual(
            self.registry.adapter_ids,
            ("ai.stub", "module.stub", "tool.stub"),
        )
        self.assertEqual(self.registry.ai_adapter_ids, ("ai.stub",))
        self.assertEqual(self.registry.tool_adapter_ids, ("tool.stub",))
        self.assertEqual(self.registry.module_adapter_ids, ("module.stub",))
        self.assertEqual(self.registry.adapter_kind("module.stub"), "module")
        self.assertIsNone(self.registry.adapter_kind("missing"))

    def test_unknown_ids_fail_closed(self) -> None:
        self.assertIsNone(self.registry.resolve_ai("missing"))
        self.assertIsNone(self.registry.resolve_tool("missing"))
        self.assertIsNone(self.registry.resolve_module("missing"))
        self.assertIsNone(self.registry.resolve_executable("missing"))

    def test_duplicate_ids_are_rejected_across_adapter_kinds(self) -> None:
        with self.assertRaises(ValueError):
            AdapterRegistry((StubAIAdapter("shared"), StubToolAdapter("shared")))

    def test_wrong_version_invalid_id_and_ambiguous_contract_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AdapterRegistry((WrongVersionAIAdapter("ai.wrong"),))
        with self.assertRaises(ValueError):
            AdapterRegistry((StubAIAdapter("  "),))
        with self.assertRaises(TypeError):
            AdapterRegistry((AmbiguousAdapter("ambiguous"),))
        with self.assertRaises(TypeError):
            AdapterRegistry((object(),))

    def test_d29_ai_registry_can_share_the_unified_registry(self) -> None:
        legacy = AIAdapterRegistry(registry=self.registry)
        self.assertEqual(legacy.adapter_ids, ("ai.stub",))
        self.assertIs(legacy.resolve("ai.stub"), self.ai)
        self.assertIsNone(legacy.resolve("tool.stub"))

    def test_d27_router_can_share_the_unified_registry(self) -> None:
        router = ToolModuleRouter(registry=self.registry)
        request = CommandRequest("request-1", "tool.stub")
        selected = router.route(
            request,
            ExecutionPlan(
                "request-1",
                "tool.stub",
                owner_approval_required=False,
            ),
        )
        blocked = router.route(
            request,
            ExecutionPlan("request-1", "module.stub"),
        )

        self.assertEqual((selected.status, selected.adapter_id), ("selected", "tool.stub"))
        self.assertEqual((blocked.status, blocked.adapter_id), ("blocked", "module.stub"))
        self.tool.execute.assert_not_called()
        self.module.execute.assert_not_called()

    def test_legacy_constructors_keep_existing_validation(self) -> None:
        self.assertIs(AIAdapterRegistry((self.ai,)).resolve("ai.stub"), self.ai)
        self.assertIs(ToolModuleRouter((self.tool,)).get_adapter("tool.stub"), self.tool)
        with self.assertRaises(TypeError):
            ToolModuleRouter((self.ai,))


if __name__ == "__main__":
    unittest.main()
