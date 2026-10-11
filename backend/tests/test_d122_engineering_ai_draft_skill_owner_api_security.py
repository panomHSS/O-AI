"""D122 Engineering AI Draft Skill owner API security acceptance."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from app.api.v1 import engineering
from app.schemas.engineering_ai_draft import EngineeringAIDraftCreateRequest


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
_ENGINEERING_FILE = _BACKEND_ROOT / "app" / "api" / "v1" / "engineering.py"
_CHAT_FILE = _BACKEND_ROOT / "app" / "api" / "v1" / "chat.py"
_PANEL_FILE = (
    _REPO_ROOT
    / "frontend"
    / "components"
    / "chat"
    / "engineering-owner-panel.tsx"
)

_STATIC_SKILL_PATH = "/skills/engineering.ai_draft/invoke"
_DYNAMIC_SKILL_PATH = "/skills/{skill_id}/invoke"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _route_for_path(path: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    matches: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in _tree(_ENGINEERING_FILE).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "router"
                and decorator.func.attr == "post"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and decorator.args[0].value == path
            ):
                matches.append(node)
    assert len(matches) == 1, f"Expected exactly one POST route for {path}"
    return matches[0]


def _decorator_text(route: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    decorators = [
        decorator
        for decorator in route.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "router"
        and decorator.func.attr == "post"
    ]
    assert len(decorators) == 1
    return ast.unparse(decorators[0])


def _call_name(call: ast.Call) -> str:
    node = call.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def test_d122_static_skill_route_is_exact_post_and_precedes_dynamic_route() -> None:
    static_route = _route_for_path(_STATIC_SKILL_PATH)
    dynamic_route = _route_for_path(_DYNAMIC_SKILL_PATH)

    assert "EngineeringAIDraftResponse" in _decorator_text(static_route)
    assert "EngineeringInvestigationResponse" in _decorator_text(dynamic_route)
    assert static_route.lineno < dynamic_route.lineno

    route_paths = [route.path for route in engineering.router.routes]
    static_full = "/engineering/skills/engineering.ai_draft/invoke"
    dynamic_full = "/engineering/skills/{skill_id}/invoke"
    assert route_paths.count(static_full) == 1
    assert route_paths.count(dynamic_full) == 1
    assert route_paths.index(static_full) < route_paths.index(dynamic_full)


def test_d122_static_route_request_contract_has_no_browser_authority() -> None:
    assert set(EngineeringAIDraftCreateRequest.model_fields) == {
        "conversation_id",
        "relative_path",
        "instruction",
    }

    route = _route_for_path(_STATIC_SKILL_PATH)
    text = ast.unparse(route)

    assert "EngineeringAIDraftCreateRequest" in text
    assert "EngineeringAIDraftRequest" in text
    assert "payload.conversation_id" in text
    assert "payload.relative_path" in text
    assert "payload.instruction" in text

    lowered = text.lower()
    for fragment in (
        "workspace_id:",
        "provider_id",
        "adapter_id",
        "model_id",
        "credential",
        "connector_id",
        "tool_id",
        "module_id",
        "approval_id",
        "apply_instruction",
    ):
        assert fragment not in lowered


def test_d122_static_route_is_fixed_to_exact_trusted_skill_identity() -> None:
    route = _route_for_path(_STATIC_SKILL_PATH)
    text = ast.unparse(route)
    calls = [
        _call_name(node)
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
    ]

    assert calls.count("bridge.invoke") == 1
    assert "skill_id=ENGINEERING_AI_DRAFT_SKILL_ID" in text
    assert "request=request" in text

    assert "Path(" not in text
    assert "payload.skill_id" not in text
    assert "skill_id=skill_id" not in text


def test_d122_static_route_uses_bridge_not_direct_d110_workflow() -> None:
    route = _route_for_path(_STATIC_SKILL_PATH)
    text = ast.unparse(route)
    calls = [
        _call_name(node)
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
    ]

    assert "SkillInvocationBridge" in text
    assert "Depends(get_skill_invocation_bridge)" in text
    assert calls.count("bridge.invoke") == 1

    assert "service.draft" not in calls
    assert "workflow.draft" not in calls
    assert "EngineeringAIDraftWorkflowService.draft" not in calls
    assert "get_engineering_ai_draft_workflow_service" not in text


def test_d122_static_route_requires_existing_local_owner_marker() -> None:
    route = _route_for_path(_STATIC_SKILL_PATH)
    text = ast.unparse(route)

    assert "require_local_engineering_owner_request_marker" in text
    assert "Depends(require_local_engineering_owner_request_marker)" in text


def test_d122_static_route_adds_no_d107_d108_or_generic_execution_authority() -> None:
    route = _route_for_path(_STATIC_SKILL_PATH)
    text = ast.unparse(route).lower()

    forbidden = (
        "engineering_change_proposal",
        "engineering_apply_execution",
        "create_proposal(",
        "approve(",
        "deny(",
        "apply(",
        "executionplanner",
        "executionguard",
        "airuntime",
        "toolruntime",
        "moduleruntime",
        "tool.execute",
        "module.execute",
        "credentialaccessbroker",
        "subprocess",
        "os.system",
        "git push",
        "git commit",
        "requests.",
        "httpx.",
        "handler_registry",
        "resolve_handler",
        "import_module",
        "entry_points",
        "getattr(",
    )
    for fragment in forbidden:
        assert fragment not in text


def test_d122_dynamic_d116_route_remains_investigation_specific() -> None:
    route = _route_for_path(_DYNAMIC_SKILL_PATH)
    text = ast.unparse(route)
    calls = [
        _call_name(node)
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
    ]

    assert "EngineeringInvestigationCreateRequest" in text
    assert "EngineeringInvestigationRequest" in text
    assert "EngineeringInvestigationResponse.from_result" in text
    assert "skill_id=skill_id" in text
    assert calls.count("bridge.invoke") == 1

    assert "EngineeringAIDraftCreateRequest" not in text
    assert "EngineeringAIDraftRequest" not in text
    assert "ENGINEERING_AI_DRAFT_SKILL_ID" not in text


def test_d122_engineering_route_surface_remains_exact_and_bounded() -> None:
    assert {route.path for route in engineering.router.routes} == {
        "/engineering/read",
        "/engineering/proposals",
        "/engineering/ai-drafts",
        "/engineering/investigations",
        "/engineering/conversations/{conversation_id}/active",
        "/engineering/approvals/{approval_id}/approve",
        "/engineering/approvals/{approval_id}/deny",
        "/engineering/approvals/{approval_id}/apply",
        "/engineering/skills",
        "/engineering/skills/engineering.ai_draft/invoke",
        "/engineering/skills/{skill_id}/invoke",
    }


def test_d122_engineering_module_imports_no_new_direct_mutation_authority() -> None:
    imports: list[str] = []
    for node in ast.walk(_tree(_ENGINEERING_FILE)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    forbidden_modules = {
        "app.services.engineering_change_proposal",
        "app.services.engineering_apply_execution",
        "app.services.execution_planner",
        "app.services.execution_guard",
        "app.services.ai_runtime",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.credential_access_broker",
        "subprocess",
    }
    for imported in imports:
        assert imported not in forbidden_modules


def test_d122_frontend_static_ai_draft_skill_route_remains_exact_when_exposed() -> None:
    panel = _PANEL_FILE.read_text(encoding="utf-8")
    static_path = "/engineering/skills/engineering.ai_draft/invoke"

    assert panel.count(static_path) == 1
    assert f'"{static_path}"' in panel
    assert "selectedSkillId" not in panel
    assert "activeSkillId" not in panel


def test_d122_chat_does_not_gain_ai_draft_skill_invocation_authority() -> None:
    chat = _CHAT_FILE.read_text(encoding="utf-8")

    assert "/skills/engineering.ai_draft/invoke" not in chat
    assert "ENGINEERING_AI_DRAFT_SKILL_ID" not in chat
    assert "get_skill_invocation_bridge" not in chat


def test_d122_static_route_has_no_retry_fallback_or_dynamic_dispatch() -> None:
    route = _route_for_path(_STATIC_SKILL_PATH)

    assert not any(
        isinstance(node, (ast.For, ast.AsyncFor, ast.While))
        for node in ast.walk(route)
    )

    text = ast.unparse(route).lower()
    for fragment in (
        "retry",
        "fallback",
        "handler_registry",
        "resolve_handler",
        "import_module",
        "entry_points",
        "getattr(",
    ):
        assert fragment not in text


def test_d122_existing_d110_direct_route_stays_distinct() -> None:
    source = inspect.getsource(engineering.create_engineering_ai_draft)

    assert "Depends(get_engineering_ai_draft_workflow_service)" in source
    assert "service.draft(request)" in source
    assert "bridge.invoke" not in source
    assert "ENGINEERING_AI_DRAFT_SKILL_ID" not in source
