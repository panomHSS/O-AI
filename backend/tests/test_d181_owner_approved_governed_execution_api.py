from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.chat import send_chat_message
from app.api.v1.execution_approvals import require_local_execution_request_marker
from app.contracts.explicit_action_live_chat_routing import ExplicitActionLiveChatProjectionOutcome
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.chat import ChatRequest
from tests.test_d180_explicit_action_live_chat_routing import nonprepared_handoff, prepared_handoff
from tests.test_d180_explicit_action_live_chat_routing_api import (
    Bridge, Calendar, CalendarUX, Cross, D180, Orchestrator, Pipeline,
    ProjectUpdates, RuntimeStatus, CONVERSATION_ID,
)

WORKSPACE = WorkspaceScope(WorkspaceId.PERSONAL)


class BindingStub:
    def __init__(self) -> None:
        self.calls = []

    def register_cognitive_projection(self, **kwargs):
        self.calls.append(kwargs)
        return object()


def call_chat(*, projection, binder):
    bridge = Bridge()
    pipeline = Pipeline()
    orchestrator = Orchestrator()
    d180 = D180("cognitive", projection)
    response = send_chat_message(
        request=SimpleNamespace(
            state=SimpleNamespace(request_id="d181-chat-turn"),
            app=SimpleNamespace(state=SimpleNamespace()),
        ),
        payload=ChatRequest(message="/action system info"),
        workspace_scope=WORKSPACE,
        command_input_pipeline=pipeline,  # type: ignore[arg-type]
        command_orchestrator=orchestrator,  # type: ignore[arg-type]
        project_update_orchestrator=ProjectUpdates(),  # type: ignore[arg-type]
        chat_action_bridge=bridge,  # type: ignore[arg-type]
        cross_connector_chat_service=Cross(),  # type: ignore[arg-type]
        explicit_action_live_chat_routing=d180,
        owner_approved_governed_execution=binder,  # type: ignore[arg-type]
        calendar_write_chat_service=Calendar(),  # type: ignore[arg-type]
        calendar_write_chat_ux_service=CalendarUX(),  # type: ignore[arg-type]
        conversation_service=object(),  # type: ignore[arg-type]
        runtime_capability_chat_service=RuntimeStatus(),  # type: ignore[arg-type]
        x_oai_local_request="1",
    )
    return response, pipeline


def test_d181_chat_registers_before_exposing_pending_cognitive_approval():
    handoff, approval = prepared_handoff()
    projection = ExplicitActionLiveChatProjectionOutcome(
        status="pending_approval",
        reason_code=handoff.reason_code,
        approval=approval,
        handoff=handoff,
    )
    binder = BindingStub()
    response, pipeline = call_chat(projection=projection, binder=binder)
    assert response.data.action is not None
    assert response.data.action.status == "pending_approval"
    assert len(binder.calls) == 1
    call = binder.calls[0]
    assert call["projection"] is projection
    assert call["command"] is pipeline.command
    assert call["conversation_id"] == CONVERSATION_ID


def test_d181_chat_does_not_bind_nonpending_cognitive_projection():
    handoff = nonprepared_handoff("cognitive_outcome_unavailable")
    projection = ExplicitActionLiveChatProjectionOutcome(
        status="unavailable",
        reason_code=handoff.reason_code,
        approval=None,
        handoff=handoff,
    )
    binder = BindingStub()
    response, _ = call_chat(projection=projection, binder=binder)
    assert response.data.action is not None
    assert response.data.action.status == "unavailable"
    assert binder.calls == []


def test_d181_local_decision_marker_remains_mandatory():
    with pytest.raises(HTTPException) as error:
        require_local_execution_request_marker(None)
    assert error.value.status_code == 403
