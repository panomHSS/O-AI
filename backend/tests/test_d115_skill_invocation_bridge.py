"""D115 Batch 01 bounded Skill invocation bridge tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.engineering_investigation import (
    EngineeringInvestigationRequest,
    EngineeringInvestigationResult,
)
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.builtin_skills import (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    build_builtin_skill_catalog,
)
from app.services.engineering_investigation import EngineeringInvestigationError
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationWorkflowService,
)
from app.services.skill_catalog import SkillCatalog
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_DESCRIPTOR_MISMATCH,
    SKILL_INVOCATION_REQUEST_INVALID,
    SKILL_INVOCATION_SKILL_NOT_FOUND,
    SKILL_INVOCATION_SKILL_UNSUPPORTED,
    SkillInvocationBridge,
    SkillInvocationError,
)


def _request() -> EngineeringInvestigationRequest:
    return EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="Inspect the bounded implementation.",
        focus_paths=(),
    )


def _result(
    request: EngineeringInvestigationRequest,
) -> EngineeringInvestigationResult:
    return EngineeringInvestigationResult(
        conversation_id=request.conversation_id,
        summary="Bounded result.",
        findings=(),
        change_plan=(),
        evidence_refs=(),
    )


class _ConversationRepository:
    def __init__(self, conversation_id) -> None:
        self._conversation_id = str(conversation_id)

    def get(self, conversation_id: str):
        if conversation_id == self._conversation_id:
            return object()
        return None


class _RecordingInvestigationService:
    def __init__(self) -> None:
        self.calls: list[tuple[object, EngineeringInvestigationRequest]] = []

    def investigate(self, *, workspace_scope, request):
        self.calls.append((workspace_scope, request))
        return _result(request)


def _workflow(
    request: EngineeringInvestigationRequest,
    recorder: _RecordingInvestigationService,
) -> EngineeringInvestigationWorkflowService:
    from app.contracts.workspace import WorkspaceId, WorkspaceScope

    workflow = object.__new__(EngineeringInvestigationWorkflowService)
    workflow._workspace_scope = WorkspaceScope(  # type: ignore[attr-defined]
        workspace_id=WorkspaceId.PERSONAL
    )
    workflow._conversations = _ConversationRepository(  # type: ignore[attr-defined]
        request.conversation_id
    )
    workflow._investigation_service = recorder  # type: ignore[attr-defined]
    return workflow


def _bridge(
    request: EngineeringInvestigationRequest,
    recorder: _RecordingInvestigationService,
    *,
    catalog: SkillCatalog | None = None,
) -> SkillInvocationBridge:
    return SkillInvocationBridge(
        catalog=catalog or build_builtin_skill_catalog(),
        engineering_investigation_workflow=_workflow(request, recorder),
    )


def test_supported_builtin_skill_delegates_once_through_d113_workflow() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()
    bridge = _bridge(request, recorder)

    result = bridge.invoke(
        skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
        request=request,
    )

    assert result == _result(request)
    assert len(recorder.calls) == 1
    assert recorder.calls[0][1] is request


@pytest.mark.parametrize(
    "skill_id",
    (
        "",
        " engineering.investigation_change_plan",
        "engineering.investigation_change_plan ",
        None,
        123,
    ),
)
def test_malformed_skill_identity_fails_before_delegate(
    skill_id: object,
) -> None:
    request = _request()
    recorder = _RecordingInvestigationService()
    bridge = _bridge(request, recorder)

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(skill_id=skill_id, request=request)

    assert exc.value.code == SKILL_INVOCATION_REQUEST_INVALID
    assert recorder.calls == []


def test_unknown_skill_fails_before_delegate() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()
    bridge = _bridge(request, recorder)

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(skill_id="missing.skill", request=request)

    assert exc.value.code == SKILL_INVOCATION_SKILL_NOT_FOUND
    assert recorder.calls == []


def test_catalog_known_but_unsupported_skill_fails_before_delegate() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()

    other = SkillDescriptor(
        skill_id="other.skill",
        version="1",
        display_name="Other Skill",
        description="Trusted server-side test metadata.",
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        input_kind="engineering_investigation_request",
        context_kind="bounded_repository_evidence",
        output_kind="engineering_investigation_result",
    )
    bridge = _bridge(
        request,
        recorder,
        catalog=SkillCatalog((other,)),
    )

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(skill_id="other.skill", request=request)

    assert exc.value.code == SKILL_INVOCATION_SKILL_UNSUPPORTED
    assert recorder.calls == []


def test_builtin_skill_descriptor_mismatch_fails_before_delegate() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()

    mismatched = SkillDescriptor(
        skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
        version="2",
        display_name=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL.display_name,
        description=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL.description,
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        input_kind="engineering_investigation_request",
        context_kind="bounded_repository_evidence",
        output_kind="engineering_investigation_result",
    )
    bridge = _bridge(
        request,
        recorder,
        catalog=SkillCatalog((mismatched,)),
    )

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(
            skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
            request=request,
        )

    assert exc.value.code == SKILL_INVOCATION_DESCRIPTOR_MISMATCH
    assert recorder.calls == []


@pytest.mark.parametrize(
    "bad_request",
    (
        None,
        {},
        {"instruction": "not a contract"},
        "engineering request",
    ),
)
def test_wrong_input_type_fails_before_delegate(
    bad_request: object,
) -> None:
    request = _request()
    recorder = _RecordingInvestigationService()
    bridge = _bridge(request, recorder)

    with pytest.raises(SkillInvocationError) as exc:
        bridge.invoke(
            skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
            request=bad_request,
        )

    assert exc.value.code == SKILL_INVOCATION_REQUEST_INVALID
    assert recorder.calls == []


def test_d113_workflow_error_is_propagated_without_retry() -> None:
    request = _request()

    class _FailingInvestigationService(_RecordingInvestigationService):
        def investigate(self, *, workspace_scope, request):
            self.calls.append((workspace_scope, request))
            raise EngineeringInvestigationError(
                "engineering_investigation_ai_unavailable"
            )

    recorder = _FailingInvestigationService()
    bridge = _bridge(request, recorder)

    with pytest.raises(EngineeringInvestigationError) as exc:
        bridge.invoke(
            skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
            request=request,
        )

    assert exc.value.code == "engineering_investigation_ai_unavailable"
    assert len(recorder.calls) == 1


def test_bridge_requires_real_skill_catalog() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()

    with pytest.raises(TypeError):
        SkillInvocationBridge(
            catalog=object(),  # type: ignore[arg-type]
            engineering_investigation_workflow=_workflow(request, recorder),
        )


def test_bridge_requires_owner_bound_d113_workflow_service_type() -> None:
    with pytest.raises(TypeError):
        SkillInvocationBridge(
            catalog=build_builtin_skill_catalog(),
            engineering_investigation_workflow=object(),  # type: ignore[arg-type]
        )


def test_bridge_has_no_generic_registration_or_execution_registry_surface() -> None:
    request = _request()
    recorder = _RecordingInvestigationService()
    bridge = _bridge(request, recorder)

    for forbidden_name in (
        "register",
        "unregister",
        "install",
        "load",
        "resolve_handler",
        "add_handler",
        "set_handler",
    ):
        assert not hasattr(bridge, forbidden_name)