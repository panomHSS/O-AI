from __future__ import annotations

import inspect

from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.command_decision import CommandDecision
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import WorkspaceAIRouteMode, WorkspaceAIRoutingPolicy
from app.services.ai_router import AIRouter


def decision(preference: str = "unspecified") -> CommandDecision:
    return CommandDecision(
        request_id="d105-security",
        intent="chat_message",
        disposition="defer_to_existing_chat",
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code="test",
    )


def policy(mode: WorkspaceAIRouteMode, workspace_id: WorkspaceId = WorkspaceId.PERSONAL) -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(workspace_id=workspace_id, mode=mode)


def router(*, cloud_available: bool = True, local_available: bool = True) -> AIRouter:
    available = []
    if cloud_available:
        available.append(CHATGPT_DEFAULT_ADAPTER_ID)
    if local_available:
        available.append(LOCAL_AI_ADAPTER_ID)
    return AIRouter(available_adapter_ids=tuple(available))


def test_task_policy_cannot_expand_cloud_only_workspace() -> None:
    route = router().route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    assert (route.status, route.adapter_id, route.selection_source, route.reason_code) == (
        "rejected", None, None, "workspace_local_ai_not_permitted"
    )


def test_task_policy_cannot_expand_company_local_only_workspace() -> None:
    route = router().route(
        decision("cloud_ai_explicit"),
        policy(WorkspaceAIRouteMode.LOCAL_ONLY, WorkspaceId.COMPANY),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    assert (route.status, route.adapter_id, route.reason_code) == (
        "rejected", None, "workspace_cloud_egress_denied"
    )


def test_explicit_provider_precedence_is_preserved() -> None:
    cloud = router().route(
        decision("cloud_ai_explicit"),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    local = router().route(
        decision("local_ai_explicit"),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.GENERAL_CHAT,
    )
    assert (cloud.adapter_id, cloud.selection_source) == (CHATGPT_DEFAULT_ADAPTER_ID, "explicit")
    assert (local.adapter_id, local.selection_source) == (LOCAL_AI_ADAPTER_ID, "explicit")


def test_general_chat_preserves_workspace_default() -> None:
    cloud = router().route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.GENERAL_CHAT,
    )
    local = router().route(
        decision(),
        policy(WorkspaceAIRouteMode.LOCAL_ONLY, WorkspaceId.COMPANY),
        task_kind=AITaskKind.GENERAL_CHAT,
    )
    assert cloud.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert local.adapter_id == LOCAL_AI_ADAPTER_ID


def test_software_engineering_uses_exact_local_adapter() -> None:
    route = router().route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    assert (route.status, route.adapter_id, route.selection_source) == (
        "selected", LOCAL_AI_ADAPTER_ID, "task"
    )


def test_invalid_raw_task_string_fails_closed() -> None:
    route = router().route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind="software_engineering",  # type: ignore[arg-type]
    )
    assert (route.status, route.adapter_id, route.reason_code) == (
        "rejected", None, "invalid_task_kind"
    )


def test_no_silent_provider_fallback() -> None:
    local = router(local_available=False).route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    cloud = router(cloud_available=False).route(
        decision(),
        policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_kind=AITaskKind.GENERAL_CHAT,
    )
    assert (local.status, local.adapter_id, local.reason_code) == (
        "unavailable", LOCAL_AI_ADAPTER_ID, "local_ai_unavailable"
    )
    assert (cloud.status, cloud.adapter_id, cloud.reason_code) == (
        "unavailable", CHATGPT_DEFAULT_ADAPTER_ID, "cloud_ai_unavailable"
    )


def test_software_engineering_requires_workspace_authority() -> None:
    route = router().route(
        decision(),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )
    assert (route.status, route.adapter_id, route.reason_code) == (
        "rejected", None, "workspace_ai_policy_required"
    )


def test_router_remains_selection_only() -> None:
    source = inspect.getsource(AIRouter)
    assert ".generate(" not in source
    assert "AIRuntime" not in source
    assert "ExecutionGuard" not in source


def test_task_routing_does_not_read_context_credentials_or_retry() -> None:
    source = inspect.getsource(AIRouter._route_with_task_policy)
    for forbidden in ("ContextResolver", "ContextSnapshot", "CredentialAccessBroker", "api_key", "connector"):
        assert forbidden not in source
    assert source.count("self._is_route_available(adapter_id)") == 1
    assert "while " not in source
    assert "retry" not in source.lower()
    assert "fallback" not in source.lower()
