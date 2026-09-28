"""D121 Engineering AI Draft Skill bridge security acceptance."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_engineering_investigation_workflow_service,
    get_skill_invocation_bridge,
)
from app.api.v1.engineering import router
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.engineering_investigation import EngineeringInvestigationRequest
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.builtin_skills import (
    ENGINEERING_AI_DRAFT_SKILL,
    ENGINEERING_AI_DRAFT_SKILL_ID,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    build_builtin_skill_catalog,
)
from app.services.engineering_ai_draft import EngineeringAIDraftWorkflowService
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationWorkflowService,
)
from app.services.skill_catalog import SkillCatalog
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_REQUEST_INVALID,
    SKILL_INVOCATION_SKILL_UNSUPPORTED,
    SkillInvocationBridge,
    SkillInvocationError,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_BRIDGE = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "services"
    / "skill_invocation_bridge.py"
)
_DEPENDENCIES = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "api"
    / "dependencies.py"
)
_ENGINEERING_API = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "api"
    / "v1"
    / "engineering.py"
)
_PANEL = (
    _REPO_ROOT
    / "frontend"
    / "components"
    / "chat"
    / "engineering-owner-panel.tsx"
)

_LOCAL_HEADERS = {"X-OAI-Local-Request": "1"}


def _bridge(*, catalog: SkillCatalog | None = None) -> SkillInvocationBridge:
    return SkillInvocationBridge(
        catalog=catalog or build_builtin_skill_catalog(),
        engineering_ai_draft_workflow=object.__new__(
            EngineeringAIDraftWorkflowService
        ),
        engineering_investigation_workflow=object.__new__(
            EngineeringInvestigationWorkflowService
        ),
    )


def _tree() -> ast.Module:
    return ast.parse(
        _BRIDGE.read_text(encoding="utf-8"),
        filename=str(_BRIDGE),
    )


def test_d121_bridge_imports_no_direct_execution_or_mutation_authority() -> None:
    forbidden_modules = {
        "app.services.ai_runtime",
        "app.services.execution_guard",
        "app.services.execution_planner",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.credential_access_broker",
        "app.services.engineering_change_proposal",
        "app.services.engineering_apply_execution",
    }
    forbidden_namespaces = (
        "app.adapters",
        "app.connectors",
        "app.providers",
        "app.plugins",
    )

    imports: list[str] = []
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    for imported in imports:
        assert imported not in forbidden_modules
        assert not imported.startswith(forbidden_namespaces)

    assert "app.services.engineering_ai_draft" in imports
    assert "app.services.engineering_investigation_workflow" in imports


def test_d121_bridge_has_no_dynamic_handler_registry_or_execution_surface() -> None:
    source = _BRIDGE.read_text(encoding="utf-8").lower()

    forbidden_fragments = (
        "getattr(",
        "import_module(",
        "entry_points(",
        "handler_registry",
        "register_handler",
        "resolve_handler",
        "skill.execute",
        'target_kind="skill"',
        "resolve_tool",
        "resolve_module",
        "create_proposal",
        "engineering_apply",
        "credential",
        "provider_id",
        "model_id",
    )

    for fragment in forbidden_fragments:
        assert fragment not in source

    for forbidden_name in (
        "register",
        "unregister",
        "install",
        "load",
        "resolve_handler",
        "add_handler",
        "set_handler",
        "execute",
        "run",
    ):
        assert not hasattr(SkillInvocationBridge, forbidden_name)

    assert hasattr(SkillInvocationBridge, "invoke")


def test_d121_bridge_source_enumerates_exact_two_supported_builtin_ids() -> None:
    source = _BRIDGE.read_text(encoding="utf-8")

    assert "ENGINEERING_AI_DRAFT_SKILL_ID" in source
    assert "ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID" in source
    assert ENGINEERING_AI_DRAFT_SKILL_ID == "engineering.ai_draft"
    assert (
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID
        == "engineering.investigation_change_plan"
    )

    catalog = build_builtin_skill_catalog()
    assert tuple(item.skill_id for item in catalog.list()) == (
        ENGINEERING_AI_DRAFT_SKILL_ID,
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    )


def test_d121_catalog_known_third_skill_still_fails_unsupported() -> None:
    third = SkillDescriptor(
        skill_id="other.skill",
        version="1",
        display_name="Other Skill",
        description="Trusted server-side security fixture.",
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        input_kind="other_request",
        context_kind="none",
        output_kind="other_result",
    )
    catalog = SkillCatalog(
        (
            ENGINEERING_AI_DRAFT_SKILL,
            ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
            third,
        )
    )

    request = EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="Known third Skill must stay unsupported.",
        focus_paths=(),
    )

    with pytest.raises(SkillInvocationError) as exc:
        _bridge(catalog=catalog).invoke(
            skill_id="other.skill",
            request=request,
        )

    assert exc.value.code == SKILL_INVOCATION_SKILL_UNSUPPORTED


class _ProjectionWorkflow:
    workspace_scope = WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)


def _api_client_with_real_bridge() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_skill_invocation_bridge] = lambda: _bridge()
    app.dependency_overrides[
        get_engineering_investigation_workflow_service
    ] = lambda: _ProjectionWorkflow()

    return TestClient(app)


def test_d121_d116_d110_skill_path_fails_request_invalid_before_d110_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def _unexpected_draft(self, request):
        calls.append(request)
        raise AssertionError("D116 investigation request reached D110 draft")

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        _unexpected_draft,
    )

    response = _api_client_with_real_bridge().post(
        "/engineering/skills/engineering.ai_draft/invoke",
        headers=_LOCAL_HEADERS,
        json={
            "conversation_id": str(uuid4()),
            "instruction": "Keep D116 investigation-specific.",
            "focus_paths": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == SKILL_INVOCATION_REQUEST_INVALID
    assert calls == []


def test_d121_dependency_wiring_reuses_existing_workflow_providers_only() -> None:
    source = _DEPENDENCIES.read_text(encoding="utf-8")
    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    node = functions["get_skill_invocation_bridge"]
    lines = source.splitlines()
    block = "\n".join(lines[node.lineno - 1 : node.end_lineno])

    assert "build_builtin_skill_catalog()" in block
    assert "Depends(get_engineering_ai_draft_workflow_service)" in block
    assert "Depends(get_engineering_investigation_workflow_service)" in block
    assert "engineering_ai_draft_workflow=ai_draft_workflow" in block
    assert "engineering_investigation_workflow=workflow" in block

    assert "EngineeringAIDraftService(" not in block
    assert "EngineeringInvestigationService(" not in block
    assert "AIRuntime(" not in block
    assert "ExecutionGuard(" not in block
    assert "ExecutionPlanner(" not in block


def test_d121_d116_api_remains_investigation_specific() -> None:
    source = _ENGINEERING_API.read_text(encoding="utf-8")

    assert '"/skills/{skill_id}/invoke"' in source
    assert "EngineeringInvestigationCreateRequest" in source
    assert "EngineeringInvestigationResponse" in source
    assert "EngineeringAIDraftCreateRequest" in source
    assert '"/ai-drafts"' in source

    route_start = source.index('"/skills/{skill_id}/invoke"')
    route_window = source[route_start : route_start + 3500]

    assert "EngineeringInvestigationCreateRequest" in route_window
    assert "EngineeringInvestigationResponse" in route_window
    assert "EngineeringAIDraftCreateRequest" not in route_window
    assert "EngineeringAIDraftResponse" not in route_window


def test_d121_frontend_remains_fixed_investigation_control_and_metadata_catalog() -> None:
    source = _PANEL.read_text(encoding="utf-8")

    assert (
        '"/engineering/skills/engineering.investigation_change_plan/invoke"'
        in source
    )
    assert "engineering.ai_draft/invoke" not in source
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
    assert "skillCatalog.skills.map((skill)" in source
    assert "Metadata only" in source
