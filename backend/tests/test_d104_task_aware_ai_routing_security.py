from __future__ import annotations

import ast
import inspect
from pathlib import Path

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
    directive: AITaskRouteDirective,
) -> TaskAwareAIRoutingPolicy:
    return TaskAwareAIRoutingPolicy(
        general_chat=directive,
        software_engineering=directive,
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


def resolve(
    *,
    task_kind: AITaskKind = AITaskKind.SOFTWARE_ENGINEERING,
    provider_preference: str = "unspecified",
    mode: WorkspaceAIRouteMode = WorkspaceAIRouteMode.CLOUD_PREFERRED,
    directive: AITaskRouteDirective = AITaskRouteDirective.WORKSPACE_DEFAULT,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
):
    return TaskAwareAIRoutingResolver().resolve(
        task_kind=task_kind,
        provider_preference=provider_preference,  # type: ignore[arg-type]
        workspace_policy=workspace_policy(mode, workspace_id=workspace_id),
        task_policy=task_policy(directive),
    )


def test_company_local_only_task_cloud_rejects_without_local_substitution() -> None:
    result = resolve(
        mode=WorkspaceAIRouteMode.LOCAL_ONLY,
        directive=AITaskRouteDirective.CLOUD_AI,
        workspace_id=WorkspaceId.COMPANY,
    )

    assert result.status == "rejected"
    assert result.adapter_id is None
    assert result.selection_source is None
    assert result.reason_code == "workspace_cloud_egress_denied"


def test_cloud_only_task_local_rejects_without_cloud_substitution() -> None:
    result = resolve(
        mode=WorkspaceAIRouteMode.CLOUD_ONLY,
        directive=AITaskRouteDirective.LOCAL_AI,
    )

    assert result.status == "rejected"
    assert result.adapter_id is None
    assert result.selection_source is None
    assert result.reason_code == "workspace_local_ai_not_permitted"


def test_explicit_cloud_beats_task_local_when_d98_permits() -> None:
    result = resolve(
        provider_preference="cloud_ai_explicit",
        mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        directive=AITaskRouteDirective.LOCAL_AI,
    )

    assert result.status == "selected"
    assert result.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert result.selection_source == "explicit"


def test_explicit_local_beats_task_cloud_when_d98_permits() -> None:
    result = resolve(
        provider_preference="local_ai_explicit",
        mode=WorkspaceAIRouteMode.LOCAL_PREFERRED,
        directive=AITaskRouteDirective.CLOUD_AI,
    )

    assert result.status == "selected"
    assert result.adapter_id == LOCAL_AI_ADAPTER_ID
    assert result.selection_source == "explicit"


@pytest.mark.parametrize(
    ("mode", "directive", "expected"),
    [
        (
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
            AITaskRouteDirective.LOCAL_AI,
            CHATGPT_DEFAULT_ADAPTER_ID,
        ),
        (
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
            AITaskRouteDirective.CLOUD_AI,
            CHATGPT_DEFAULT_ADAPTER_ID,
        ),
        (
            WorkspaceAIRouteMode.LOCAL_PREFERRED,
            AITaskRouteDirective.LOCAL_AI,
            LOCAL_AI_ADAPTER_ID,
        ),
        (
            WorkspaceAIRouteMode.LOCAL_PREFERRED,
            AITaskRouteDirective.CLOUD_AI,
            LOCAL_AI_ADAPTER_ID,
        ),
    ],
)
def test_automatic_always_preserves_exact_d98_default(
    mode: WorkspaceAIRouteMode,
    directive: AITaskRouteDirective,
    expected: str,
) -> None:
    result = resolve(
        provider_preference="automatic",
        mode=mode,
        directive=directive,
    )

    assert result.status == "selected"
    assert result.adapter_id == expected
    assert result.selection_source == "workspace_default"
    assert result.effective_directive is AITaskRouteDirective.WORKSPACE_DEFAULT


def test_invalid_task_fails_closed() -> None:
    with pytest.raises(ValueError, match="invalid_task_kind"):
        TaskAwareAIRoutingResolver().resolve(
            task_kind="software_engineering",  # type: ignore[arg-type]
            provider_preference="unspecified",
            workspace_policy=workspace_policy(
                WorkspaceAIRouteMode.CLOUD_PREFERRED
            ),
            task_policy=task_policy(AITaskRouteDirective.LOCAL_AI),
        )


def test_invalid_task_policy_fails_closed() -> None:
    with pytest.raises(ValueError, match="invalid_task_routing_policy"):
        TaskAwareAIRoutingResolver().resolve(
            task_kind=AITaskKind.SOFTWARE_ENGINEERING,
            provider_preference="unspecified",
            workspace_policy=workspace_policy(
                WorkspaceAIRouteMode.CLOUD_PREFERRED
            ),
            task_policy=object(),  # type: ignore[arg-type]
        )


def test_invalid_provider_preference_fails_closed() -> None:
    with pytest.raises(ValueError, match="invalid_provider_preference"):
        resolve(provider_preference="task_aware")


def test_context_and_ai_output_are_not_resolver_inputs() -> None:
    parameters = inspect.signature(TaskAwareAIRoutingResolver.resolve).parameters
    assert tuple(parameters) == (
        "self",
        "task_kind",
        "provider_preference",
        "workspace_policy",
        "task_policy",
    )

    resolver = TaskAwareAIRoutingResolver()
    common = {
        "task_kind": AITaskKind.GENERAL_CHAT,
        "provider_preference": "unspecified",
        "workspace_policy": workspace_policy(
            WorkspaceAIRouteMode.CLOUD_PREFERRED
        ),
        "task_policy": task_policy(AITaskRouteDirective.WORKSPACE_DEFAULT),
    }

    with pytest.raises(TypeError):
        resolver.resolve(**common, context="route local")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        resolver.resolve(**common, ai_output="route cloud")  # type: ignore[call-arg]


def test_resolver_import_boundary_has_no_runtime_provider_network_or_persistence() -> None:
    source_file = Path(inspect.getsourcefile(TaskAwareAIRoutingResolver) or "")
    tree = ast.parse(source_file.read_text(encoding="utf-8"))

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_fragments = (
        "adapter_registry",
        "ai_runtime",
        "local_ai",
        "openai",
        "ollama",
        "http",
        "requests",
        "socket",
        "sqlalchemy",
        "repository",
        "db.",
        "execution_planner",
        "execution_guard",
        "context",
    )
    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in forbidden_fragments
    )


def test_resolver_source_has_no_fallback_retry_model_backend_or_base_url_authority() -> None:
    source = inspect.getsource(TaskAwareAIRoutingResolver).lower()

    forbidden = (
        "fallback",
        "retry",
        "model_id",
        "backend_id",
        "base_url",
        "runtime_url",
        "credential",
        "api_key",
        "execution_plan",
        "authorize",
    )
    assert not any(item in source for item in forbidden)
