"""D100 Batch 01 executable trust-boundary and attack-surface inventory."""

from __future__ import annotations

import inspect
from pathlib import Path

from fastapi import FastAPI
from fastapi.params import Depends as DependsParam

from app.api import dependencies
from app.api.router import api_router
from app.api.workspace_scope import get_workspace_scope
from app.db.verification import TARGET_REVISION
from app.services.command_orchestrator import CommandOrchestrator


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


D100_API_SURFACE_PREFIXES = {
    "/api/v1/automations",
    "/api/v1/chat",
    "/api/v1/conversations",
    "/api/v1/diagnostics",
    "/api/v1/health",
    "/api/v1/execution-approvals",
    "/api/v1/calendar-write-approvals",
    "/api/v1/gmail-send-approvals",
    "/api/v1/gmail-send-executions",
    "/api/v1/calendar-write-chat",
    "/api/v1/calendar-write-executions",
    "/api/v1/knowledge",
    "/api/v1/knowledge/answer",
    "/api/v1/memories",
    "/api/v1/oauth",
    "/api/v1/oauth/google-gmail",
    "/api/v1/oauth/google-gmail-send",
    "/api/v1/projects",
    "/api/v1/project-update-proposals",
}

D100_AUTHORITY_COMPONENTS = {
    "WorkspaceScope",
    "WorkspaceAIPolicyResolver",
    "AIRouter",
    "ExecutionPlanner",
    "ExecutionGuard",
    "AIRuntime",
    "ToolRuntime",
    "ModuleRuntime",
    "CredentialAccessBroker",
    "ContextResolver",
    "ContextSnapshotService",
    "ContextSnapshotRepository",
    "ConversationService",
}

D100_ATTACK_CLASSES = {
    "workspace_spoofing",
    "cross_workspace_resource_probe",
    "legacy_null_workspace",
    "stale_workspace_response",
    "client_state_tamper",
    "context_prompt_injection",
    "context_routing_injection",
    "context_approval_injection",
    "context_credential_injection",
    "company_cloud_escalation",
    "provider_reroute",
    "approval_replay",
    "authorization_replay",
    "adapter_replay",
    "stale_proposal",
    "association_substitution",
    "special_lane_scope_bypass",
    "snapshot_drift_tamper",
    "metadata_leakage",
    "secret_error_leakage",
}


def _backend(relative: str) -> str:
    return (BACKEND / relative).read_text(encoding="utf-8-sig").replace(
        "\r\n",
        "\n",
    )


def _frontend(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig").replace(
        "\r\n",
        "\n",
    )


def test_d100_inventory_covers_registered_api_domains() -> None:
    app = FastAPI()
    app.include_router(api_router)
    paths = set(app.openapi()["paths"])

    for prefix in D100_API_SURFACE_PREFIXES:
        assert any(
            path == prefix or path.startswith(prefix + "/")
            for path in paths
        ), prefix


def test_d100_attack_class_inventory_is_explicit_and_nonempty() -> None:
    assert len(D100_ATTACK_CLASSES) >= 20
    assert {
        "workspace_spoofing",
        "context_routing_injection",
        "company_cloud_escalation",
        "approval_replay",
        "special_lane_scope_bypass",
        "secret_error_leakage",
    } <= D100_ATTACK_CLASSES


def test_d100_workspace_header_remains_exact_request_metadata() -> None:
    source = inspect.getsource(get_workspace_scope)

    assert "if x_oai_workspace is None:" in source
    assert "parse_workspace_id(x_oai_workspace)" in source

    for forbidden in (
        ".strip(",
        ".lower(",
        ".upper(",
        'or "personal"',
        'or "company"',
    ):
        assert forbidden not in source


def test_d100_workspace_scoped_service_roots_depend_on_workspace_scope() -> None:
    service_factories = (
        dependencies.get_conversation_service,
        dependencies.get_project_service,
        dependencies.get_memory_service,
        dependencies.get_knowledge_service,
        dependencies.get_project_update_proposal_service,
        dependencies.get_execution_approval_service,
    )

    for factory in service_factories:
        source = inspect.getsource(factory)
        assert "Depends(get_workspace_scope)" in source


