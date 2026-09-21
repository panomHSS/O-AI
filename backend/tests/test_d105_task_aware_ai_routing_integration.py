from __future__ import annotations

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command_decision import CommandDecision
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.ai_router import AIRouter


def decision(preference: str = "unspecified") -> CommandDecision:
    return CommandDecision(
        request_id="d105-request",
        intent="chat_message",
        disposition="defer_to_existing_chat",
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code="test",
    )


def workspace_policy(
    mode: WorkspaceAIRouteMode,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=workspace_id,
        mode=mode,
    )


def router(
    *,
    cloud_available: bool = True,
    local_available: bool = True,
) -> AIRouter:
    available: list[str] = []
    if cloud_available:
        available.append(CHATGPT_DEFAULT_ADAPTER_ID)
    if local_available:
        available.append(LOCAL_AI_ADAPTER_ID)
    return AIRouter(available_adapter_ids=tuple(available))


def test_general_chat_uses_workspace_default() -> None:
    route = router().route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert route.status == "selected"
    assert route.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert route.selection_source == "default"
    assert route.reason_code == "workspace_configured_default"


def test_software_engineering_selects_local_when_permitted() -> None:
    route = router().route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "selected"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID
    assert route.selection_source == "task"
    assert route.reason_code == "task_route_selected"


def test_software_engineering_cannot_bypass_cloud_only_workspace() -> None:
    route = router().route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "rejected"
    assert route.adapter_id is None
    assert route.selection_source is None
    assert route.reason_code == "workspace_local_ai_not_permitted"


def test_general_chat_respects_local_only_workspace_default() -> None:
    route = router().route(
        decision(),
        workspace_policy(
            WorkspaceAIRouteMode.LOCAL_ONLY,
            WorkspaceId.COMPANY,
        ),
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert route.status == "selected"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID
    assert route.selection_source == "default"


def test_explicit_local_precedes_general_chat_policy() -> None:
    route = router().route(
        decision("local_ai_explicit"),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert route.status == "selected"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID
    assert route.selection_source == "explicit"
    assert route.reason_code == "local_ai_explicit"


def test_explicit_cloud_precedes_software_engineering_policy() -> None:
    route = router().route(
        decision("cloud_ai_explicit"),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "selected"
    assert route.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert route.selection_source == "explicit"
    assert route.reason_code == "cloud_ai_explicit"


def test_explicit_cloud_is_denied_when_workspace_forbids_cloud() -> None:
    route = router().route(
        decision("cloud_ai_explicit"),
        workspace_policy(
            WorkspaceAIRouteMode.LOCAL_ONLY,
            WorkspaceId.COMPANY,
        ),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "rejected"
    assert route.adapter_id is None
    assert route.reason_code == "workspace_cloud_egress_denied"


def test_explicit_local_is_denied_when_workspace_forbids_local() -> None:
    route = router().route(
        decision("local_ai_explicit"),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert route.status == "rejected"
    assert route.adapter_id is None
    assert route.reason_code == "workspace_local_ai_not_permitted"


def test_automatic_preserves_workspace_default_instead_of_task_policy() -> None:
    route = router().route(
        decision("automatic"),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "selected"
    assert route.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert route.selection_source == "automatic"
    assert route.reason_code == "workspace_configured_default"


def test_invalid_task_identity_fails_closed() -> None:
    route = router().route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind="software_engineering",  # type: ignore[arg-type]
    )

    assert route.status == "rejected"
    assert route.adapter_id is None
    assert route.selection_source is None
    assert route.reason_code == "invalid_task_kind"


def test_software_engineering_requires_workspace_policy() -> None:
    route = router().route(
        decision(),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "rejected"
    assert route.adapter_id is None
    assert route.reason_code == "workspace_ai_policy_required"


def test_local_unavailable_does_not_fallback_to_cloud() -> None:
    route = router(local_available=False).route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    )

    assert route.status == "unavailable"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID
    assert route.selection_source is None
    assert route.reason_code == "local_ai_unavailable"


def test_cloud_unavailable_does_not_fallback_to_local() -> None:
    route = router(cloud_available=False).route(
        decision(),
        workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert route.status == "unavailable"
    assert route.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert route.selection_source is None
    assert route.reason_code == "cloud_ai_unavailable"
