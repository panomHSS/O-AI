import unittest
from types import SimpleNamespace

from app.adapters.local_ai import LocalAIResponseError
from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.chat import ChatService
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_orchestrator import CommandOrchestrationFailure
from app.services.execution_audit import (
    ExecutionAuditTrail,
    InMemoryAuditSink,
)
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.knowledge_answer import KnowledgeAnswerService
from app.services.knowledge_intelligence import (
    CitationEngine,
    ConfidenceEvaluator,
    ConflictDetector,
    ContextBuilder,
    EvidenceRanker,
    GroundedPromptBuilder,
    IntentAnalyzer,
    RetrievalPlanner,
)


EVIDENCE_TEXT = "Document evidence says the pump pressure is 10 bar."


class RecordingAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str, *, error: Exception | None = None) -> None:
        self.adapter_id = adapter_id
        self.error = error
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return AIResult(content="Grounded answer S1")


class StaticDiscovery:
    def discover(self, adapter_id: str):
        _ = adapter_id

        class Discovery:
            status = "available"
            capability_ids = (AI_CAPABILITY_TEXT_GENERATION,)
            configured_model_id = "configured-model"

        return Discovery()


class RecordingExecutionPlanner:
    def __init__(self, planner: ExecutionPlanner) -> None:
        self._planner = planner
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        return self._planner.plan(request)


class FailIfDirectProvider:
    def __init__(self) -> None:
        self.called = False

    def generate_reply(self, prompt: str) -> str:
        self.called = True
        raise AssertionError("D50 grounded Knowledge Answer bypassed AIRuntime.")


class EvidenceRepository:
    def search(self, query: str, limit: int):
        _ = (query, limit)
        return [{
            "document_id": "00000000-0000-0000-0000-000000000001",
            "chunk_id": "chunk-1",
            "file_name": "manual.txt",
            "source_path": "manual.txt",
            "source_locator": "line 1",
            "content": EVIDENCE_TEXT,
            "relevance_score": 1.0,
            "file_extension": ".txt",
        }]


class FakeConversations:
    def __init__(self) -> None:
        self.completed = []

    def begin_turn(self, question, conversation_id, project_id):
        _ = (question, conversation_id, project_id)
        return (
            SimpleNamespace(
                id="11111111-1111-1111-1111-111111111111",
                project_id=None,
            ),
            [],
        )

    def resolve_project_context(self, conversation):
        _ = conversation
        return None

    def complete_turn(self, conversation_id, answer, snapshots) -> None:
        self.completed.append((conversation_id, answer, snapshots))


