import unittest

from app.adapters.local_ai import LocalAIResponseError
from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.command import CommandRequest
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_audit import ExecutionAuditTrail, InMemoryAuditSink
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner


class RecordingAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        adapter_id: str,
        *,
        error: Exception | None = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.error = error
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return AIResult(content=f"{self.adapter_id} reply")


class StaticDiscovery:
    def discover(self, adapter_id: str):
        class Discovery:
            status = "available"
            capability_ids = (AI_CAPABILITY_TEXT_GENERATION,)
            configured_model_id = "configured-model"

        return Discovery()


class UnifiedAIExecutionE2ETests(unittest.TestCase):
    def build_lane(
        self,
        *,
        local_enabled: bool,
        local_error: Exception | None = None,
    ):
        chatgpt = RecordingAdapter("chatgpt.default")
        local = RecordingAdapter(
            "local_ai.default",
            error=local_error,
        )
        registry = AdapterRegistry((chatgpt, local))
        enabled = {"chatgpt.default"}
        if local_enabled:
            enabled.add("local_ai.default")
        router = AIRouter(
            registry=registry,
            policy=AIProviderRoutingPolicy(
                default_adapter_id="chatgpt.default",
                enabled_adapter_ids=frozenset(enabled),
            ),
        )
        sink = InMemoryAuditSink()
        audit = ExecutionAuditTrail(sink=sink)
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=router,
            ai_discovery=StaticDiscovery(),  # type: ignore[arg-type]
            permission_policy=object(),
            audit=audit,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=object(),
            audit=audit,
        )
        runtime = AIRuntime(
            registry=registry,
            audit=audit,
        )
        return chatgpt, local, planner, guard, runtime, sink

    @staticmethod
    def command(
        message: str,
        request_id: str = "request-1",
    ) -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command="chat.message",
            arguments={
                "message": message,
                "conversation_id": None,
                "project_id": None,
            },
        )

    def execute_lane(self, message: str, *, local_enabled: bool = False):
        chatgpt, local, planner, guard, runtime, sink = self.build_lane(
            local_enabled=local_enabled
        )
        request = self.command(message)
        planning = planner.plan(request)
        self.assertEqual(planning.status, "planned")
        authorization = guard.authorize(request, planning)
        self.assertEqual(authorization.status, "authorized")
        proxy = runtime.bind(request, authorization)
        result = proxy.generate(AIRequest(content="formatted context"))
        return chatgpt, local, planning, authorization, result, sink

    def test_default_ai_runs_planner_guard_runtime_and_adapter_once(self) -> None:
        (
            chatgpt,
            local,
            planning,
            authorization,
            result,
            sink,
        ) = self.execute_lane("hello")

        self.assertEqual(planning.target_kind, "ai")
        self.assertEqual(authorization.target_kind, "ai")
        self.assertEqual(result.content, "chatgpt.default reply")
        self.assertEqual(len(chatgpt.requests), 1)
        self.assertEqual(local.requests, [])
        execution_events = [
            event for event in sink.events if event.stage == "execution"
        ]
        self.assertEqual(
            [event.status for event in execution_events],
            ["started", "succeeded"],
        )

    def test_explicit_local_runs_only_local_adapter(self) -> None:
        chatgpt, local, _, _, result, _ = self.execute_lane(
            "Use local AI for this command",
            local_enabled=True,
        )

        self.assertEqual(result.content, "local_ai.default reply")
        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(len(local.requests), 1)

    def test_disabled_local_stops_at_planning_without_cloud_fallback(self) -> None:
        chatgpt, local, planner, _, _, sink = self.build_lane(
            local_enabled=False
        )
        request = self.command("Use local AI for this command")

        planning = planner.plan(request)

        self.assertEqual(planning.status, "unavailable")
        self.assertEqual(planning.reason_code, "local_ai_unavailable")
        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(local.requests, [])
        self.assertFalse(
            any(event.stage == "execution" for event in sink.events)
        )

    def test_local_provider_failure_never_falls_back_to_cloud(self) -> None:
        chatgpt, local, planner, guard, runtime, sink = self.build_lane(
            local_enabled=True,
            local_error=LocalAIResponseError("private local detail"),
        )
        request = self.command("Use local AI for this command")
        planning = planner.plan(request)
        authorization = guard.authorize(request, planning)
        proxy = runtime.bind(request, authorization)

        with self.assertRaises(LocalAIResponseError):
            proxy.generate(AIRequest(content="formatted private context"))

        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(len(local.requests), 1)
        execution_events = [
            event for event in sink.events if event.stage == "execution"
        ]
        self.assertEqual(
            [event.status for event in execution_events],
            ["started", "failed"],
        )
        self.assertNotIn("private local detail", repr(execution_events))
        self.assertNotIn("formatted private context", repr(execution_events))


if __name__ == "__main__":
    unittest.main()
