import unittest
from unittest.mock import Mock
from uuid import UUID

from app.adapters.local_ai import LocalAIResponseError
from app.adapters.standard_tool import StandardToolAdapter
from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIAdapter,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import ExecutionAuthorization
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ChatTurnResult
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
from app.services.tool_runtime import ToolRuntime


class RecordingAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        adapter_id: str,
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


class RecordingConversationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object, AIAdapter]] = []

    def send_message(
        self,
        message,
        conversation_id=None,
        project_id=None,
        ai_adapter=None,
    ):
        assert ai_adapter is not None
        self.calls.append(
            (message, conversation_id, project_id, ai_adapter)
        )
        reply = ai_adapter.generate(
            AIRequest(
                content="formatted history/context/memory/planning"
            )
        )
        return ChatTurnResult(
            reply=reply.content,
            conversation_id=UUID(
                "11111111-1111-1111-1111-111111111111"
            ),
            project_id=project_id,
        )


class CommandOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chatgpt = RecordingAdapter("chatgpt.default")
        self.local = RecordingAdapter("local_ai.default")
        self.conversations = RecordingConversationService()
        self.normalizer = OrchestrationErrorNormalizer()
        self.composer = ResponseComposer(self.normalizer)

    @staticmethod
    def command(
        message="hello",
        request_id="request-1",
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

    def orchestrator(
        self,
        *,
        local_enabled: bool = False,
        include_chatgpt: bool = True,
    ) -> CommandOrchestrator:
        adapters: list[object] = []
        if include_chatgpt:
            adapters.append(self.chatgpt)
        adapters.extend((self.local, StandardToolAdapter()))
        registry = AdapterRegistry(tuple(adapters))
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
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=router,
            ai_discovery=StaticDiscovery(),  # type: ignore[arg-type]
            permission_policy=object(),
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=object(),
        )
        return CommandOrchestrator(
            conversation_service=self.conversations,  # type: ignore[arg-type]
            planner=planner,
            guard=guard,
            ai_runtime=AIRuntime(registry=registry),
            error_normalizer=self.normalizer,
            response_composer=self.composer,
            tool_runtime=ToolRuntime(registry=registry),
        )

    def test_default_and_automatic_route_to_chatgpt_once_with_context(self) -> None:
        for message in (
            "hello",
            "Route this command automatically",
        ):
            with self.subTest(message=message):
                outcome = self.orchestrator().process_chat(
                    self.command(message)
                )
                self.assertIsNotNone(outcome.chat_turn)
                self.assertEqual(
                    outcome.response.request_id,
                    "request-1",
                )

        self.assertEqual(len(self.chatgpt.requests), 2)
        self.assertEqual(len(self.local.requests), 0)
        self.assertIn(
            "formatted history/context/memory/planning",
            self.chatgpt.requests[0].content,
        )

    def test_explicit_local_routes_to_local_adapter_once(self) -> None:
        outcome = self.orchestrator(local_enabled=True).process_chat(
            self.command("Use local AI for this command")
        )

        self.assertIsNotNone(outcome.chat_turn)
        self.assertEqual(len(self.local.requests), 1)
        self.assertEqual(len(self.chatgpt.requests), 0)

    def test_disabled_or_failing_local_never_falls_back_to_chatgpt(self) -> None:
        disabled = self.orchestrator().process_chat(
            self.command("Use local AI for this command")
        )
        self.assertEqual(
            disabled.response.result.error,
            "LOCAL_AI_UNAVAILABLE",
        )
        self.assertEqual(len(self.chatgpt.requests), 0)

        self.local.error = LocalAIResponseError(
            "private runtime detail"
        )
        failed = self.orchestrator(local_enabled=True).process_chat(
            self.command(
                "Use local AI for this command",
                "request-2",
            )
        )
        self.assertEqual(
            failed.response.result.error,
            "LOCAL_AI_RESPONSE_FAILED",
        )
        self.assertEqual(len(self.chatgpt.requests), 0)
        self.assertEqual(len(self.local.requests), 1)

    def test_missing_selected_adapter_fails_closed(self) -> None:
        outcome = self.orchestrator(
            include_chatgpt=False
        ).process_chat(self.command())

        self.assertEqual(
            outcome.response.result.error,
            "AI_ROUTE_UNAVAILABLE",
        )
        self.assertFalse(self.conversations.calls)

    def test_raw_tool_plan_cannot_execute_directly(self) -> None:
        adapter = StandardToolAdapter()
        adapter.execute = Mock(
            wraps=adapter.execute
        )
        orchestrator = self.orchestrator()
        orchestrator._tool_runtime = ToolRuntime(
            registry=AdapterRegistry((adapter,))
        )
        request = CommandRequest("request-1", "tool.echo")
        raw_plan = ExecutionPlan(
            "request-1",
            adapter.adapter_id,
            (ExecutionStep(1, "echo", {"value": "safe"}),),
            False,
        )

        response = orchestrator.execute_tool(
            request,
            raw_plan,
        )

        self.assertEqual(response.result.error, "INTERNAL_ERROR")
        adapter.execute.assert_not_called()

    def test_authorized_tool_executes_once_and_composes_result(self) -> None:
        adapter = StandardToolAdapter()
        adapter.execute = Mock(
            wraps=adapter.execute
        )
        orchestrator = self.orchestrator()
        orchestrator._tool_runtime = ToolRuntime(
            registry=AdapterRegistry((adapter,))
        )
        request = CommandRequest("request-1", "tool.execute")
        execution_plan = ExecutionPlan(
            "request-1",
            adapter.adapter_id,
            (ExecutionStep(1, "echo", {"value": "safe"}),),
            False,
        )
        authorization = ExecutionAuthorization(
            request_id="request-1",
            status="authorized",
            target_kind="tool",
            source_plan_digest="a" * 64,
            execution_plan=execution_plan,
            reason_code="owner_approval_verified",
        )

        response = orchestrator.execute_tool(
            request,
            authorization,
        )

        self.assertEqual(response.result.status, "succeeded")
        self.assertEqual(
            response.result.output,
            {"value": "safe"},
        )
        adapter.execute.assert_called_once_with(
            request,
            execution_plan,
        )

    def test_non_authorized_tool_never_executes(self) -> None:
        adapter = StandardToolAdapter()
        adapter.execute = Mock(
            wraps=adapter.execute
        )
        orchestrator = self.orchestrator()
        orchestrator._tool_runtime = ToolRuntime(
            registry=AdapterRegistry((adapter,))
        )
        request = CommandRequest("request-1", "tool.echo")
        authorizations = (
            ExecutionAuthorization(
                "request-1",
                "blocked",
                "tool",
                "b" * 64,
                None,
                "owner_approval_required",
            ),
            ExecutionAuthorization(
                "request-1",
                "blocked",
                "tool",
                "b" * 64,
                None,
                "owner_approval_denied",
            ),
            ExecutionAuthorization(
                "request-1",
                "rejected",
                "tool",
                "b" * 64,
                None,
                "approval_plan_mismatch",
            ),
        )
        expected = (
            "OWNER_APPROVAL_REQUIRED",
            "OWNER_APPROVAL_DENIED",
            "EXECUTION_AUTHORIZATION_REJECTED",
        )

        for authorization, code in zip(
            authorizations,
            expected,
            strict=True,
        ):
            with self.subTest(authorization=authorization):
                response = orchestrator.execute_tool(
                    request,
                    authorization,
                )
                self.assertEqual(
                    response.result.error,
                    code,
                )

        adapter.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