class KnowledgeAnswerAIExecutionTests(unittest.TestCase):
    def build_lane(self, *, local_enabled: bool, local_error: Exception | None = None):
        chatgpt = RecordingAdapter("chatgpt.default")
        local = RecordingAdapter("local_ai.default", error=local_error)
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
        planner = RecordingExecutionPlanner(
            ExecutionPlanner(
                registry=registry,
                decision_engine=CommandDecisionEngine(),
                ai_router=router,
                ai_discovery=StaticDiscovery(),  # type: ignore[arg-type]
                permission_policy=object(),
                audit=audit,
            )
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=object(),
            audit=audit,
        )
        runtime = AIRuntime(registry=registry, audit=audit)
        return chatgpt, local, planner, guard, runtime, sink

    @staticmethod
    def build_service(planner, guard, runtime):
        provider = FailIfDirectProvider()
        conversations = FakeConversations()
        service = KnowledgeAnswerService(
            repository=EvidenceRepository(),  # type: ignore[arg-type]
            conversations=conversations,  # type: ignore[arg-type]
            chat=ChatService(provider),  # type: ignore[arg-type]
            analyzer=IntentAnalyzer(),
            planner=RetrievalPlanner(1),
            ranker=EvidenceRanker(1),
            conflict_detector=ConflictDetector(),
            context_builder=ContextBuilder(2_000),
            prompt_builder=GroundedPromptBuilder(),
            citations=CitationEngine(),
            confidence=ConfidenceEvaluator(),
            candidates_per_query=1,
            selected_limit=1,
            execution_planner=planner,  # type: ignore[arg-type]
            execution_guard=guard,
            ai_runtime=runtime,
        )
        return service, provider, conversations

    def test_grounded_default_runs_planner_guard_runtime_once(self) -> None:
        chatgpt, local, planner, guard, runtime, sink = self.build_lane(local_enabled=False)
        service, provider, conversations = self.build_service(planner, guard, runtime)
        question = "What is the pump pressure?"
        response = service.answer(question, None, request_id="knowledge-default-1")

        self.assertEqual(response.answer, "Grounded answer S1")
        self.assertEqual(len(chatgpt.requests), 1)
        self.assertEqual(local.requests, [])
        self.assertFalse(provider.called)
        self.assertEqual(len(planner.requests), 1)
        self.assertEqual(planner.requests[0].request_id, "knowledge-default-1")
        self.assertEqual(planner.requests[0].arguments["message"], question)
        self.assertNotEqual(planner.requests[0].arguments["message"], chatgpt.requests[0].content)
        self.assertIn(EVIDENCE_TEXT, chatgpt.requests[0].content)
        self.assertEqual(len(conversations.completed), 1)

        execution_events = [event for event in sink.events if event.stage == "execution"]
        self.assertEqual([event.status for event in execution_events], ["started", "succeeded"])
        self.assertTrue(all(event.request_id == "knowledge-default-1" for event in sink.events))
        audit_text = repr(sink.events)
        self.assertNotIn(EVIDENCE_TEXT, audit_text)
        self.assertNotIn("Grounded answer S1", audit_text)

    def test_grounded_explicit_local_runs_only_local_adapter(self) -> None:
        chatgpt, local, planner, guard, runtime, _ = self.build_lane(local_enabled=True)
        service, provider, _ = self.build_service(planner, guard, runtime)
        response = service.answer(
            "Use local AI for this command",
            None,
            request_id="knowledge-local-1",
        )
        self.assertEqual(response.answer, "Grounded answer S1")
        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(len(local.requests), 1)
        self.assertFalse(provider.called)

    def test_disabled_local_stops_before_execution_without_fallback(self) -> None:
        chatgpt, local, planner, guard, runtime, sink = self.build_lane(local_enabled=False)
        service, provider, _ = self.build_service(planner, guard, runtime)
        with self.assertRaises(CommandOrchestrationFailure) as caught:
            service.answer(
                "Use local AI for this command",
                None,
                request_id="knowledge-local-disabled",
            )
        self.assertEqual(caught.exception.response.result.error, "LOCAL_AI_UNAVAILABLE")
        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(local.requests, [])
        self.assertFalse(provider.called)
        self.assertFalse(any(event.stage == "execution" for event in sink.events))

    def test_local_failure_never_falls_back_to_cloud(self) -> None:
        chatgpt, local, planner, guard, runtime, sink = self.build_lane(
            local_enabled=True,
            local_error=LocalAIResponseError("private local detail"),
        )
        service, provider, _ = self.build_service(planner, guard, runtime)
        with self.assertRaises(CommandOrchestrationFailure) as caught:
            service.answer(
                "Use local AI for this command",
                None,
                request_id="knowledge-local-failure",
            )
        self.assertEqual(caught.exception.response.result.error, "LOCAL_AI_RESPONSE_FAILED")
        self.assertEqual(chatgpt.requests, [])
        self.assertEqual(len(local.requests), 1)
        self.assertFalse(provider.called)
        execution_events = [event for event in sink.events if event.stage == "execution"]
        self.assertEqual([event.status for event in execution_events], ["started", "failed"])
        self.assertNotIn("private local detail", repr(execution_events))


if __name__ == "__main__":
    unittest.main()
