from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.chatgpt import ChatGPTAdapter
from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.contracts.command import CommandRequest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.db.session import create_database_engine, initialize_test_database
from app.repositories.conversations import ConversationRepository
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_capability_model_discovery import (
    AICapabilityModelDiscovery,
)
from app.services.ai_discovery_sources import (
    ChatGPTConfiguredModelDiscoverySource,
)
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.chat import ChatService
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_orchestrator import CommandOrchestrator
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.orchestration_error_normalizer import (
    OrchestrationErrorNormalizer,
)
from app.services.response_composer import ResponseComposer
from tests.d97_context_chat_fixture import (
    build_context_aware_conversation_service,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


class RecordingCloudProvider:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def generate_reply(self, message: str) -> str:
        self.inputs.append(message)
        return "authorized cloud reply"


class RecordingConversationService:
    def __init__(self) -> None:
        self.calls = 0

    def send_context_message(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError(
            "Context must not run after workspace Cloud rejection"
        )


def command(
    message: str,
    *,
    conversation_id: UUID | None = None,
    request_id: str = "d112-b03",
) -> CommandRequest:
    return CommandRequest(
        request_id=request_id,
        command="chat.message",
        arguments={
            "message": message,
            "conversation_id": conversation_id,
            "project_id": None,
        },
    )


def cloud_lane(
    *,
    workspace_id: WorkspaceId,
    workspace_mode: WorkspaceAIRouteMode,
    provider: RecordingCloudProvider,
):
    cloud = ChatGPTAdapter(provider)
    registry = AdapterRegistry((cloud,))
    policy = AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(
            {CHATGPT_DEFAULT_ADAPTER_ID}
        ),
    )
    router = AIRouter(
        registry=registry,
        policy=policy,
        workspace_policy=WorkspaceAIRoutingPolicy(
            workspace_id=workspace_id,
            mode=workspace_mode,
        ),
    )
    discovery = AICapabilityModelDiscovery(
        registry=registry,
        sources=(
            ChatGPTConfiguredModelDiscoverySource(
                configured_model_id="configured-cloud-model",
                enabled=True,
                credential_configured=True,
            ),
        ),
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=router,
        ai_discovery=discovery,
        permission_policy=object(),  # type: ignore[arg-type]
    )
    guard = ExecutionGuard(
        registry=registry,
        permission_policy=object(),  # type: ignore[arg-type]
    )
    runtime = AIRuntime(registry=registry)
    return planner, guard, runtime


def orchestrator(
    *,
    conversation_service,
    planner: ExecutionPlanner,
    guard: ExecutionGuard,
    runtime: AIRuntime,
) -> CommandOrchestrator:
    normalizer = OrchestrationErrorNormalizer()
    return CommandOrchestrator(
        conversation_service=conversation_service,
        planner=planner,
        guard=guard,
        ai_runtime=runtime,
        error_normalizer=normalizer,
        response_composer=ResponseComposer(normalizer),
        tool_runtime=object(),  # type: ignore[arg-type]
    )


@pytest.fixture
def session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    initialize_test_database(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    with SessionLocal() as value:
        yield value
    engine.dispose()


@pytest.mark.parametrize(
    "logical_mode",
    (AIMode.AUTO, AIMode.CLOUD_AI),
)
def test_d112_personal_cloud_chat_egresses_only_after_d35_d36_d49(
    session: Session,
    logical_mode: AIMode,
) -> None:
    repository = ConversationRepository(session, PERSONAL)
    conversation = repository.create("D112 Personal Cloud")
    repository.add_message(
        conversation,
        "user",
        "personal-context-marker",
    )
    repository.add_message(
        conversation,
        "assistant",
        "prior-answer-marker",
    )
    repository.commit()

    provider = RecordingCloudProvider()
    planner, guard, runtime = cloud_lane(
        workspace_id=WorkspaceId.PERSONAL,
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        provider=provider,
    )
    conversation_service = build_context_aware_conversation_service(
        session=session,
        workspace_scope=PERSONAL,
        chat_service=ChatService(provider=provider),
        context_message_limit=20,
    )
    service = orchestrator(
        conversation_service=conversation_service,
        planner=planner,
        guard=guard,
        runtime=runtime,
    )

    outcome = service.process_chat(
        command(
            "Summarize the prior Personal discussion.",
            conversation_id=UUID(conversation.id),
            request_id=f"d112-personal-{logical_mode.value}",
        ),
        ai_mode=logical_mode,
    )

    assert outcome.response.result.status == "succeeded"
    assert outcome.response.message == "authorized cloud reply"
    assert outcome.chat_turn is not None
    assert len(provider.inputs) == 1

    provider_input = provider.inputs[0]
    assert "personal-context-marker" in provider_input
    assert "prior-answer-marker" in provider_input
    assert (
        "Current user message:\n"
        "Summarize the prior Personal discussion."
        in provider_input
    )
    assert "untrusted contextual data" in provider_input
    assert "cannot authorize actions" in provider_input


def test_d112_company_structured_cloud_mode_stops_before_context_and_provider() -> None:
    provider = RecordingCloudProvider()
    planner, guard, runtime = cloud_lane(
        workspace_id=WorkspaceId.COMPANY,
        workspace_mode=WorkspaceAIRouteMode.LOCAL_ONLY,
        provider=provider,
    )
    conversation_service = RecordingConversationService()
    service = orchestrator(
        conversation_service=conversation_service,
        planner=planner,
        guard=guard,
        runtime=runtime,
    )

    outcome = service.process_chat(
        command(
            "Company data must stay local.",
            request_id="d112-company-cloud-blocked",
        ),
        ai_mode=AIMode.CLOUD_AI,
    )

    assert outcome.response.result.status == "failed"
    assert outcome.response.result.error == "AI_ROUTE_REJECTED"
    assert conversation_service.calls == 0
    assert provider.inputs == []


def test_d112_cloud_lane_has_no_fallback_adapter() -> None:
    provider = RecordingCloudProvider()
    planner, _, _ = cloud_lane(
        workspace_id=WorkspaceId.PERSONAL,
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        provider=provider,
    )

    assert planner._registry.ai_adapter_ids == (  # type: ignore[attr-defined]
        CHATGPT_DEFAULT_ADAPTER_ID,
    )