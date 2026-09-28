"""D122 dedicated Engineering AI Draft Skill owner API tests."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_skill_invocation_bridge
from app.api.v1.engineering import router
from app.contracts.engineering_ai_draft import EngineeringAIDraftResult
from app.services.builtin_skills import ENGINEERING_AI_DRAFT_SKILL_ID
from app.services.engineering_ai_draft import (
    EngineeringAIDraftConversationNotFoundError,
    EngineeringAIDraftError,
)
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_DESCRIPTOR_MISMATCH,
    SKILL_INVOCATION_REQUEST_INVALID,
    SkillInvocationError,
)

_LOCAL_HEADERS = {"X-OAI-Local-Request": "1"}
_STATIC_PATH = "/engineering/skills/engineering.ai_draft/invoke"
_DYNAMIC_PATH = "/engineering/skills/{skill_id}/invoke"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENGINEERING_API = (
    _REPO_ROOT / "backend" / "app" / "api" / "v1" / "engineering.py"
)


class _Bridge:
    def __init__(self, outcome=None) -> None:
        self.calls: list[tuple[str, object]] = []
        self._outcome = outcome

    def invoke(self, *, skill_id, request):
        self.calls.append((skill_id, request))
        if isinstance(self._outcome, Exception):
            raise self._outcome
        if self._outcome is not None:
            return self._outcome
        return EngineeringAIDraftResult(
            conversation_id=request.conversation_id,
            relative_path=request.relative_path,
            draft_operation="create_text",
            source_state="absent",
            source_sha256=None,
            source_size_bytes=None,
            draft_content="Candidate D122 draft.",
            ai_adapter_id="test.adapter",
        )


def _client(bridge: _Bridge) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_skill_invocation_bridge] = lambda: bridge
    return TestClient(app)


def _payload(conversation_id) -> dict[str, object]:
    return {
        "conversation_id": str(conversation_id),
        "relative_path": "notes/d122.txt",
        "instruction": "Draft bounded D122 candidate text.",
    }


def test_d122_static_route_precedes_d116_dynamic_route() -> None:
    paths = [route.path for route in router.routes]
    assert _STATIC_PATH in paths
    assert _DYNAMIC_PATH in paths
    assert paths.index(_STATIC_PATH) < paths.index(_DYNAMIC_PATH)


def test_d122_route_requires_existing_local_owner_marker() -> None:
    bridge = _Bridge()
    response = _client(bridge).post(_STATIC_PATH, json=_payload(uuid4()))
    assert response.status_code == 403
    assert bridge.calls == []


def test_d122_valid_request_invokes_exact_ai_draft_skill_once() -> None:
    conversation_id = uuid4()
    bridge = _Bridge()

    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json=_payload(conversation_id),
    )

    assert response.status_code == 200
    assert len(bridge.calls) == 1

    skill_id, request = bridge.calls[0]
    assert skill_id == ENGINEERING_AI_DRAFT_SKILL_ID
    assert request.conversation_id == conversation_id
    assert request.relative_path == "notes/d122.txt"
    assert request.instruction == "Draft bounded D122 candidate text."

    assert response.json()["data"] == {
        "contract_version": "d110.v1",
        "conversation_id": str(conversation_id),
        "relative_path": "notes/d122.txt",
        "draft_operation": "create_text",
        "source_state": "absent",
        "source_sha256": None,
        "source_size_bytes": None,
        "draft_content": "Candidate D122 draft.",
        "ai_adapter_id": "test.adapter",
    }


def test_d122_investigation_shaped_body_fails_before_bridge() -> None:
    bridge = _Bridge()

    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json={
            "conversation_id": str(uuid4()),
            "instruction": "Investigation shape must not become D110.",
            "focus_paths": [],
        },
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert bridge.calls == []


def test_d122_bridge_descriptor_mismatch_reuses_skill_http_mapping() -> None:
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_DESCRIPTOR_MISMATCH)
    )
    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json=_payload(uuid4()),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == SKILL_INVOCATION_DESCRIPTOR_MISMATCH
    assert len(bridge.calls) == 1


def test_d122_bridge_request_invalid_reuses_skill_http_mapping() -> None:
    bridge = _Bridge(
        SkillInvocationError(SKILL_INVOCATION_REQUEST_INVALID)
    )
    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json=_payload(uuid4()),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == SKILL_INVOCATION_REQUEST_INVALID
    assert len(bridge.calls) == 1


def test_d122_missing_conversation_reuses_d110_not_found_mapping() -> None:
    bridge = _Bridge(EngineeringAIDraftConversationNotFoundError())
    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json=_payload(uuid4()),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "engineering_ai_draft_conversation_not_found"
    )
    assert len(bridge.calls) == 1


def test_d122_d110_unavailable_reuses_service_unavailable_mapping() -> None:
    bridge = _Bridge(
        EngineeringAIDraftError("engineering_ai_draft_unavailable")
    )
    response = _client(bridge).post(
        _STATIC_PATH,
        headers=_LOCAL_HEADERS,
        json=_payload(uuid4()),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "engineering_ai_draft_unavailable"
    assert len(bridge.calls) == 1


def test_d122_static_route_source_uses_bridge_not_direct_d110_workflow() -> None:
    source = _ENGINEERING_API.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    node = functions["invoke_engineering_ai_draft_skill"]
    lines = source.splitlines()
    block = "\n".join(lines[node.lineno - 1 : node.end_lineno])

    assert "EngineeringAIDraftCreateRequest" in block
    assert "EngineeringAIDraftResponse" in block
    assert "EngineeringAIDraftRequest(" in block
    assert "bridge.invoke(" in block
    assert "ENGINEERING_AI_DRAFT_SKILL_ID" in block

    assert "EngineeringAIDraftWorkflowService" not in block
    assert "get_engineering_ai_draft_workflow_service" not in block
    assert ".draft(" not in block
    assert "create_engineering_proposal" not in block
    assert "engineering_apply" not in block
