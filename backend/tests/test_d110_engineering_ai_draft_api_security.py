from pathlib import Path
import inspect

from app.api import dependencies
from app.api.v1 import engineering
from app.schemas.engineering_ai_draft import EngineeringAIDraftCreateRequest
from app.services.engineering_ai_draft import EngineeringAIDraftWorkflowService


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_d110_api_route_is_exact_and_local_marker_guarded() -> None:
    routes = [
        route
        for route in engineering.router.routes
        if route.path == "/engineering/ai-drafts"
    ]
    assert len(routes) == 1
    assert "POST" in routes[0].methods

    source = inspect.getsource(engineering.create_engineering_ai_draft)
    assert "Depends(require_local_engineering_owner_request_marker)" in source
    assert "Depends(get_engineering_ai_draft_workflow_service)" in source


def test_d110_api_request_surface_has_no_browser_authority() -> None:
    assert set(EngineeringAIDraftCreateRequest.model_fields) == {
        "conversation_id",
        "relative_path",
        "instruction",
    }


def test_d110_conversation_lookup_precedes_repository_or_ai_draft() -> None:
    source = inspect.getsource(EngineeringAIDraftWorkflowService.draft)
    lookup = source.index("self._conversations.get(")
    draft = source.index("self._draft_service.draft(")
    assert lookup < draft


def test_d110_dependency_is_server_workspace_and_server_root_bound() -> None:
    source = inspect.getsource(
        dependencies.get_engineering_ai_draft_workflow_service
    )
    assert "workspace_scope: WorkspaceScope = Depends(get_workspace_scope)" in source
    assert "ConversationRepository(" in source
    assert "database_session" in source
    assert "workspace_scope" in source
    assert "get_engineering_repository_root()" in source
    assert "EngineeringRepositoryReader(repository_root)" in source
    assert "EngineeringAIDraftService(" in source
    assert "execution_planner=execution_planner" in source
    assert "execution_guard=execution_guard" in source
    assert "ai_runtime=ai_runtime" in source


def test_d110_engineering_api_has_no_direct_write_or_generic_execution_authority() -> None:
    source = inspect.getsource(engineering)
    forbidden = (
        "FilesystemCreateTextToolAdapter",
        "FilesystemReplaceTextToolAdapter",
        "ToolRuntime",
        "ModuleRuntime",
        "ExecutionApprovalService",
        "CommandExecutionCoordinator",
        "subprocess",
        "os.system",
        "git push",
        "git commit",
        "requests.",
        "httpx.",
        "CredentialAccessBroker",
    )
    for token in forbidden:
        assert token not in source


def test_d110_chat_has_no_ai_draft_authority_bridge() -> None:
    source = _read("app/api/v1/chat.py")
    assert "EngineeringAIDraftWorkflowService" not in source
    assert "create_engineering_ai_draft" not in source
    assert "/engineering/ai-drafts" not in source


def test_d110_engineering_route_set_remains_bounded() -> None:
    assert {route.path for route in engineering.router.routes} == {
        "/engineering/read",
        "/engineering/proposals",
        "/engineering/ai-drafts",
        "/engineering/conversations/{conversation_id}/active",
        "/engineering/approvals/{approval_id}/approve",
        "/engineering/approvals/{approval_id}/deny",
        "/engineering/approvals/{approval_id}/apply",
    }
