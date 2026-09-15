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
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.capability_permission_policy import CapabilityPermissionPolicy
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
        self.policy = CapabilityPermissionPolicy(
            registry=self.registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.tool", "tool", "tool.stub", "echo",
                    "none", "none", True,
                ),
                ExecutableCapabilityPermission(
                    "exec.test.module", "module", "module.stub", "inspect",
                    "read", "workspace_metadata", True,
                ),
            ),
        )

    def make_planner(self, *, router=None, discovery=None, permission_policy=None) -> ExecutionPlanner:
        return ExecutionPlanner(
            registry=self.registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=router or StubAIRouter(),  # type: ignore[arg-type]
            ai_discovery=discovery or StubDiscovery(available_discovery()),  # type: ignore[arg-type]
            permission_policy=permission_policy or self.policy,
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

    def test_registered_but_unpermitted_operation_is_rejected(self) -> None:
        request = CommandRequest(
            "req-tool-policy", TOOL_EXECUTE_COMMAND,
            {"adapter_id": "tool.stub", "operation": "delete", "parameters": {}},
        )
        outcome = self.make_planner().plan(request)
        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(outcome.reason_code, "capability_not_permitted")
        self.assertIsNone(outcome.plan)

    def test_policy_derives_no_approval_plan_without_execution(self) -> None:
        policy = CapabilityPermissionPolicy(
            registry=self.registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.no-approval", "tool", "tool.stub", "echo",
                    "none", "none", False,
                ),
            ),
        )
        request = CommandRequest(
            "req-tool-no-approval", TOOL_EXECUTE_COMMAND,
            {"adapter_id": "tool.stub", "operation": "echo", "parameters": {"value": "hello"}},
        )
        outcome = self.make_planner(permission_policy=policy).plan(request)
        self.assertEqual(outcome.status, "planned")
        self.assertFalse(outcome.plan.owner_approval_required)  # type: ignore[union-attr]
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



# D49 regression: preserve safe AI route reason codes while retaining the
# exact D35 AI plan shape.
import unittest as _d49_unittest

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION as _D49_AI_ADAPTER_CONTRACT_VERSION,
    AIRequest as _D49_AIRequest,
    AIResult as _D49_AIResult,
)
from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION as _D49_AI_CAPABILITY_TEXT_GENERATION,
)
from app.contracts.command import CommandRequest as _D49_CommandRequest
from app.services.adapter_registry import AdapterRegistry as _D49_AdapterRegistry
from app.services.ai_provider_routing import (
    AIProviderRoutingPolicy as _D49_AIProviderRoutingPolicy,
)
from app.services.ai_router import AIRouter as _D49_AIRouter
from app.services.command_decision_engine import (
    CommandDecisionEngine as _D49_CommandDecisionEngine,
)
from app.services.execution_planner import ExecutionPlanner as _D49_ExecutionPlanner


class _D49RecordingAI:
    contract_version = _D49_AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id

    def generate(self, request: _D49_AIRequest) -> _D49_AIResult:
        return _D49_AIResult(content="unused")


class _D49Discovery:
    def discover(self, adapter_id: str):
        class Discovery:
            status = "available"
            capability_ids = (_D49_AI_CAPABILITY_TEXT_GENERATION,)
            configured_model_id = "configured-model"

        return Discovery()


class D49ExecutionPlannerRegressionTests(_d49_unittest.TestCase):
    @staticmethod
    def _request(message: str) -> _D49_CommandRequest:
        return _D49_CommandRequest(
            "request-d49",
            "chat.message",
            {
                "message": message,
                "conversation_id": None,
                "project_id": None,
            },
        )

    @staticmethod
    def _planner(
        *,
        include_chatgpt: bool = True,
        local_enabled: bool = False,
    ) -> _D49_ExecutionPlanner:
        adapters = []
        if include_chatgpt:
            adapters.append(_D49RecordingAI("chatgpt.default"))
        adapters.append(_D49RecordingAI("local_ai.default"))
        registry = _D49_AdapterRegistry(tuple(adapters))
        enabled = {"chatgpt.default"}
        if local_enabled:
            enabled.add("local_ai.default")
        router = _D49_AIRouter(
            registry=registry,
            policy=_D49_AIProviderRoutingPolicy(
                default_adapter_id="chatgpt.default",
                enabled_adapter_ids=frozenset(enabled),
            ),
        )
        return _D49_ExecutionPlanner(
            registry=registry,
            decision_engine=_D49_CommandDecisionEngine(),
            ai_router=router,
            ai_discovery=_D49Discovery(),
            permission_policy=object(),
        )

    def test_local_ai_unavailable_reason_is_preserved(self) -> None:
        outcome = self._planner().plan(
            self._request("Use local AI for this command")
        )

        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(
            outcome.reason_code,
            "local_ai_unavailable",
        )

    def test_default_adapter_unavailable_reason_is_preserved(self) -> None:
        outcome = self._planner(
            include_chatgpt=False
        ).plan(self._request("hello"))

        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(
            outcome.reason_code,
            "default_adapter_unavailable",
        )

    def test_successful_ai_plan_retains_exact_shape(self) -> None:
        outcome = self._planner().plan(self._request("hello"))

        self.assertEqual(outcome.status, "planned")
        self.assertEqual(outcome.target_kind, "ai")
        assert outcome.plan is not None
        self.assertFalse(outcome.plan.owner_approval_required)
        self.assertEqual(len(outcome.plan.steps), 1)
        step = outcome.plan.steps[0]
        self.assertEqual(step.sequence, 1)
        self.assertEqual(step.operation, "ai.generate_text")
        self.assertEqual(
            dict(step.parameters),
            {
                "capability_id": _D49_AI_CAPABILITY_TEXT_GENERATION,
                "model_id": "configured-model",
            },
        )


if __name__ == "__main__":
    unittest.main()
