"""D121 Engineering AI Draft Skill bridge primary acceptance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.contracts.engineering_ai_draft import (
    EngineeringAIDraftRequest,
    EngineeringAIDraftResult,
)
from app.contracts.engineering_investigation import EngineeringInvestigationRequest
from app.services.builtin_skills import (
    ENGINEERING_AI_DRAFT_SKILL,
    ENGINEERING_AI_DRAFT_SKILL_ID,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    build_builtin_skill_catalog,
)
from app.services.engineering_ai_draft import (
    EngineeringAIDraftError,
    EngineeringAIDraftWorkflowService,
)
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationWorkflowService,
)
from app.services.skill_catalog import SkillCatalog
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_DESCRIPTOR_MISMATCH,
    SKILL_INVOCATION_REQUEST_INVALID,
    SkillInvocationBridge,
    SkillInvocationError,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _draft_request() -> EngineeringAIDraftRequest:
    return EngineeringAIDraftRequest(
        conversation_id=uuid4(),
        relative_path="README.md",
        instruction="Tighten one bounded paragraph.",
    )


def _investigation_request() -> EngineeringInvestigationRequest:
    return EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="Inspect one bounded path.",
        focus_paths=(),
    )


def _draft_result(request: EngineeringAIDraftRequest) -> EngineeringAIDraftResult:
    return EngineeringAIDraftResult(
        conversation_id=request.conversation_id,
        relative_path=request.relative_path,
        draft_operation="create_text",
        source_state="absent",
        source_sha256=None,
        source_size_bytes=None,
        draft_content="candidate content\n",
        ai_adapter_id="local_ai",
    )


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


def test_d121_ai_draft_skill_delegates_once_to_existing_d110_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _draft_request()
    calls: list[EngineeringAIDraftRequest] = []

    def _draft(self, received):
        calls.append(received)
        return _draft_result(received)

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        _draft,
    )

    result = _bridge().invoke(
        skill_id=ENGINEERING_AI_DRAFT_SKILL_ID,
        request=request,
    )

    assert result == _draft_result(request)
    assert calls == [request]


@pytest.mark.parametrize(
    ("skill_id", "skill_request"),
    (
        (ENGINEERING_AI_DRAFT_SKILL_ID, _investigation_request()),
        (ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID, _draft_request()),
    ),
)
def test_d121_supported_skill_rejects_wrong_request_contract_before_delegate(
    monkeypatch: pytest.MonkeyPatch,
    skill_id: str,
    skill_request: object,
) -> None:
    draft_calls: list[object] = []
    investigation_calls: list[object] = []

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        lambda self, value: draft_calls.append(value),
    )
    monkeypatch.setattr(
        EngineeringInvestigationWorkflowService,
        "investigate",
        lambda self, value: investigation_calls.append(value),
    )

    with pytest.raises(SkillInvocationError) as exc:
        _bridge().invoke(skill_id=skill_id, request=skill_request)

    assert exc.value.code == SKILL_INVOCATION_REQUEST_INVALID
    assert draft_calls == []
    assert investigation_calls == []


def test_d121_ai_draft_descriptor_mismatch_fails_before_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _draft_request()
    calls: list[object] = []

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        lambda self, value: calls.append(value),
    )

    mismatched = replace(ENGINEERING_AI_DRAFT_SKILL, version="2")
    catalog = SkillCatalog(
        (
            mismatched,
            ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
        )
    )

    with pytest.raises(SkillInvocationError) as exc:
        _bridge(catalog=catalog).invoke(
            skill_id=ENGINEERING_AI_DRAFT_SKILL_ID,
            request=request,
        )

    assert exc.value.code == SKILL_INVOCATION_DESCRIPTOR_MISMATCH
    assert calls == []


def test_d121_bridge_requires_real_d110_workflow_type() -> None:
    with pytest.raises(TypeError):
        SkillInvocationBridge(
            catalog=build_builtin_skill_catalog(),
            engineering_ai_draft_workflow=object(),  # type: ignore[arg-type]
            engineering_investigation_workflow=object.__new__(
                EngineeringInvestigationWorkflowService
            ),
        )


def test_d121_d110_workflow_error_propagates_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _draft_request()
    calls: list[object] = []

    def _fail(self, received):
        calls.append(received)
        raise EngineeringAIDraftError("engineering_ai_draft_unavailable")

    monkeypatch.setattr(
        EngineeringAIDraftWorkflowService,
        "draft",
        _fail,
    )

    with pytest.raises(EngineeringAIDraftError) as exc:
        _bridge().invoke(
            skill_id=ENGINEERING_AI_DRAFT_SKILL_ID,
            request=request,
        )

    assert exc.value.code == "engineering_ai_draft_unavailable"
    assert calls == [request]


def test_d121_dependency_wiring_reuses_existing_owner_bound_workflows() -> None:
    source = (
        _REPO_ROOT / "backend" / "app" / "api" / "dependencies.py"
    ).read_text(encoding="utf-8")

    start = source.index("def get_skill_invocation_bridge(")
    end = source.find("\ndef ", start + 1)
    block = source[start:] if end == -1 else source[start:end]

    assert "build_builtin_skill_catalog()" in block
    assert "get_engineering_ai_draft_workflow_service" in block
    assert "get_engineering_investigation_workflow_service" in block
    assert "engineering_ai_draft_workflow=ai_draft_workflow" in block
    assert "engineering_investigation_workflow=workflow" in block


def test_d121_d116_and_frontend_production_surfaces_remain_unchanged() -> None:
    engineering_api = (
        _REPO_ROOT / "backend" / "app" / "api" / "v1" / "engineering.py"
    ).read_text(encoding="utf-8")
    panel = (
        _REPO_ROOT
        / "frontend"
        / "components"
        / "chat"
        / "engineering-owner-panel.tsx"
    ).read_text(encoding="utf-8")

    assert '"/skills/{skill_id}/invoke"' in engineering_api
    assert "EngineeringInvestigationCreateRequest" in engineering_api
    assert "EngineeringInvestigationResponse" in engineering_api
    assert (
        '"/engineering/skills/engineering.investigation_change_plan/invoke"'
        in panel
    )
    assert "engineering.ai_draft/invoke" not in panel
    assert "selectedSkillId" not in panel
    assert "activeSkillId" not in panel
