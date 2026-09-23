# D116 owner-facing bounded Skill invocation API tests.

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_engineering_investigation_workflow_service,
    get_skill_invocation_bridge,
)
from app.api.v1.engineering import router
from app.contracts.engineering_investigation import (
    EngineeringInvestigationResult,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_investigation import EngineeringInvestigationError
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationConversationNotFoundError,
)
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_DESCRIPTOR_MISMATCH,
    SKILL_INVOCATION_REQUEST_INVALID,
    SKILL_INVOCATION_SKILL_NOT_FOUND,
    SKILL_INVOCATION_SKILL_UNSUPPORTED,
    SkillInvocationError,
)


_SKILL_ID = "engineering.investigation_change_plan"
_LOCAL_HEADERS = {"X-OAI-Local-Request": "1"}


class _Workflow:
    workspace_scope = WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)


class _Bridge:
    def __init__(self, outcome=None) -> None:
        self.calls = []
        self._outcome = outcome

    def invoke(self, *, skill_id, request):
        self.calls.append((skill_id, request))
        if isinstance(self._outcome, Exception):
            raise self._outcome
        if self._outcome is not None:
            return self._outcome
        return EngineeringInvestigationResult(
            conversation_id=request.conversation_id,
            summary="Bounded D116 result.",
            findings=(),
            change_plan=(),
            evidence_refs=(),
        )


def _client(bridge: _Bridge) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_skill_invocation_bridge] = lambda: bridge
    app.dependency_overrides[
        get_engineering_investigation_workflow_service
    ] = lambda: _Workflow()
    return TestClient(app)


def _payload(conversation_id) -> dict[str, object]:
    return {
        "conversation_id": str(conversation_id),
        "instruction": "Inspect the bounded implementation.",
        "focus_paths": [],
    }


def test_d116_route_requires_existing_local_owner_marker() -> None:
    conversation_id = uuid4()
    bridge = _Bridge()
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        json=_payload(conversation_id),
    )

    assert response.status_code == 403
    assert bridge.calls == []


def test_d116_supported_skill_invokes_bridge_once() -> None:
    conversation_id = uuid4()
    bridge = _Bridge()
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 200
    assert len(bridge.calls) == 1

    called_skill_id, request = bridge.calls[0]
    assert called_skill_id == _SKILL_ID
    assert request.conversation_id == conversation_id
    assert request.instruction == "Inspect the bounded implementation."
    assert request.focus_paths == ()

    body = response.json()
    assert body["data"]["workspace_id"] == "personal"
    assert body["data"]["conversation_id"] == str(conversation_id)


def test_d116_malformed_body_fails_before_bridge() -> None:
    bridge = _Bridge()
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json={
            "conversation_id": "not-a-uuid",
            "instruction": "",
            "focus_paths": [],
        },
    )

    assert response.status_code == 422
    assert bridge.calls == []


def test_d116_unknown_skill_maps_to_not_found() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_SKILL_NOT_FOUND)
    )
    client = _client(bridge)

    response = client.post(
        "/engineering/skills/unknown.skill/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == SKILL_INVOCATION_SKILL_NOT_FOUND
    assert len(bridge.calls) == 1


def test_d116_unsupported_skill_maps_to_unprocessable() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_SKILL_UNSUPPORTED)
    )
    client = _client(bridge)

    response = client.post(
        "/engineering/skills/other.skill/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == SKILL_INVOCATION_SKILL_UNSUPPORTED
    assert len(bridge.calls) == 1


def test_d116_descriptor_mismatch_maps_to_service_unavailable() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_DESCRIPTOR_MISMATCH)
    )
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == SKILL_INVOCATION_DESCRIPTOR_MISMATCH
    assert len(bridge.calls) == 1


def test_d116_request_error_maps_to_unprocessable() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_REQUEST_INVALID)
    )
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == SKILL_INVOCATION_REQUEST_INVALID
    assert len(bridge.calls) == 1


def test_d116_missing_conversation_reuses_d113_not_found_mapping() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        EngineeringInvestigationConversationNotFoundError()
    )
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "engineering_investigation_conversation_not_found"
    )
    assert len(bridge.calls) == 1


def test_d116_d113_ai_unavailable_reuses_service_unavailable_mapping() -> None:
    conversation_id = uuid4()
    bridge = _Bridge(
        EngineeringInvestigationError(
            "engineering_investigation_ai_unavailable"
        )
    )
    client = _client(bridge)

    response = client.post(
        f"/engineering/skills/{_SKILL_ID}/invoke",
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "engineering_investigation_ai_unavailable"
    )
    assert len(bridge.calls) == 1
