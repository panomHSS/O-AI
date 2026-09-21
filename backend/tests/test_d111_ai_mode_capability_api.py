from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from app.api.v1.chat import get_ai_brain_capabilities, send_chat_message
from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.schemas.chat import ChatRequest
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.command_orchestrator import CommandOrchestrator


def workspace_policy(
    mode: WorkspaceAIRouteMode,
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=workspace_id,
        mode=mode,
    )


def provider_policy(*, local_enabled: bool = True) -> AIProviderRoutingPolicy:
    enabled = {CHATGPT_DEFAULT_ADAPTER_ID}
    if local_enabled:
        enabled.add(LOCAL_AI_ADAPTER_ID)
    return AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(enabled),
    )


def task(response, task_kind: str):
    return next(
        item
        for item in response.data.tasks
        if item.task_kind == task_kind
    )


def mode(task_capability, logical_mode: str):
    return next(
        item
        for item in task_capability.modes
        if item.mode == logical_mode
    )


def test_d111_chat_request_accepts_only_bounded_logical_ai_mode() -> None:
    request = ChatRequest(message="hello", ai_mode="local_ai")
    assert request.ai_mode is AIMode.LOCAL_AI

    for field_name in (
        "provider",
        "provider_id",
        "adapter_id",
        "model",
        "model_id",
        "base_url",
        "endpoint",
        "api_key",
        "credential",
        "fallback_target",
    ):
        with pytest.raises(ValidationError):
            ChatRequest(
                message="hello",
                **{field_name: "attacker-value"},
            )


def test_d111_personal_capabilities_are_workspace_derived_and_bounded() -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=workspace_policy(
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
        ),
        provider_policy=provider_policy(local_enabled=True),
    )

    assert response.data.workspace_id == "personal"
    general = task(response, "general_chat")
    engineering = task(response, "software_engineering")

    assert mode(general, "auto").status == "ready"
    assert mode(general, "local_ai").status == "ready"
    assert mode(general, "cloud_ai").status == "ready"

    assert mode(engineering, "auto").status == "ready"
    assert mode(engineering, "local_ai").status == "ready"
    assert mode(engineering, "cloud_ai").status == "blocked"
    assert (
        mode(engineering, "cloud_ai").reason_code
        == "d111_task_mode_not_permitted"
    )

    encoded = repr(response.data.model_dump())
    for forbidden in (
        "effective_adapter_id",
        "adapter_id",
        "model_id",
        "base_url",
        "api_key",
        "credential",
        "authorization",
        "execution_plan",
    ):
        assert forbidden not in encoded


def test_d111_company_capability_cannot_expand_local_only_workspace() -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=workspace_policy(
            WorkspaceAIRouteMode.LOCAL_ONLY,
            workspace_id=WorkspaceId.COMPANY,
        ),
        provider_policy=provider_policy(local_enabled=True),
    )
    general = task(response, "general_chat")

    cloud = mode(general, "cloud_ai")
    assert cloud.status == "blocked"
    assert cloud.provider_class is None
    assert cloud.reason_code == "workspace_cloud_egress_denied"


def test_d111_engineering_auto_is_unavailable_when_local_disabled_no_cloud_fallback() -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=workspace_policy(
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
        ),
        provider_policy=provider_policy(local_enabled=False),
    )
    engineering = task(response, "software_engineering")

    automatic = mode(engineering, "auto")
    assert automatic.status == "unavailable"
    assert automatic.provider_class == "local_ai"
    assert automatic.reason_code == "local_ai_unavailable"
    assert automatic.fallback_allowed is False


def test_d111_chat_api_threads_only_typed_mode_to_orchestrator() -> None:
    source = inspect.getsource(send_chat_message)

    assert "ai_mode=payload.ai_mode" in source
    for forbidden in (
        "payload.provider",
        "payload.adapter",
        "payload.model",
        "payload.base_url",
        "payload.api_key",
        "payload.credential",
    ):
        assert forbidden not in source


def test_d111_orchestrator_preserves_legacy_path_when_mode_omitted() -> None:
    signature = inspect.signature(CommandOrchestrator.process_chat)
    assert signature.parameters["ai_mode"].default is None

    source = inspect.getsource(CommandOrchestrator.process_chat)
    assert "if ai_mode is None" in source
    assert "self._planner.plan(command)" in source
    assert "self._planner.plan(command, ai_mode=ai_mode)" in source

    for forbidden in (
        "provider_id",
        "model_id",
        "base_url",
        "api_key",
        "credential",
    ):
        assert forbidden not in source
