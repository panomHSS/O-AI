from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.contracts.ai_brain_routing import AIMode
from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveTurnState,
)
from app.contracts.cognitive_runtime_adoption import (
    D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION,
    CognitiveRuntimeObservation,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.core.config import Settings
from app.services.cognitive_executive import CognitiveExecutiveFailure
from app.services.cognitive_runtime_observability import CognitiveRuntimeObserver
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ChatTurnResult
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer

from tests import test_d136_cognitive_executive as d136


ROOT = Path(__file__).resolve().parents[2]
CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _command(request_id: str = "request-1") -> CommandRequest:
    return CommandRequest(
        request_id=request_id,
        command="chat.message",
        arguments={
            "message": "hello",
            "conversation_id": CONVERSATION_ID,
            "project_id": PROJECT_ID,
        },
    )


def _failed(code: CognitiveFailureCode):
    return replace(
        d136.outcome(CognitiveTurnState.FAILED),
        failure_code=code,
    )


class _CaptureLogger:
    def __init__(self) -> None:
        self.records: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def info(self, *args, **kwargs) -> None:
        self.records.append((args, kwargs))


class _RecordingObserver:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.selections: list[dict[str, object]] = []
        self.outcomes: list[dict[str, object]] = []

    def try_record_selection(self, **kwargs) -> bool:
        if self.fail:
            raise RuntimeError("observer unavailable")
        self.selections.append(kwargs)
        return True

    def try_record_cognitive_outcome(self, **kwargs) -> bool:
        if self.fail:
            raise RuntimeError("observer unavailable")
        self.outcomes.append(kwargs)
        return True


class _FakeCognitive:
    def __init__(self, *, outcome=None, failure=None) -> None:
        self.outcome = outcome or d136.outcome()
        self.failure = failure
        self.calls: list[dict[str, object]] = []

    def process_chat(self, command, *, ai_mode=None, task_kind=None):
        self.calls.append(
            {
                "command": command,
                "ai_mode": ai_mode,
                "task_kind": task_kind,
            }
        )
        if self.failure is not None:
            raise CognitiveExecutiveFailure(self.failure)
        return SimpleNamespace(
            chat_turn=ChatTurnResult(
                reply="cognitive answer",
                conversation_id=CONVERSATION_ID,
                project_id=PROJECT_ID,
            ),
            outcome=self.outcome,
        )


class _Planner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def plan(
        self,
        command,
        *,
        task_kind=AITaskKind.GENERAL_CHAT,
        ai_mode=None,
    ):
        self.calls.append(
            {
                "command": command,
                "task_kind": task_kind,
                "ai_mode": ai_mode,
            }
        )
        plan = ExecutionPlan(
            request_id=command.request_id,
            adapter_id="chatgpt.default",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="ai.generate_text",
                    parameters={
                        "capability_id": "text_generation",
                        "model_id": "model-a",
                    },
                ),
            ),
            owner_approval_required=False,
        )
        return ExecutionPlanningOutcome(
            request_id=command.request_id,
            status="planned",
            target_kind="ai",
            plan=plan,
            reason_code="ai_text_generation_planned",
        )


class _Guard:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []

    def authorize(self, command, planning):
        self.calls.append((command, planning))
        return ExecutionAuthorization(
            request_id=command.request_id,
            status="authorized",
            target_kind="ai",
            source_plan_digest="a" * 64,
            execution_plan=planning.plan,
            reason_code="approval_not_required",
        )


class _Runtime:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []
        self.adapter = object()

    def bind(self, command, authorization):
        self.calls.append((command, authorization))
        return self.adapter


class _Conversation:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def send_context_message(
        self,
        message,
        conversation_id,
        project_id,
        *,
        ai_adapter,
    ):
        self.calls.append(
            {
                "message": message,
                "conversation_id": conversation_id,
                "project_id": project_id,
                "ai_adapter": ai_adapter,
            }
        )
        return ChatTurnResult(
            reply="legacy answer",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
        )


def _orchestrator(
    *,
    cognitive=None,
    observer=None,
):
    planner = _Planner()
    guard = _Guard()
    runtime = _Runtime()
    conversation = _Conversation()
    normalizer = OrchestrationErrorNormalizer()
    orchestrator = CommandOrchestrator(
        conversation_service=conversation,  # type: ignore[arg-type]
        planner=planner,  # type: ignore[arg-type]
        guard=guard,  # type: ignore[arg-type]
        ai_runtime=runtime,  # type: ignore[arg-type]
        error_normalizer=normalizer,
        response_composer=ResponseComposer(normalizer),
        tool_runtime=object(),  # type: ignore[arg-type]
        cognitive_executive=cognitive,  # type: ignore[arg-type]
        cognitive_runtime_observer=observer,  # type: ignore[arg-type]
    )
    return orchestrator, planner, guard, runtime, conversation


