"""D120 second built-in Skill metadata security acceptance."""

from __future__ import annotations

import inspect
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
from app.contracts.engineering_investigation import EngineeringInvestigationRequest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.builtin_skills import (
    BUILTIN_SKILL_DESCRIPTORS,
    ENGINEERING_AI_DRAFT_SKILL,
    ENGINEERING_AI_DRAFT_SKILL_ID,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    build_builtin_skill_catalog,
)
from app.services.engineering_ai_draft import EngineeringAIDraftWorkflowService
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationWorkflowService,
)
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_REQUEST_INVALID,
    SkillInvocationBridge,
    SkillInvocationError,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_HEADERS = {"X-OAI-Local-Request": "1"}


def _request() -> EngineeringInvestigationRequest:
    return EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="This request must never reach D113 for the D110 Skill.",
        focus_paths=(),
    )


def _real_bridge_without_runnable_workflow() -> SkillInvocationBridge:
    ai_draft_workflow = object.__new__(EngineeringAIDraftWorkflowService)
    workflow = object.__new__(EngineeringInvestigationWorkflowService)
    return SkillInvocationBridge(
        catalog=build_builtin_skill_catalog(),
        engineering_ai_draft_workflow=ai_draft_workflow,
        engineering_investigation_workflow=workflow,
    )


def test_d120_security_catalog_visibility_does_not_define_request_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_calls: list[object] = []
    investigation_calls: list[object] = []

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        lambda self, request: draft_calls.append(request),
    )
    monkeypatch.setattr(
        EngineeringInvestigationWorkflowService,
        "investigate",
        lambda self, request: investigation_calls.append(request),
    )

    bridge = _real_bridge_without_runnable_workflow()

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(
            skill_id=ENGINEERING_AI_DRAFT_SKILL_ID,
            request=_request(),
        )

    assert exc.value.code == SKILL_INVOCATION_REQUEST_INVALID
    assert draft_calls == []
    assert investigation_calls == []



def test_d120_security_new_skill_metadata_remains_exact_after_d121_support() -> None:
    catalog = build_builtin_skill_catalog()

    assert catalog.resolve(ENGINEERING_AI_DRAFT_SKILL_ID) is ENGINEERING_AI_DRAFT_SKILL
    assert tuple(item.skill_id for item in catalog.list()) == (
        ENGINEERING_AI_DRAFT_SKILL_ID,
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    )

    bridge_source = inspect.getsource(SkillInvocationBridge.invoke)

    assert "ENGINEERING_AI_DRAFT_SKILL_ID" in bridge_source
    assert "ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID" in bridge_source
    assert "handler_registry" not in bridge_source



class _ProjectionWorkflow:
    workspace_scope = WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)


def _api_client_with_real_bridge() -> TestClient:
    bridge = _real_bridge_without_runnable_workflow()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_skill_invocation_bridge] = lambda: bridge
    app.dependency_overrides[
        get_engineering_investigation_workflow_service
    ] = lambda: _ProjectionWorkflow()

    return TestClient(app)


def test_d120_security_d122_static_d110_path_rejects_investigation_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_calls: list[object] = []

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        lambda self, request: draft_calls.append(request),
    )

    conversation_id = uuid4()
    client = _api_client_with_real_bridge()

    response = client.post(
        "/engineering/skills/engineering.ai_draft/invoke",
        headers=_LOCAL_HEADERS,
        json={
            "conversation_id": str(conversation_id),
            "instruction": "Investigation shape must not become D110 input.",
            "focus_paths": [],
        },
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert draft_calls == []



def test_d120_security_bridge_d110_support_adds_no_generic_or_mutation_authority() -> None:
    bridge_path = (
        _REPO_ROOT
        / "backend"
        / "app"
        / "services"
        / "skill_invocation_bridge.py"
    )
    source = bridge_path.read_text(encoding="utf-8").lower()

    forbidden = (
        "create_proposal",
        "engineering_change_proposal",
        "engineering_apply",
        "provider_id",
        "model_id",
        "credential",
        "resolve_tool",
        "resolve_module",
        "handler_registry",
        "register_handler",
        'target_kind="skill"',
        "'skill.execute'",
    )

    for token in forbidden:
        assert token not in source



def test_d120_security_frontend_does_not_gain_catalog_driven_invocation() -> None:
    panel_path = (
        _REPO_ROOT
        / "frontend"
        / "components"
        / "chat"
        / "engineering-owner-panel.tsx"
    )
    source = panel_path.read_text(encoding="utf-8")

    assert (
        '"/engineering/skills/engineering.investigation_change_plan/invoke"'
        in source
    )
    assert (
        '"/engineering/skills/engineering.ai_draft/invoke"'
        in source
    )
    assert source.count(
        "/engineering/skills/engineering.ai_draft/invoke"
    ) == 1
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
    assert "skillCatalog.skills.map((skill)" in source
    assert "Metadata only" in source


def test_d120_security_builtin_metadata_has_no_runtime_authority_fields() -> None:
    forbidden_names = {
        "handler",
        "callable",
        "service",
        "provider",
        "adapter",
        "model",
        "credential",
        "tool",
        "module",
        "connector",
        "route",
        "approval",
        "proposal",
        "apply",
        "execution_target",
    }

    descriptor_dict = {
        "skill_id": ENGINEERING_AI_DRAFT_SKILL.skill_id,
        "version": ENGINEERING_AI_DRAFT_SKILL.version,
        "display_name": ENGINEERING_AI_DRAFT_SKILL.display_name,
        "description": ENGINEERING_AI_DRAFT_SKILL.description,
        "task_kind": ENGINEERING_AI_DRAFT_SKILL.task_kind.value,
        "required_ai_capability_ids": (
            ENGINEERING_AI_DRAFT_SKILL.required_ai_capability_ids
        ),
        "input_kind": ENGINEERING_AI_DRAFT_SKILL.input_kind,
        "context_kind": ENGINEERING_AI_DRAFT_SKILL.context_kind,
        "output_kind": ENGINEERING_AI_DRAFT_SKILL.output_kind,
    }

    lowered = {name.lower() for name in descriptor_dict}
    assert forbidden_names.isdisjoint(lowered)


def test_d120_security_exact_two_builtin_descriptors_remain_server_owned() -> None:
    assert len(BUILTIN_SKILL_DESCRIPTORS) == 2
    assert tuple(item.skill_id for item in BUILTIN_SKILL_DESCRIPTORS) == (
        "engineering.ai_draft",
        "engineering.investigation_change_plan",
    )
