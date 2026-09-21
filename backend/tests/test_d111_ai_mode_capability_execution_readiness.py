from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.chat import get_ai_brain_capabilities
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.ai_provider_routing import AIProviderRoutingPolicy


class DiscoveryStub:
    def __init__(
        self,
        results: dict[str, tuple[str, tuple[str, ...], str | None]],
    ) -> None:
        self._results = results

    def discover(self, adapter_id: str):
        status, capability_ids, configured_model_id = self._results[adapter_id]
        return SimpleNamespace(
            status=status,
            capability_ids=capability_ids,
            configured_model_id=configured_model_id,
        )


def workspace_policy() -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=WorkspaceId.PERSONAL,
        mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )


def provider_policy() -> AIProviderRoutingPolicy:
    return AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(
            {
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            }
        ),
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


def test_d111_capability_uses_execution_discovery_without_cross_provider_fallback() -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=workspace_policy(),
        provider_policy=provider_policy(),
        ai_discovery=DiscoveryStub(
            {
                CHATGPT_DEFAULT_ADAPTER_ID: (
                    "unavailable",
                    (AI_CAPABILITY_TEXT_GENERATION,),
                    None,
                ),
                LOCAL_AI_ADAPTER_ID: (
                    "available",
                    (AI_CAPABILITY_TEXT_GENERATION,),
                    "local-model",
                ),
            }
        ),
    )

    general = task(response, "general_chat")

    automatic = mode(general, "auto")
    assert automatic.status == "unavailable"
    assert automatic.provider_class == "cloud_ai"
    assert automatic.reason_code == "cloud_ai_unavailable"
    assert automatic.fallback_allowed is False

    cloud = mode(general, "cloud_ai")
    assert cloud.status == "unavailable"
    assert cloud.provider_class == "cloud_ai"
    assert cloud.reason_code == "cloud_ai_unavailable"
    assert cloud.fallback_allowed is False

    local = mode(general, "local_ai")
    assert local.status == "ready"
    assert local.provider_class == "local_ai"


def test_d111_capability_requires_same_discovery_shape_as_execution_planner() -> None:
    invalid_cloud_shapes = (
        ("available", (), "cloud-model"),
        ("available", ("other_capability",), "cloud-model"),
        ("available", (AI_CAPABILITY_TEXT_GENERATION,), None),
        ("unavailable", (AI_CAPABILITY_TEXT_GENERATION,), "cloud-model"),
    )

    for status, capability_ids, configured_model_id in invalid_cloud_shapes:
        response = get_ai_brain_capabilities(
            workspace_policy=workspace_policy(),
            provider_policy=provider_policy(),
            ai_discovery=DiscoveryStub(
                {
                    CHATGPT_DEFAULT_ADAPTER_ID: (
                        status,
                        capability_ids,
                        configured_model_id,
                    ),
                    LOCAL_AI_ADAPTER_ID: (
                        "available",
                        (AI_CAPABILITY_TEXT_GENERATION,),
                        "local-model",
                    ),
                }
            ),
        )

        general = task(response, "general_chat")
        assert mode(general, "cloud_ai").status == "unavailable"
        assert mode(general, "auto").status == "unavailable"


def test_d111_capability_marks_cloud_ready_when_discovery_is_execution_ready() -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=workspace_policy(),
        provider_policy=provider_policy(),
        ai_discovery=DiscoveryStub(
            {
                CHATGPT_DEFAULT_ADAPTER_ID: (
                    "available",
                    (AI_CAPABILITY_TEXT_GENERATION,),
                    "cloud-model",
                ),
                LOCAL_AI_ADAPTER_ID: (
                    "available",
                    (AI_CAPABILITY_TEXT_GENERATION,),
                    "local-model",
                ),
            }
        ),
    )

    general = task(response, "general_chat")
    assert mode(general, "auto").status == "ready"
    assert mode(general, "cloud_ai").status == "ready"
    assert mode(general, "local_ai").status == "ready"