_FAILURE_EXPECTATIONS = (
    (CognitiveFailureCode.TURN_IN_PROGRESS, "COGNITIVE_RUNTIME_BUSY"),
    (
        CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
        "COGNITIVE_RUNTIME_UNAVAILABLE",
    ),
    (CognitiveFailureCode.CONTEXT_UNSTABLE, "COGNITIVE_RUNTIME_UNAVAILABLE"),
    (CognitiveFailureCode.CRITIC_UNAVAILABLE, "COGNITIVE_RUNTIME_UNAVAILABLE"),
    (CognitiveFailureCode.STALE_LATE_RESULT, "COGNITIVE_RUNTIME_UNAVAILABLE"),
    (CognitiveFailureCode.INVALID_COGNITION, "COGNITIVE_RESPONSE_BLOCKED"),
    (CognitiveFailureCode.CONTRACT_VIOLATION, "COGNITIVE_RESPONSE_BLOCKED"),
)


def run_case(case: int) -> None:
    if case == 1:
        assert Settings.model_fields["oai_cognitive_runtime_enabled"].default is True
    elif case == 2:
        assert (
            Settings.model_fields["oai_cognitive_runtime_enabled"].annotation
            is bool
        )
    elif case == 3:
        text = _source("backend/app/api/dependencies.py")
        assert "settings.oai_cognitive_runtime_enabled" in text
    elif case == 4:
        assert "_d136_live_runtime_enabled" not in _source(
            "backend/app/api/dependencies.py"
        )
    elif case == 5:
        text = _source("backend/app/api/dependencies.py")
        assert "chat_service: ChatService = Depends(get_chat_service)" in text
    elif case == 6:
        text = _source("backend/app/api/dependencies.py")
        assert "context_resolver: ContextResolver = Depends(get_context_resolver)" in text
    elif case == 7:
        text = _source("backend/app/api/dependencies.py")
        assert "context_snapshot_service: ContextSnapshotService = Depends(" in text
    elif case == 8:
        text = _source("backend/app/api/dependencies.py")
        assert "get_cognitive_runtime_observer" in text
        assert (
            "get_conversation_service not in request.app.dependency_overrides"
            in text
        )
    elif 9 <= case <= 15:
        failure, expected = _FAILURE_EXPECTATIONS[case - 9]
        normalized = OrchestrationErrorNormalizer().normalize_cognitive_outcome(
            "request-1",
            _failed(failure),
        )
        assert normalized.code == expected
        assert normalized.status == "failed"
        assert normalized.request_id == "request-1"
    elif case == 16:
        normalized = OrchestrationErrorNormalizer().normalize_cognitive_outcome(
            "request-1",
            d136.outcome(),
        )
        assert normalized.code == "INTERNAL_ERROR"
    elif 17 <= case <= 23:
        failure, expected = _FAILURE_EXPECTATIONS[case - 17]
        cognitive = _FakeCognitive(failure=_failed(failure))
        observer = _RecordingObserver()
        orchestrator, planner, guard, runtime, conversation = _orchestrator(
            cognitive=cognitive,
            observer=observer,
        )
        result = orchestrator.process_chat(_command())
        assert result.response.result.error == expected
        assert result.chat_turn is None
        assert len(cognitive.calls) == 1
        assert cognitive.calls[0]["task_kind"] is AITaskKind.GENERAL_CHAT
        assert planner.calls == []
        assert guard.calls == []
        assert runtime.calls == []
        assert conversation.calls == []
        assert len(observer.selections) == 1
        assert observer.selections[0]["selected_lane"] == "cognitive"
        assert len(observer.outcomes) == 1
    elif 24 <= case <= 30:
        mode = (None, AIMode.AUTO, AIMode.LOCAL_AI, AIMode.CLOUD_AI)[
            (case - 24) % 4
        ]
        cognitive = _FakeCognitive()
        observer = _RecordingObserver()
        orchestrator, planner, guard, runtime, conversation = _orchestrator(
            cognitive=cognitive,
            observer=observer,
        )
        result = orchestrator.process_chat(_command(), ai_mode=mode)
        assert result.response.result.status == "succeeded"
        assert result.response.message == "cognitive answer"
        assert result.chat_turn is not None
        assert cognitive.calls[0]["task_kind"] is AITaskKind.GENERAL_CHAT
        assert cognitive.calls[0]["ai_mode"] is mode
        assert planner.calls == []
        assert guard.calls == []
        assert runtime.calls == []
        assert conversation.calls == []
        assert observer.selections[0]["selected_lane"] == "cognitive"
        assert observer.outcomes[0]["outcome"].terminal_state is CognitiveTurnState.COMPLETED
    elif 31 <= case <= 38:
        mode = (None, AIMode.AUTO, AIMode.LOCAL_AI, AIMode.CLOUD_AI)[
            (case - 31) % 4
        ]
        observer = _RecordingObserver()
        orchestrator, planner, guard, runtime, conversation = _orchestrator(
            observer=observer,
        )
        result = orchestrator.process_chat(_command(), ai_mode=mode)
        assert result.response.result.status == "succeeded"
        assert result.response.message == "legacy answer"
        assert len(planner.calls) == 1
        assert planner.calls[0]["task_kind"] is AITaskKind.GENERAL_CHAT
        assert planner.calls[0]["ai_mode"] is mode
        assert len(guard.calls) == 1
        assert len(runtime.calls) == 1
        assert len(conversation.calls) == 1
        assert observer.selections[0]["selected_lane"] == "legacy"
        assert observer.outcomes == []
    elif 39 <= case <= 46:
        observer = _RecordingObserver(fail=True)
        cognitive = _FakeCognitive()
        orchestrator, planner, guard, runtime, conversation = _orchestrator(
            cognitive=cognitive,
            observer=observer,
        )
        result = orchestrator.process_chat(_command())
        assert result.response.result.status == "succeeded"
        assert result.response.message == "cognitive answer"
        assert planner.calls == []
        assert guard.calls == []
        assert runtime.calls == []
        assert conversation.calls == []
    elif 47 <= case <= 54:
        logger = _CaptureLogger()
        runtime_observer = CognitiveRuntimeObserver(
            workspace_id=WorkspaceId.PERSONAL,
            logger=logger,  # type: ignore[arg-type]
        )
        assert runtime_observer.try_record_selection(
            request_id=f"request-{case}",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
            selected_lane=("cognitive" if case % 2 else "legacy"),
            task_kind=AITaskKind.GENERAL_CHAT,
        )
        payload = logger.records[-1][1]["extra"]["cognitive_runtime"]
        assert payload["request_id"] == f"request-{case}"
        assert payload["workspace_id"] == "personal"
        assert payload["task_kind"] == "general_chat"
        assert payload["terminal_state"] is None
    elif 55 <= case <= 61:
        logger = _CaptureLogger()
        runtime_observer = CognitiveRuntimeObserver(
            workspace_id=WorkspaceId.PERSONAL,
            logger=logger,  # type: ignore[arg-type]
        )
        assert runtime_observer.try_record_cognitive_outcome(
            request_id="request-1",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
            task_kind=AITaskKind.GENERAL_CHAT,
            outcome=d136.outcome(),
        )
        payload = logger.records[-1][1]["extra"]["cognitive_runtime"]
        checks = (
            ("selected_lane", "cognitive"),
            ("terminal_state", "completed"),
            ("failure_code", None),
            ("publication_disposition", "eligible"),
            ("adapter_id", "chatgpt.default"),
            ("model_id", "model-a"),
            ("invocation_count", 1),
        )
        assert payload[checks[case - 55][0]] == checks[case - 55][1]
    elif 62 <= case <= 66:
        event = CognitiveRuntimeObservation(
            request_id="request-1",
            workspace_id=WorkspaceId.PERSONAL,
            selected_lane="legacy",
            task_kind=AITaskKind.GENERAL_CHAT,
            conversation_id=str(CONVERSATION_ID),
            project_id=str(PROJECT_ID),
        )
        checks = (
            event.contract_version
            == D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION,
            event.selected_lane == "legacy",
            event.task_kind is AITaskKind.GENERAL_CHAT,
            event.terminal_state is None,
            event.failure_code is None,
        )
        assert checks[case - 62]
    elif 67 <= case <= 69:
        code = (
            "COGNITIVE_RUNTIME_BUSY",
            "COGNITIVE_RUNTIME_UNAVAILABLE",
            "COGNITIVE_RESPONSE_BLOCKED",
        )[case - 67]
        response = ResponseComposer().compose_error(
            SimpleNamespace(
                request_id="request-1",
                code=code,
                status="failed",
            )
        )
        assert response.result.error == code
        assert response.message == {
            "COGNITIVE_RUNTIME_BUSY": "The cognitive runtime is currently busy.",
            "COGNITIVE_RUNTIME_UNAVAILABLE": (
                "The cognitive runtime could not complete this request."
            ),
            "COGNITIVE_RESPONSE_BLOCKED": (
                "The response could not be safely completed."
            ),
        }[code]
    elif case == 70:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert "selected_lane" in names and "task_kind" in names
    elif case == 71:
        names = {field.name for field in fields(CognitiveRuntimeObservation)}
        assert {"terminal_state", "failure_code", "publication_disposition"} <= names
    elif case == 72:
        source = _source("backend/app/services/command_orchestrator.py")
        assert "task_kind = AITaskKind.GENERAL_CHAT" in source
        assert "task_kind=task_kind" in source
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 73),
    ids=[f"F{i:02d}" for i in range(1, 73)],
)
def test_d140_functional_matrix(case: int) -> None:
    run_case(case)
