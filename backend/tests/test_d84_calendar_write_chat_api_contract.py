from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.router import api_router
from app.schemas.calendar_write_chat import CalendarWriteChatDecisionRequest
from app.schemas.chat import ChatResponse


_DIGEST = "a" * 64


def test_d84_chat_response_has_separate_calendar_write_surface() -> None:
    assert "calendar_write" in ChatResponse.model_fields
    assert "action" in ChatResponse.model_fields


def test_d84_decision_request_accepts_digest_only() -> None:
    request = CalendarWriteChatDecisionRequest(write_digest=_DIGEST)
    assert request.write_digest == _DIGEST

    with pytest.raises(ValidationError):
        CalendarWriteChatDecisionRequest(
            write_digest=_DIGEST,
            conversation_id="00000000-0000-0000-0000-000000000000",
        )


def test_d84_structured_decision_routes_are_registered() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(api_router)
    paths = app.openapi()["paths"]
    approve_path = "/api/v1/calendar-write-chat/{approval_id}/approve"
    deny_path = "/api/v1/calendar-write-chat/{approval_id}/deny"
    assert approve_path in paths
    assert deny_path in paths
    assert "post" in paths[approve_path]
    assert "post" in paths[deny_path]


def test_d84_chat_route_does_not_reimplement_d74() -> None:
    source = Path("app/api/v1/chat.py").read_text(encoding="utf-8")
    assert "execute_create(" not in source
    assert "CalendarWriteChatProposalResponse.from_outcome" in source
    assert "calendar_write_chat_ux_service.propose_candidate" in source


def test_d84_decision_api_uses_server_bound_conversation() -> None:
    source = Path("app/api/v1/calendar_write_chat.py").read_text(encoding="utf-8")
    d84_source = source[source.index("def deny_calendar_write_chat(") :]
    assert "payload.conversation_id" not in d84_source
    assert "_complete_original_conversation(" in d84_source
    assert "conversation_service.complete_turn" in source
    assert "service.approve(" in d84_source
    assert "service.deny(" in d84_source
    assert "execute_create(" not in d84_source


def test_d81_labels_calendar_create_via_chat_only() -> None:
    source = Path("app/services/chat_runtime_capability.py").read_text(encoding="utf-8")
    assert "Write via Chat" in source
    assert "รองรับการสร้างนัด" in source
    assert "create event supported" in source
    assert "Update/Delete via Chat" in source
    assert "Calendar update via Chat" not in source
    assert "Calendar delete via Chat" not in source
