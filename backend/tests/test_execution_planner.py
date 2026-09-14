import unittest
from types import SimpleNamespace

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_STATUS_AVAILABLE,
    AI_DISCOVERY_STATUS_UNAVAILABLE,
    AIAdapterDiscovery,
    AIModelDescriptor,
)
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_planner import ExecutionPlanner, MODULE_EXECUTE_COMMAND, TOOL_EXECUTE_COMMAND


class StubAIAdapter:
    adapter_id = "chatgpt.default"
    contract_version = AI_ADAPTER_CONTRACT_VERSION
    def __init__(self) -> None: self.generate_calls = 0
    def generate(self, request: AIRequest) -> AIResult:
        self.generate_calls += 1
        return AIResult(content="not used")


class StubToolAdapter:
    adapter_id = "tool.stub"
    tool_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    def __init__(self) -> None: self.execute_calls = 0
    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        self.execute_calls += 1
        return Result(request.request_id, "succeeded")


class StubModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    def __init__(self) -> None: self.execute_calls = 0
    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        self.execute_calls += 1
        return Result(request.request_id, "succeeded")


class StubAIRouter:
    def __init__(self, *, status: str = "selected", adapter_id: str | None = "chatgpt.default") -> None:
        self.status, self.adapter_id, self.calls = status, adapter_id, 0
    def route(self, decision):
        self.calls += 1
        return SimpleNamespace(request_id=decision.request_id, status=self.status, adapter_id=self.adapter_id, reason_code="test")


class StubDiscovery:
    def __init__(self, result: AIAdapterDiscovery) -> None:
        self.result, self.calls = result, 0
    def discover(self, adapter_id: str) -> AIAdapterDiscovery:
        self.calls += 1
        if adapter_id != self.result.adapter_id: raise KeyError(adapter_id)
        return self.result


def available_discovery(*, adapter_id: str = "chatgpt.default", model_id: str = "model-a", capabilities: tuple[str, ...] = (AI_CAPABILITY_TEXT_GENERATION,)) -> AIAdapterDiscovery:
    return AIAdapterDiscovery(
        adapter_id=adapter_id,
        status=AI_DISCOVERY_STATUS_AVAILABLE,
        configured_model_id=model_id,
        capability_ids=capabilities,
        models=(AIModelDescriptor(model_id=model_id, capability_ids=capabilities),),
        reason_code="configured_model",
    )


class ExecutionPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ai, self.tool, self.module = StubAIAdapter(), StubToolAdapter(), StubModuleAdapter()
        self.registry = AdapterRegistry((self.ai, self.tool, self.module))

    def make_planner(self, *, router=None, discovery=None) -> ExecutionPlanner:
        return ExecutionPlanner(
            registry=self.registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=router or StubAIRouter(),  # type: ignore[arg-type]
            ai_discovery=discovery or StubDiscovery(available_discovery()),  # type: ignore[arg-type]
        )

    @staticmethod
    def chat_request(message: str = "hello") -> CommandRequest:
        return CommandRequest(
            request_id="req-chat",
            command="chat.message",
            arguments={"message": message, "conversation_id": None, "project_id": None},
        )

    def test_chat_message_plans_text_generation_without_copying_message(self) -> None:
        outcome = self.make_planner().plan(self.chat_request("sensitive message"))
        self.assertEqual((outcome.status, outcome.target_kind), ("planned", "ai"))
        plan = outcome.plan
        assert plan is not None
        self.assertEqual(plan.adapter_id, "chatgpt.default")
        self.assertFalse(plan.owner_approval_required)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].operation, "ai.generate_text")
        self.assertEqual(dict(plan.steps[0].parameters), {"capability_id": "text_generation", "model_id": "model-a"})
        self.assertNotIn("sensitive message", repr(plan))
        self.assertEqual((self.ai.generate_calls, self.tool.execute_calls, self.module.execute_calls), (0, 0, 0))

    def test_ai_route_unavailable_does_not_fallback(self) -> None:
        outcome = self.make_planner(router=StubAIRouter(status="unavailable", adapter_id="local_ai.default")).plan(self.chat_request())
        self.assertEqual((outcome.status, outcome.reason_code, outcome.plan), ("unavailable", "ai_route_unavailable", None))

    def test_ai_discovery_unavailable_produces_no_plan(self) -> None:
        unavailable = AIAdapterDiscovery(
            adapter_id="chatgpt.default",
            status=AI_DISCOVERY_STATUS_UNAVAILABLE,
            configured_model_id=None,
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=(),
            reason_code="configured_model_missing",
        )
        outcome = self.make_planner(discovery=StubDiscovery(unavailable)).plan(self.chat_request())
        self.assertEqual((outcome.status, outcome.reason_code), ("unavailable", "ai_discovery_unavailable"))

    def test_missing_text_generation_capability_produces_no_plan(self) -> None:
        outcome = self.make_planner(discovery=StubDiscovery(available_discovery(capabilities=("other_capability",)))).plan(self.chat_request())
        self.assertEqual(outcome.reason_code, "ai_capability_unavailable")

    def test_invalid_chat_command_is_rejected_before_routing(self) -> None:
        router = StubAIRouter()
        request = CommandRequest("req-chat", "chat.message", {"message": "hello"})
        outcome = self.make_planner(router=router).plan(request)
        self.assertEqual((outcome.status, outcome.reason_code, router.calls), ("rejected", "invalid_chat_command", 0))

    def test_tool_plan_requires_owner_approval_and_never_executes(self) -> None:
        request = CommandRequest("req-tool", TOOL_EXECUTE_COMMAND, {"adapter_id": "tool.stub", "operation": "echo", "parameters": {"value": "hello"}})
        outcome = self.make_planner().plan(request)
        self.assertEqual((outcome.status, outcome.target_kind), ("planned", "tool"))
        self.assertTrue(outcome.plan.owner_approval_required)  # type: ignore[union-attr]
        self.assertEqual(self.tool.execute_calls, 0)

    def test_unknown_tool_and_wrong_kind_fail_closed(self) -> None:
        planner = self.make_planner()
        unknown = CommandRequest("req-tool", TOOL_EXECUTE_COMMAND, {"adapter_id": "tool.unknown", "operation": "echo", "parameters": {}})
        wrong = CommandRequest("req-tool-2", TOOL_EXECUTE_COMMAND, {"adapter_id": "module.stub", "operation": "echo", "parameters": {}})
        self.assertEqual(planner.plan(unknown).reason_code, "tool_adapter_unavailable")
        self.assertEqual(planner.plan(wrong).reason_code, "tool_adapter_kind_mismatch")

    def test_module_plan_requires_owner_approval_and_never_executes(self) -> None:
        request = CommandRequest("req-module", MODULE_EXECUTE_COMMAND, {"adapter_id": "module.stub", "operation": "inspect", "parameters": {}})
        outcome = self.make_planner().plan(request)
        self.assertEqual((outcome.status, outcome.target_kind), ("planned", "module"))
        self.assertTrue(outcome.plan.owner_approval_required)  # type: ignore[union-attr]
        self.assertEqual(self.module.execute_calls, 0)

    def test_module_wrong_kind_and_invalid_shape_are_rejected(self) -> None:
        planner = self.make_planner()
        wrong = CommandRequest("req-module", MODULE_EXECUTE_COMMAND, {"adapter_id": "tool.stub", "operation": "inspect", "parameters": {}})
        invalid = CommandRequest("req-module-2", MODULE_EXECUTE_COMMAND, {"adapter_id": "module.stub", "operation": "", "parameters": {}})
        self.assertEqual(planner.plan(wrong).reason_code, "module_adapter_kind_mismatch")
        self.assertEqual(planner.plan(invalid).reason_code, "invalid_module_command")

    def test_unsupported_command_is_rejected(self) -> None:
        outcome = self.make_planner().plan(CommandRequest("req-x", "something.else", {}))
        self.assertEqual((outcome.status, outcome.reason_code), ("rejected", "unsupported_command"))

    def test_repeated_planning_is_deterministic(self) -> None:
        planner, request = self.make_planner(), self.chat_request()
        self.assertEqual(planner.plan(request), planner.plan(request))
        self.assertEqual(self.ai.generate_calls, 0)


if __name__ == "__main__":
    unittest.main()
