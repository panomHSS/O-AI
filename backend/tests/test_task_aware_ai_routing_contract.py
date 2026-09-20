from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.task_aware_ai_routing import (
    AITaskKind,
    AITaskRouteDirective,
    TaskAwareAIRoutingPolicy,
    TaskAwareRouteResolution,
)
from app.contracts.workspace import WorkspaceId


def policy() -> TaskAwareAIRoutingPolicy:
    return TaskAwareAIRoutingPolicy(
        general_chat=AITaskRouteDirective.WORKSPACE_DEFAULT,
        software_engineering=AITaskRouteDirective.LOCAL_AI,
    )


def test_exact_task_taxonomy_v1() -> None:
    assert tuple(item.value for item in AITaskKind) == (
        "general_chat",
        "software_engineering",
    )


def test_exact_route_directives_v1() -> None:
    assert tuple(item.value for item in AITaskRouteDirective) == (
        "workspace_default",
        "local_ai",
        "cloud_ai",
    )


def test_policy_is_frozen_slotted_and_covers_exact_taxonomy() -> None:
    value = policy()

    assert not hasattr(value, "__dict__")
    assert value.directive_for(AITaskKind.GENERAL_CHAT) is (
        AITaskRouteDirective.WORKSPACE_DEFAULT
    )
    assert value.directive_for(AITaskKind.SOFTWARE_ENGINEERING) is (
        AITaskRouteDirective.LOCAL_AI
    )

    with pytest.raises(FrozenInstanceError):
        value.general_chat = AITaskRouteDirective.CLOUD_AI  # type: ignore[misc]


def test_policy_missing_or_unknown_entry_fails_closed() -> None:
    with pytest.raises(TypeError):
        TaskAwareAIRoutingPolicy(  # type: ignore[call-arg]
            general_chat=AITaskRouteDirective.WORKSPACE_DEFAULT,
        )

    with pytest.raises(TypeError):
        TaskAwareAIRoutingPolicy(  # type: ignore[call-arg]
            general_chat=AITaskRouteDirective.WORKSPACE_DEFAULT,
            software_engineering=AITaskRouteDirective.LOCAL_AI,
            arbitrary_task=AITaskRouteDirective.CLOUD_AI,
        )


def test_unknown_task_and_directive_fail_closed() -> None:
    value = policy()

    with pytest.raises(ValueError, match="invalid_task_kind"):
        value.directive_for("software_engineering")

    with pytest.raises(ValueError, match="invalid_task_routing_policy"):
        TaskAwareAIRoutingPolicy(
            general_chat="workspace_default",  # type: ignore[arg-type]
            software_engineering=AITaskRouteDirective.LOCAL_AI,
        )


def test_resolution_is_frozen_slotted_and_bounded() -> None:
    value = TaskAwareRouteResolution(
        workspace_id=WorkspaceId.COMPANY,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        effective_directive=AITaskRouteDirective.LOCAL_AI,
        status="selected",
        adapter_id=LOCAL_AI_ADAPTER_ID,
        selection_source="task",
        reason_code="task_route_selected",
    )

    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.reason_code = "changed"  # type: ignore[misc]


def test_resolution_rejects_arbitrary_adapter_and_invalid_shape() -> None:
    common = dict(
        workspace_id=WorkspaceId.COMPANY,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        effective_directive=AITaskRouteDirective.LOCAL_AI,
        reason_code="task_route_selected",
    )

    with pytest.raises(ValueError, match="task_route_adapter_invalid"):
        TaskAwareRouteResolution(
            **common,
            status="selected",
            adapter_id="arbitrary.provider",
            selection_source="task",
        )

    with pytest.raises(ValueError, match="task_route_rejected_invalid"):
        TaskAwareRouteResolution(
            **common,
            status="rejected",
            adapter_id=LOCAL_AI_ADAPTER_ID,
            selection_source=None,
        )

    with pytest.raises(ValueError, match="task_route_selected_invalid"):
        TaskAwareRouteResolution(
            **common,
            status="selected",
            adapter_id=None,
            selection_source="task",
        )


def test_contract_has_no_model_backend_base_url_or_execution_fields() -> None:
    names = {item.name for item in fields(TaskAwareRouteResolution)}
    names.update(item.name for item in fields(TaskAwareAIRoutingPolicy))

    forbidden = {
        "model_id",
        "backend_id",
        "base_url",
        "runtime_url",
        "provider_endpoint",
        "credential",
        "api_key",
        "execution_plan",
        "execution_authorized",
        "context",
    }
    assert names.isdisjoint(forbidden)
