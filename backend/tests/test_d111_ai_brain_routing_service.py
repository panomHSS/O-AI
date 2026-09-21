from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.contracts.ai_brain_routing import (
    AIBrainRouteStatus,
    AIMode,
    AIProviderClass,
)
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.ai_brain_routing import (
    AIBrainRoutingPolicy,
    AIProviderCapabilityRegistry,
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


def capabilities(
    *,
    cloud: bool = True,
    local: bool = True,
) -> AIProviderCapabilityRegistry:
    values: list[str] = []
    if cloud:
        values.append(CHATGPT_DEFAULT_ADAPTER_ID)
    if local:
        values.append(LOCAL_AI_ADAPTER_ID)
    return AIProviderCapabilityRegistry(values)


def resolve(
    *,
    task_kind: AITaskKind,
    requested_mode: AIMode,
    mode: WorkspaceAIRouteMode = WorkspaceAIRouteMode.CLOUD_PREFERRED,
    cloud: bool = True,
    local: bool = True,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
):
    return AIBrainRoutingPolicy().resolve(
        task_kind=task_kind,
        requested_mode=requested_mode,
        workspace_policy=workspace_policy(
            mode,
            workspace_id=workspace_id,
        ),
        capabilities=capabilities(cloud=cloud, local=local),
    )


def test_d111_task_policy_preserves_d110_local_only_boundary() -> None:
    policy = AIBrainRoutingPolicy().task_policy_for(
        AITaskKind.SOFTWARE_ENGINEERING
    )

    assert policy.allowed_provider_classes == frozenset(
        {AIProviderClass.LOCAL_AI}
    )
    assert policy.auto_provider_class is AIProviderClass.LOCAL_AI
    assert policy.fallback_allowed is False


def test_d111_general_chat_auto_preserves_existing_workspace_default() -> None:
    personal = resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.AUTO,
    )
    company = resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.AUTO,
        mode=WorkspaceAIRouteMode.LOCAL_ONLY,
        workspace_id=WorkspaceId.COMPANY,
    )

    assert (
        personal.route_status,
        personal.effective_provider_class,
        personal.effective_adapter_id,
    ) == (
        AIBrainRouteStatus.READY,
        AIProviderClass.CLOUD_AI,
        CHATGPT_DEFAULT_ADAPTER_ID,
    )
    assert (
        company.route_status,
        company.effective_provider_class,
        company.effective_adapter_id,
    ) == (
        AIBrainRouteStatus.READY,
        AIProviderClass.LOCAL_AI,
        LOCAL_AI_ADAPTER_ID,
    )


def test_d111_software_engineering_auto_and_local_resolve_exact_local() -> None:
    for requested_mode in (AIMode.AUTO, AIMode.LOCAL_AI):
        result = resolve(
            task_kind=AITaskKind.SOFTWARE_ENGINEERING,
            requested_mode=requested_mode,
        )
        assert (
            result.route_status,
            result.effective_provider_class,
            result.effective_adapter_id,
            result.fallback_allowed,
        ) == (
            AIBrainRouteStatus.READY,
            AIProviderClass.LOCAL_AI,
            LOCAL_AI_ADAPTER_ID,
            False,
        )


def test_d111_software_engineering_cloud_is_blocked_before_capability() -> None:
    result = resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        requested_mode=AIMode.CLOUD_AI,
    )

    assert result.route_status is AIBrainRouteStatus.BLOCKED
    assert result.effective_provider_class is None
    assert result.effective_adapter_id is None
    assert result.reason_code == "d111_task_mode_not_permitted"
    assert result.fallback_allowed is False


def test_d111_workspace_policy_cannot_be_expanded_by_mode() -> None:
    cloud = resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.CLOUD_AI,
        mode=WorkspaceAIRouteMode.LOCAL_ONLY,
        workspace_id=WorkspaceId.COMPANY,
    )
    local = resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.LOCAL_AI,
        mode=WorkspaceAIRouteMode.CLOUD_ONLY,
    )

    assert (
        cloud.route_status,
        cloud.reason_code,
        cloud.effective_adapter_id,
    ) == (
        AIBrainRouteStatus.BLOCKED,
        "workspace_cloud_egress_denied",
        None,
    )
    assert (
        local.route_status,
        local.reason_code,
        local.effective_adapter_id,
    ) == (
        AIBrainRouteStatus.BLOCKED,
        "workspace_local_ai_not_permitted",
        None,
    )


def test_d111_unavailable_local_has_no_cloud_fallback() -> None:
    result = resolve(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        requested_mode=AIMode.AUTO,
        local=False,
        cloud=True,
    )

    assert result.route_status is AIBrainRouteStatus.UNAVAILABLE
    assert result.effective_provider_class is AIProviderClass.LOCAL_AI
    assert result.effective_adapter_id is None
    assert result.reason_code == "local_ai_unavailable"
    assert result.fallback_allowed is False


def test_d111_unavailable_cloud_has_no_local_fallback() -> None:
    result = resolve(
        task_kind=AITaskKind.GENERAL_CHAT,
        requested_mode=AIMode.CLOUD_AI,
        cloud=False,
        local=True,
    )

    assert result.route_status is AIBrainRouteStatus.UNAVAILABLE
    assert result.effective_provider_class is AIProviderClass.CLOUD_AI
    assert result.effective_adapter_id is None
    assert result.reason_code == "cloud_ai_unavailable"
    assert result.fallback_allowed is False


def test_d111_capability_registry_rejects_arbitrary_adapter_ids() -> None:
    with pytest.raises(
        ValueError,
        match="invalid_ai_provider_capability_registry",
    ):
        AIProviderCapabilityRegistry(("arbitrary.provider",))


def test_d111_resolver_inputs_have_no_model_endpoint_or_credential_authority() -> None:
    parameters = inspect.signature(AIBrainRoutingPolicy.resolve).parameters
    assert tuple(parameters) == (
        "self",
        "task_kind",
        "requested_mode",
        "workspace_policy",
        "capabilities",
    )


def test_d111_routing_service_has_no_execution_network_or_mutation_imports() -> None:
    source_file = Path(
        inspect.getsourcefile(AIBrainRoutingPolicy) or ""
    )
    tree = ast.parse(source_file.read_text(encoding="utf-8"))

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden_fragments = (
        "ai_runtime",
        "execution_guard",
        "execution_planner",
        "providers",
        "openai",
        "ollama",
        "http",
        "requests",
        "socket",
        "subprocess",
        "credential",
        "repository",
        "filesystem",
        "git",
    )
    assert not any(
        fragment in module
        for module in imports
        for fragment in forbidden_fragments
    )

    source = inspect.getsource(AIBrainRoutingPolicy).lower()
    for forbidden in (
        ".generate(",
        "authorize(",
        "retry",
        "api_key",
        "base_url",
        "model_id",
        "repository_root",
        "git push",
        "subprocess",
    ):
        assert forbidden not in source
