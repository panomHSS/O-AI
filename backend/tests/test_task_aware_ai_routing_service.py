from __future__ import annotations

import pytest

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.task_aware_ai_routing import (
    AITaskKind,
    AITaskRouteDirective,
    TaskAwareAIRoutingPolicy,
)
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.task_aware_ai_routing import TaskAwareAIRoutingResolver


def task_policy(
    *,
    general_chat: AITaskRouteDirective = AITaskRouteDirective.WORKSPACE_DEFAULT,
    software_engineering: AITaskRouteDirective = AITaskRouteDirective.LOCAL_AI,
) -> TaskAwareAIRoutingPolicy:
    return TaskAwareAIRoutingPolicy(
        general_chat=general_chat,
        software_engineering=software_engineering,
    )


def workspace_policy(
    mode: WorkspaceAIRouteMode,
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=workspace_id,
        mode=mode,
    )


def test_unspecified_may_use_task_local_route_when_d98_permits() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="unspecified",
        workspace_policy=workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_policy=task_policy(),
    )

    assert result.status == "selected"
    assert result.adapter_id == LOCAL_AI_ADAPTER_ID
    assert result.selection_source == "task"
    assert result.effective_directive is AITaskRouteDirective.LOCAL_AI
    assert result.reason_code == "task_route_selected"


def test_unspecified_workspace_default_uses_exact_d98_default() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        provider_preference="unspecified",
        workspace_policy=workspace_policy(WorkspaceAIRouteMode.LOCAL_PREFERRED),
        task_policy=task_policy(),
    )

    assert result.status == "selected"
    assert result.adapter_id == LOCAL_AI_ADAPTER_ID
    assert result.selection_source == "workspace_default"
    assert result.effective_directive is AITaskRouteDirective.WORKSPACE_DEFAULT
    assert result.reason_code == "workspace_default_selected"


@pytest.mark.parametrize(
    ("mode", "task_directive", "expected_adapter"),
    [
        (
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
            AITaskRouteDirective.LOCAL_AI,
            CHATGPT_DEFAULT_ADAPTER_ID,
        ),
        (
            WorkspaceAIRouteMode.LOCAL_PREFERRED,
            AITaskRouteDirective.CLOUD_AI,
            LOCAL_AI_ADAPTER_ID,
        ),
    ],
)
def test_automatic_ignores_task_directive_and_preserves_d98_default(
    mode: WorkspaceAIRouteMode,
    task_directive: AITaskRouteDirective,
    expected_adapter: str,
) -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="automatic",
        workspace_policy=workspace_policy(mode),
        task_policy=task_policy(software_engineering=task_directive),
    )

    assert result.status == "selected"
    assert result.adapter_id == expected_adapter
    assert result.selection_source == "workspace_default"
    assert result.effective_directive is AITaskRouteDirective.WORKSPACE_DEFAULT
    assert result.reason_code == "workspace_default_selected"


def test_explicit_cloud_precedes_task_local_when_d98_permits() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="cloud_ai_explicit",
        workspace_policy=workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_policy=task_policy(software_engineering=AITaskRouteDirective.LOCAL_AI),
    )

    assert result.status == "selected"
    assert result.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert result.selection_source == "explicit"
    assert result.effective_directive is AITaskRouteDirective.CLOUD_AI
    assert result.reason_code == "explicit_route_selected"


def test_explicit_local_precedes_task_cloud_when_d98_permits() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="local_ai_explicit",
        workspace_policy=workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        task_policy=task_policy(software_engineering=AITaskRouteDirective.CLOUD_AI),
    )

    assert result.status == "selected"
    assert result.adapter_id == LOCAL_AI_ADAPTER_ID
    assert result.selection_source == "explicit"
    assert result.effective_directive is AITaskRouteDirective.LOCAL_AI
    assert result.reason_code == "explicit_route_selected"


def test_company_local_only_rejects_task_cloud_without_substitution() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="unspecified",
        workspace_policy=workspace_policy(
            WorkspaceAIRouteMode.LOCAL_ONLY,
            workspace_id=WorkspaceId.COMPANY,
        ),
        task_policy=task_policy(software_engineering=AITaskRouteDirective.CLOUD_AI),
    )

    assert result.status == "rejected"
    assert result.adapter_id is None
    assert result.selection_source is None
    assert result.effective_directive is AITaskRouteDirective.CLOUD_AI
    assert result.reason_code == "workspace_cloud_egress_denied"


def test_cloud_only_rejects_task_local_without_substitution() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="unspecified",
        workspace_policy=workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        task_policy=task_policy(software_engineering=AITaskRouteDirective.LOCAL_AI),
    )

    assert result.status == "rejected"
    assert result.adapter_id is None
    assert result.selection_source is None
    assert result.effective_directive is AITaskRouteDirective.LOCAL_AI
    assert result.reason_code == "workspace_local_ai_not_permitted"


def test_explicit_cloud_denied_does_not_fall_back_to_task_local() -> None:
    result = TaskAwareAIRoutingResolver().resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        provider_preference="cloud_ai_explicit",
        workspace_policy=workspace_policy(
            WorkspaceAIRouteMode.LOCAL_ONLY,
            workspace_id=WorkspaceId.COMPANY,
        ),
        task_policy=task_policy(software_engineering=AITaskRouteDirective.LOCAL_AI),
    )

    assert result.status == "rejected"
    assert result.adapter_id is None
    assert result.selection_source is None
    assert result.effective_directive is AITaskRouteDirective.CLOUD_AI
    assert result.reason_code == "workspace_cloud_egress_denied"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("task_kind", "software_engineering", "invalid_task_kind"),
        ("provider_preference", "task_aware", "invalid_provider_preference"),
        ("workspace_policy", object(), "invalid_workspace_ai_policy"),
        ("task_policy", object(), "invalid_task_routing_policy"),
    ],
)
def test_invalid_inputs_fail_closed(
    field: str,
    value: object,
    reason: str,
) -> None:
    kwargs: dict[str, object] = {
        "task_kind": AITaskKind.SOFTWARE_ENGINEERING,
        "provider_preference": "unspecified",
        "workspace_policy": workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        "task_policy": task_policy(),
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=reason):
        TaskAwareAIRoutingResolver().resolve(**kwargs)  # type: ignore[arg-type]
