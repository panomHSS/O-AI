from __future__ import annotations

import pytest

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command import CommandRequest
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime, AIExecutionRejectedError
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner


class RecordingAI:
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


class Discovery:
    def discover(self, adapter_id: str):
        class Result:
            status = "available"
            capability_ids = (AI_CAPABILITY_TEXT_GENERATION,)
            configured_model_id = "configured-model"

        return Result()


def command(
    message: str = "hello",
    *,
    request_id: str = "d111-b02",
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


def build_lane(
    *,
    workspace_mode: WorkspaceAIRouteMode,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    cloud_enabled: bool = True,
    local_enabled: bool = True,
    cloud_error: Exception | None = None,
    local_error: Exception | None = None,
):
    cloud = RecordingAI(
        CHATGPT_DEFAULT_ADAPTER_ID,
        error=cloud_error,
    )
    local = RecordingAI(
        LOCAL_AI_ADAPTER_ID,
        error=local_error,
    )
    registry = AdapterRegistry((cloud, local))

    enabled: set[str] = set()
    if cloud_enabled:
        enabled.add(CHATGPT_DEFAULT_ADAPTER_ID)
    if local_enabled:
        enabled.add(LOCAL_AI_ADAPTER_ID)

    router = AIRouter(
        registry=registry,
        policy=AIProviderRoutingPolicy(
            default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
            enabled_adapter_ids=frozenset(enabled),
        ),
        workspace_policy=WorkspaceAIRoutingPolicy(
            workspace_id=workspace_id,
            mode=workspace_mode,
        ),
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=router,
        ai_discovery=Discovery(),  # type: ignore[arg-type]
        permission_policy=object(),  # type: ignore[arg-type]
    )
    guard = ExecutionGuard(
        registry=registry,
        permission_policy=object(),  # type: ignore[arg-type]
    )
    runtime = AIRuntime(registry=registry)
    return cloud, local, router, planner, guard, runtime


def test_d111_local_mode_runs_through_d35_d36_d49_once() -> None:
    cloud, local, _, planner, guard, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    request = command()

    planning = planner.plan(
        request,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        ai_mode=AIMode.LOCAL_AI,
    )
    assert planning.status == "planned"
    assert planning.target_kind == "ai"
    assert planning.plan is not None
    assert planning.plan.adapter_id == LOCAL_AI_ADAPTER_ID

    authorization = guard.authorize(request, planning)
    assert authorization.status == "authorized"
    adapter = runtime.bind(request, authorization)
    assert adapter.adapter_id == LOCAL_AI_ADAPTER_ID

    result = adapter.generate(AIRequest(content="bounded context"))
    assert result.content == "local_ai.default reply"
    assert cloud.requests == []
    assert len(local.requests) == 1


def test_d111_engineering_auto_remains_exact_local() -> None:
    cloud, local, _, planner, _, _ = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    planning = planner.plan(
        command(),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        ai_mode=AIMode.AUTO,
    )

    assert planning.status == "planned"
    assert planning.plan is not None
    assert planning.plan.adapter_id == LOCAL_AI_ADAPTER_ID
    assert cloud.requests == []
    assert local.requests == []


def test_d111_engineering_cloud_mode_is_blocked_before_d36_d49() -> None:
    cloud, local, _, planner, guard, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    request = command()

    planning = planner.plan(
        request,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        ai_mode=AIMode.CLOUD_AI,
    )

    assert planning.status == "rejected"
    assert planning.plan is None
    assert planning.reason_code == "ai_route_rejected"

    authorization = guard.authorize(request, planning)
    assert authorization.status == "rejected"

    with pytest.raises(
        AIExecutionRejectedError,
        match="ai_execution_not_authorized",
    ):
        runtime.bind(request, authorization)

    assert cloud.requests == []
    assert local.requests == []


def test_d111_local_unavailable_stops_at_planning_without_cloud_fallback() -> None:
    cloud, local, _, planner, _, _ = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        cloud_enabled=True,
        local_enabled=False,
    )

    planning = planner.plan(
        command(),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        ai_mode=AIMode.AUTO,
    )

    assert planning.status == "unavailable"
    assert planning.reason_code == "local_ai_unavailable"
    assert planning.plan is None
    assert cloud.requests == []
    assert local.requests == []


def test_d111_general_chat_cloud_mode_uses_existing_cloud_compatibility_lane() -> None:
    cloud, local, _, planner, guard, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    request = command("ordinary chat")

    planning = planner.plan(
        request,
        task_kind=AITaskKind.GENERAL_CHAT,
        ai_mode=AIMode.CLOUD_AI,
    )
    assert planning.status == "planned"
    assert planning.plan is not None
    assert planning.plan.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID

    authorization = guard.authorize(request, planning)
    assert authorization.status == "authorized"
    adapter = runtime.bind(request, authorization)
    result = adapter.generate(AIRequest(content="existing cloud context"))

    assert result.content == "chatgpt.default reply"
    assert len(cloud.requests) == 1
    assert local.requests == []


def test_d111_structured_mode_overrides_plaintext_provider_hint_only_for_route() -> None:
    cloud, local, _, planner, guard, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    request = command("Use ChatGPT for this command")

    planning = planner.plan(
        request,
        task_kind=AITaskKind.GENERAL_CHAT,
        ai_mode=AIMode.LOCAL_AI,
    )
    assert planning.status == "planned"
    assert planning.plan is not None
    assert planning.plan.adapter_id == LOCAL_AI_ADAPTER_ID

    authorization = guard.authorize(request, planning)
    adapter = runtime.bind(request, authorization)
    adapter.generate(AIRequest(content="verified context"))

    assert cloud.requests == []
    assert len(local.requests) == 1


def test_d111_route_decision_alone_is_not_d49_execution_authority() -> None:
    cloud, local, router, _, _, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )
    decision = CommandDecisionEngine().decide(command())
    route = router.route_mode(
        decision,
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.LOCAL_AI,
    )

    assert route.status == "selected"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID

    with pytest.raises(
        AIExecutionRejectedError,
        match="invalid_execution_authorization",
    ):
        runtime.bind(command(), route)  # type: ignore[arg-type]

    assert cloud.requests == []
    assert local.requests == []


def test_d111_provider_failure_has_no_cross_provider_retry() -> None:
    cloud, local, _, planner, guard, runtime = build_lane(
        workspace_mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        local_error=RuntimeError("local failed"),
    )
    request = command()
    planning = planner.plan(
        request,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        ai_mode=AIMode.LOCAL_AI,
    )
    authorization = guard.authorize(request, planning)
    adapter = runtime.bind(request, authorization)

    with pytest.raises(RuntimeError, match="local failed"):
        adapter.generate(AIRequest(content="bounded context"))

    assert cloud.requests == []
    assert len(local.requests) == 1
