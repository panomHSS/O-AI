from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.v1.chat import send_chat_message
from app.contracts.chat_action import ChatActionBridgeOutcome
from app.contracts.command import CommandRequest
from app.contracts.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatProjectionOutcome,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.chat import ChatRequest
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.conversations import ChatTurnResult
from app.services.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatRoutingService,
)
from tests.test_d180_explicit_action_live_chat_routing import (
    nonprepared_handoff,
    prepared_handoff,
)


CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
WORKSPACE = WorkspaceScope(WorkspaceId.PERSONAL)


class Bridge:
    def __init__(self, *, plugin=False) -> None:
        self.plugin = plugin
        self.process_calls = 0

    def calendar_clarification_disposition(self, *_args):
        return "none"

    def is_action_directive(self, message):
        normalized = message.strip()
        return normalized == "/action" or normalized.startswith("/action ")

    def is_plugin_action_request(self, _message):
        return self.plugin

    def is_pending_calendar_plaintext_approval(self, *_args):
        return False

    def is_pending_gmail_plaintext_approval(self, *_args):
        return False

    def process(self, **_kwargs):
        self.process_calls += 1
        handoff, approval = prepared_handoff()
        return ChatActionBridgeOutcome(
            reply="legacy action reply",
            conversation_id=CONVERSATION_ID,
            status="pending_approval",
            reason_code=handoff.reason_code,
            approval=approval,
        )


class Pipeline:
    def __init__(self) -> None:
        self.calls = []
        self.command = None

    def normalize_chat(self, **kwargs):
        self.calls.append(kwargs)
        self.command = CommandRequest(
            request_id=kwargs["request_id"],
            command="chat.message",
            arguments={
                "message": kwargs["message"],
                "conversation_id": kwargs["conversation_id"],
                "project_id": kwargs["project_id"],
            },
        )
        return self.command


class Orchestrator:
    def __init__(self, *, turn=True) -> None:
        self.calls = []
        self.turn = turn
        self.last_outcome = None

    def process_chat(self, command, *, ai_mode=None):
        self.calls.append((command, ai_mode))
        chat_turn = (
            ChatTurnResult(
                reply="cognitive persisted reply",
                conversation_id=CONVERSATION_ID,
                project_id=None,
            )
            if self.turn
            else None
        )
        self.last_outcome = CommandOrchestrationOutcome(
            response=SimpleNamespace(
                result=SimpleNamespace(error="AI_ROUTE_UNAVAILABLE")
            ),  # type: ignore[arg-type]
            chat_turn=chat_turn,
        )
        return self.last_outcome


class D180(ExplicitActionLiveChatRoutingService):
    def __init__(self, mode, projection=None) -> None:
        self._mode = mode
        self.projection = projection
        self.calls = []

    @property
    def route_mode(self):
        return self._mode

    def project_cognitive(self, message, **kwargs):
        self.calls.append((message, kwargs))
        if self.projection is None:
            handoff = nonprepared_handoff("cognitive_outcome_unavailable")
            return ExplicitActionLiveChatProjectionOutcome(
                status="unavailable",
                reason_code=handoff.reason_code,
                approval=None,
                handoff=handoff,
            )
        return self.projection


class Cross:
    def is_request(self, _message):
        return False


class Calendar:
    def is_request(self, _message):
        return False

    def pending_plaintext_approval_disposition(self, **_kwargs):
        return "none"


class CalendarUX:
    def plaintext_decision_kind(self, **_kwargs):
        return "none"


class RuntimeStatus:
    def is_request(self, _message):
        return False


class ProjectUpdates:
    def __init__(self):
        self.calls = 0

    def process(self, _turn):
        self.calls += 1
        raise AssertionError("D180 explicit action must not reach project updates")


def call(
    *,
    message="/action system info",
    local="1",
    bridge=None,
    pipeline=None,
    orchestrator=None,
    d180=None,
    ai_mode=None,
    project_updates=None,
):
    bridge = bridge or Bridge()
    pipeline = pipeline or Pipeline()
    orchestrator = orchestrator or Orchestrator()
    d180 = d180 or D180("legacy")
    project_updates = project_updates or ProjectUpdates()
    response = send_chat_message(
        request=SimpleNamespace(
            state=SimpleNamespace(request_id="d180-request"),
            app=SimpleNamespace(state=SimpleNamespace()),
        ),
        payload=ChatRequest(
            message=message,
            ai_mode=ai_mode,
        ),
        workspace_scope=WORKSPACE,
        command_input_pipeline=pipeline,  # type: ignore[arg-type]
        command_orchestrator=orchestrator,  # type: ignore[arg-type]
        project_update_orchestrator=project_updates,  # type: ignore[arg-type]
        chat_action_bridge=bridge,  # type: ignore[arg-type]
        cross_connector_chat_service=Cross(),  # type: ignore[arg-type]
        calendar_write_chat_service=Calendar(),  # type: ignore[arg-type]
        calendar_write_chat_ux_service=CalendarUX(),  # type: ignore[arg-type]
        conversation_service=object(),  # type: ignore[arg-type]
        runtime_capability_chat_service=RuntimeStatus(),  # type: ignore[arg-type]
        explicit_action_live_chat_routing=d180,
        x_oai_local_request=local,
    )
    return response, bridge, pipeline, orchestrator, d180, project_updates


