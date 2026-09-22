from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.engineering import (
    create_engineering_investigation,
    require_local_engineering_owner_request_marker,
)
from app.contracts.engineering_investigation import (
    EngineeringInvestigationChangePlanItem,
    EngineeringInvestigationFinding,
    EngineeringInvestigationRequest,
    EngineeringInvestigationResult,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.engineering_investigation import (
    EngineeringInvestigationCreateRequest,
)
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationConversationNotFoundError,
    EngineeringInvestigationWorkflowService,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


class ConversationLookup:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.lookups: list[str] = []

    def get(self, conversation_id: str):
        self.lookups.append(conversation_id)
        return object() if self.exists else None


class InvestigationCore:
    def __init__(self, result: EngineeringInvestigationResult) -> None:
        self.result = result
        self.calls = []

    def investigate(self, *, workspace_scope, request):
        self.calls.append((workspace_scope, request))
        return self.result


def result(conversation_id):
    return EngineeringInvestigationResult(
        conversation_id=conversation_id,
        summary="bounded summary",
        findings=(
            EngineeringInvestigationFinding(
                finding_id="finding-1",
                title="One finding",
                detail="Bounded detail.",
                evidence_refs=("overview:0",),
                confidence="medium",
            ),
        ),
        change_plan=(
            EngineeringInvestigationChangePlanItem(
                sequence=1,
                title="Inspect first",
                rationale="Stay read-only.",
                candidate_relative_path="README.md",
                candidate_change_kind="inspect",
                evidence_refs=("overview:0",),
            ),
        ),
        evidence_refs=("overview:0",),
    )


def test_d113_workflow_fails_before_ai_when_conversation_missing() -> None:
    conversations = ConversationLookup(exists=False)
    value = EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="inspect",
        focus_paths=("README.md",),
    )

    class Core:
        def investigate(self, **kwargs):
            raise AssertionError("must not run")

    from app.services.engineering_investigation import (
        EngineeringInvestigationService,
    )

    core = object.__new__(EngineeringInvestigationService)
    core.investigate = Core().investigate  # type: ignore[method-assign]

    workflow = EngineeringInvestigationWorkflowService(
        workspace_scope=PERSONAL,
        conversation_repository=conversations,
        investigation_service=core,
    )

    with pytest.raises(
        EngineeringInvestigationConversationNotFoundError,
        match="engineering_investigation_conversation_not_found",
    ):
        workflow.investigate(value)

    assert conversations.lookups == [str(value.conversation_id)]


def test_d113_api_returns_workspace_bound_non_authoritative_result() -> None:
    conversation_id = uuid4()
    payload = EngineeringInvestigationCreateRequest(
        conversation_id=conversation_id,
        instruction="inspect",
        focus_paths=["README.md"],
    )

    class FakeWorkflow:
        workspace_scope = PERSONAL

        def __init__(self) -> None:
            self.requests = []

        def investigate(self, request):
            self.requests.append(request)
            return result(request.conversation_id)

    service = FakeWorkflow()
    response = create_engineering_investigation(
        payload,
        None,
        service,  # type: ignore[arg-type]
    )

    assert response.data.workspace_id == "personal"
    assert response.data.conversation_id == conversation_id
    assert response.data.focus_paths == ["README.md"]
    assert response.data.summary == "bounded summary"
    assert response.data.findings[0].confidence == "medium"
    assert response.data.change_plan[0].candidate_change_kind == "inspect"

    assert len(service.requests) == 1
    request = service.requests[0]
    assert tuple(request.focus_paths) == ("README.md",)
    assert not hasattr(request, "provider")
    assert not hasattr(request, "model")
    assert not hasattr(request, "approval_id")


def test_d113_local_owner_marker_is_required() -> None:
    require_local_engineering_owner_request_marker("1")

    with pytest.raises(HTTPException) as captured:
        require_local_engineering_owner_request_marker(None)
    assert captured.value.status_code == 403


def test_d113_api_schema_forbids_authority_fields() -> None:
    with pytest.raises(Exception):
        EngineeringInvestigationCreateRequest(
            conversation_id=uuid4(),
            instruction="inspect",
            focus_paths=[],
            provider="cloud_ai",  # type: ignore[call-arg]
        )