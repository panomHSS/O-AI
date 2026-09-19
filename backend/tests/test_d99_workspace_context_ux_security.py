from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.contracts.context_usage import ContextUsage
from app.db.verification import TARGET_REVISION
from app.schemas.chat import ChatResponse
from app.schemas.context_usage import ContextUsageResponse


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def _read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


def test_workspace_id_surface_is_exact_and_alias_free() -> None:
    source = _read("types/workspace.ts")

    assert 'WORKSPACE_IDS = ["personal", "company"] as const' in source
    assert (
        'return value === "personal" || value === "company" ? value : null;'
        in source
    )
    for alias in (
        '"default"',
        '"work"',
        '"business"',
        '"private"',
        '"personal_workspace"',
    ):
        assert alias not in source


def test_missing_or_invalid_workspace_has_no_implicit_default() -> None:
    provider = _read("components/workspace/workspace-provider.tsx")
    workspace = _read("lib/workspace.ts")

    assert "useState<WorkspaceId | null>(null)" in provider
    assert "loadStoredWorkspace(window.localStorage)" in provider
    assert 'storage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY)' in workspace
    assert '?? "personal"' not in provider
    assert '|| "personal"' not in provider
    assert '?? "company"' not in provider
    assert '|| "company"' not in provider


def test_legacy_unscoped_conversation_is_discarded_not_reclassified() -> None:
    provider = _read("components/workspace/workspace-provider.tsx")
    workspace = _read("lib/workspace.ts")

    assert (
        'LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY = "oai.activeConversationId"'
        in workspace
    )
    assert (
        "storage.removeItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY)"
        in workspace
    )
    assert "discardLegacyUnscopedConversation(window.localStorage)" in provider
    assert "oai.activeConversationId.${workspaceId}" in workspace
    assert (
        "storage.setItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY"
        not in workspace
    )


def test_workspace_header_is_explicit_and_not_global() -> None:
    source = _read("lib/api-client.ts")
    marker = "export function workspaceApiRequest"
    index = source.index(marker)

    generic_prefix = source[:index]
    scoped = source[index:]

    assert "X-OAI-Workspace" not in generic_prefix
    assert 'headers.set("X-OAI-Workspace", workspaceId)' in scoped
    assert "parseWorkspaceId(workspaceId)" in scoped


def test_workspace_owned_frontend_calls_require_workspace_argument() -> None:
    source = _read("lib/api-client.ts")

    expected = (
        "sendChatMessage",
        "approveExecutionApproval",
        "denyExecutionApproval",
        "approveCalendarWriteChat",
        "denyCalendarWriteChat",
        "getConversation",
        "scanKnowledge",
        "listKnowledgeDocuments",
        "searchKnowledge",
        "createProject",
        "listProjects",
        "getProject",
        "updateProjectDetails",
        "updateProjectProgress",
        "changeProjectNextAction",
        "changeProjectStatus",
        "getProjectHistory",
    )
    for name in expected:
        start = source.index(f"export function {name}(")
        signature = source[start : source.index("):", start) + 2]
        assert "workspaceId: WorkspaceId" in signature


def test_workspace_switch_remounts_scoped_ui_state() -> None:
    layout = _read("app/layout.tsx")
    provider = _read("components/workspace/workspace-provider.tsx")

    assert "<WorkspaceResetBoundary>{children}</WorkspaceResetBoundary>" in layout
    assert "const workspaceKey = isReady" in provider
    assert "workspaceId ??" in provider
    assert "return <div key={workspaceKey}>{children}</div>;" in provider


def test_response_workspace_mismatch_fails_closed_before_return() -> None:
    source = _read("lib/api-client.ts")

    assert "function assertResponseWorkspace" in source
    assert "response.workspace_id !== workspaceId" in source
    assert (
        "The workspace changed before this request completed."
        in source
    )
    assert ".then((response) => assertResponseWorkspace(workspaceId, response))" in source


def test_context_indicator_is_display_only_and_has_no_action_surface() -> None:
    source = _read("components/chat/context-usage.tsx")

    assert "Context · not recorded" in source
    assert "Context · none" in source
    assert "Conversation {usage.conversation_items}" in source
    assert "Project {usage.project_items}" in source
    assert "Memory {usage.memory_items}" in source
    assert "Knowledge {usage.knowledge_items}" in source

    for forbidden in (
        "api-client",
        "fetch(",
        "onClick",
        "<button",
        "approve",
        "execute",
        "route",
        "provider",
        "cloud",
        "local_ai",
    ):
        assert forbidden not in source.lower()


def test_context_usage_response_has_only_fixed_transparency_fields() -> None:
    assert set(ContextUsageResponse.model_fields) == {
        "captured_at",
        "total_items",
        "conversation_items",
        "project_items",
        "memory_items",
        "knowledge_items",
    }

    assert set(ContextUsage.__dataclass_fields__) == {
        "captured_at",
        "total_items",
        "conversation_items",
        "project_items",
        "memory_items",
        "knowledge_items",
    }


def test_context_usage_code_has_no_routing_or_execution_authority() -> None:
    service = (
        ROOT / "backend" / "app" / "services" / "context_usage.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "AIRouter",
        "ExecutionGuard",
        "ExecutionPlanner",
        "AIRuntime",
        "adapter_id",
        "cloud_egress",
        "owner_approval",
        "credential",
    ):
        assert forbidden not in service


def test_special_chat_response_defaults_context_usage_to_null() -> None:
    response = ChatResponse(
        workspace_id="personal",
        reply="special deterministic lane",
        conversation_id=UUID("11111111-1111-1111-1111-111111111111"),
    )

    assert response.context_usage is None


def test_only_normal_chat_api_branch_projects_context_usage() -> None:
    source = (
        ROOT / "backend" / "app" / "api" / "v1" / "chat.py"
    ).read_text(encoding="utf-8")

    assert source.count("context_usage=(") == 1
    assert "ContextUsageResponse.from_usage(result.context_usage)" in source


def test_d99_does_not_add_database_revision() -> None:
    assert TARGET_REVISION == "0013_context_snapshot_persistence"