def test_d100_workspace_scope_flows_into_authoritative_repositories() -> None:
    dependency_source = _backend("app/api/dependencies.py")

    for marker in (
        "ConversationRepository(\n            database_session,\n            workspace_scope,",
        "ProjectRepository(\n            database_session,\n            workspace_scope,",
        "MemoryRepository(\n            database_session,\n            workspace_scope,",
        "get_knowledge_repository(\n            database_session,\n            workspace_scope,",
    ):
        assert marker in dependency_source


def test_d100_ai_route_composition_binds_exact_workspace_policy() -> None:
    policy_source = inspect.getsource(dependencies.get_workspace_ai_policy)
    router_source = inspect.getsource(dependencies.get_ai_router)

    assert "Depends(get_workspace_scope)" in policy_source
    assert "resolver.resolve(workspace_scope)" in policy_source

    signature = inspect.signature(dependencies.get_ai_router)
    workspace_dependency = signature.parameters["workspace_policy"].default
    assert isinstance(workspace_dependency, DependsParam)
    assert (
        workspace_dependency.dependency
        is dependencies.get_workspace_ai_policy
    )
    assert "workspace_policy=workspace_policy" in router_source


def test_d100_normal_chat_authority_order_is_frozen() -> None:
    source = inspect.getsource(CommandOrchestrator.process_chat)

    order = (
        source.index("self._planner.plan"),
        source.index("self._guard.authorize"),
        source.index("self._ai_runtime.bind"),
        source.index("send_context_message"),
    )
    assert order == tuple(sorted(order))


def test_d100_execution_approval_is_workspace_bound_not_execution_grant() -> None:
    source = inspect.getsource(dependencies.get_execution_approval_service)

    assert "workspace_scope: WorkspaceScope = Depends(get_workspace_scope)" in source
    assert "workspace_scope=workspace_scope" in source
    assert "ExecutionApprovalService(" in source


def test_d100_private_side_effect_lanes_remain_private() -> None:
    source = _backend("app/api/dependencies.py")

    for marker in (
        "get_gmail_send_private_registry",
        "get_gmail_send_private_permission_policy",
        "get_calendar_create_private_registry",
        "get_calendar_create_private_permission_policy",
        "get_calendar_update_delete_private_registry",
        "get_calendar_update_delete_private_permission_policy",
    ):
        assert marker in source


def test_d100_frontend_workspace_header_is_not_global_authority() -> None:
    source = _frontend("lib/api-client.ts")
    scoped_marker = "export function workspaceApiRequest"
    index = source.index(scoped_marker)

    generic = source[:index]
    scoped = source[index:]

    assert "X-OAI-Workspace" not in generic
    assert 'headers.set("X-OAI-Workspace", workspaceId)' in scoped
    assert "assertResponseWorkspace" in scoped


def test_d100_context_usage_surface_has_no_execution_or_routing_bridge() -> None:
    backend = _backend("app/services/context_usage.py")
    frontend = _frontend("components/chat/context-usage.tsx")
    combined = backend + "\n" + frontend

    for forbidden in (
        "ExecutionGuard",
        "ExecutionPlanner",
        "AIRouter",
        "AIRuntime",
        "CredentialAccessBroker",
        "ToolRuntime",
        "ModuleRuntime",
        "adapter_id",
        "cloud_egress",
        "<button",
        "onClick",
    ):
        assert forbidden not in combined


def test_d100_database_revision_is_frozen_at_d97_snapshot_schema() -> None:
    assert TARGET_REVISION == "0013_context_snapshot_persistence"


def test_d100_authority_component_inventory_matches_composition_root() -> None:
    dependencies_source = _backend("app/api/dependencies.py")

    for component in D100_AUTHORITY_COMPONENTS:
        assert component in dependencies_source