def test_d180_untrusted_action_stops_before_both_routes() -> None:
    bridge = Bridge()
    pipeline = Pipeline()
    orchestrator = Orchestrator()
    d180 = D180("cognitive")
    with pytest.raises(HTTPException) as error:
        call(
            local=None,
            bridge=bridge,
            pipeline=pipeline,
            orchestrator=orchestrator,
            d180=d180,
        )
    assert error.value.status_code == 403
    assert bridge.process_calls == 0
    assert pipeline.calls == []
    assert orchestrator.calls == []
    assert d180.calls == []


def test_d180_legacy_action_uses_d46_only() -> None:
    response, bridge, pipeline, orchestrator, d180, _ = call(
        d180=D180("legacy")
    )
    assert response.data.reply == "legacy action reply"
    assert response.data.action is not None
    assert response.data.action.status == "pending_approval"
    assert bridge.process_calls == 1
    assert pipeline.calls == []
    assert orchestrator.calls == []
    assert d180.calls == []


def test_d180_cognitive_action_uses_pipeline_orchestrator_and_projection_once() -> None:
    handoff, approval = prepared_handoff()
    projection = ExplicitActionLiveChatProjectionOutcome(
        status="pending_approval",
        reason_code=handoff.reason_code,
        approval=approval,
        handoff=handoff,
    )
    response, bridge, pipeline, orchestrator, d180, _ = call(
        d180=D180("cognitive", projection),
    )
    assert response.data.reply == "cognitive persisted reply"
    assert response.data.conversation_id == CONVERSATION_ID
    assert response.data.action is not None
    assert response.data.action.status == "pending_approval"
    assert response.data.action.approval is not None
    assert bridge.process_calls == 0
    assert len(pipeline.calls) == 1
    assert len(orchestrator.calls) == 1
    assert len(d180.calls) == 1
    assert orchestrator.calls[0][0] is pipeline.command
    assert d180.calls[0][1]["command"] is pipeline.command
    assert d180.calls[0][1]["orchestration_outcome"] is orchestrator.last_outcome


def test_d180_cognitive_action_forwards_ai_mode() -> None:
    _, _, _, orchestrator, _, _ = call(
        d180=D180("cognitive"),
        ai_mode="local_ai",
    )
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0][1].value == "local_ai"


def test_d180_cognitive_unavailable_never_falls_back_to_d46() -> None:
    response, bridge, _, _, d180, _ = call(d180=D180("cognitive"))
    assert response.data.action is not None
    assert response.data.action.status == "unavailable"
    assert response.data.action.reason_code == "cognitive_outcome_unavailable"
    assert bridge.process_calls == 0
    assert len(d180.calls) == 1


def test_d180_cognitive_action_never_runs_project_update() -> None:
    project_updates = ProjectUpdates()
    call(
        d180=D180("cognitive"),
        project_updates=project_updates,
    )
    assert project_updates.calls == 0


def test_d180_plugin_request_remains_d46_under_cognitive_mode() -> None:
    response, bridge, pipeline, orchestrator, d180, _ = call(
        message="plugin action request",
        bridge=Bridge(plugin=True),
        d180=D180("cognitive"),
    )
    assert response.data.reply == "legacy action reply"
    assert bridge.process_calls == 1
    assert pipeline.calls == []
    assert orchestrator.calls == []
    assert d180.calls == []


def test_d180_normal_chat_bypasses_d180_and_d46() -> None:
    response, bridge, pipeline, orchestrator, d180, _ = call(
        message="hello",
        bridge=Bridge(),
        d180=D180("cognitive"),
    )
    assert response.data.reply == "cognitive persisted reply"
    assert response.data.action is None
    assert bridge.process_calls == 0
    assert len(pipeline.calls) == 1
    assert len(orchestrator.calls) == 1
    assert d180.calls == []


def test_d180_cognitive_projection_preserves_exact_message_and_orchestration() -> None:
    _, _, pipeline, orchestrator, d180, _ = call(d180=D180("cognitive"))
    assert d180.calls[0][0] == "/action system info"
    kwargs = d180.calls[0][1]
    assert kwargs["command"] is pipeline.command
    assert kwargs["orchestration_outcome"] is orchestrator.last_outcome


def test_d180_legacy_action_reply_and_conversation_remain_d46_owned() -> None:
    response, bridge, _, _, _, _ = call(d180=D180("legacy"))
    assert bridge.process_calls == 1
    assert response.data.reply == "legacy action reply"
    assert response.data.conversation_id == CONVERSATION_ID
