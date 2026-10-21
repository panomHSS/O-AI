from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import pytest

from app.contracts.ai_brain_routing import AIMode
from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.command_orchestrator import CommandOrchestrationOutcome

from tests import test_d136_cognitive_executive as d136
from tests import test_d140_cognitive_runtime_adoption as d140


def test_d178_outcome_contract_adds_only_internal_cognitive_handoff_field() -> None:
    assert tuple(item.name for item in fields(CommandOrchestrationOutcome)) == (
        "response",
        "chat_turn",
        "cognitive_outcome",
    )


@pytest.mark.parametrize("mode", (None, AIMode.AUTO, AIMode.LOCAL_AI, AIMode.CLOUD_AI))
def test_d178_completed_cognitive_lane_hands_off_exact_outcome_identity(mode) -> None:
    brain = d136.outcome(CognitiveTurnState.COMPLETED)
    cognitive = d140._FakeCognitive(outcome=brain)
    observer = d140._RecordingObserver()
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator(
        cognitive=cognitive,
        observer=observer,
    )

    result = orchestrator.process_chat(d140._command(), ai_mode=mode)

    assert result.response.result.status == "succeeded"
    assert result.response.message == "cognitive answer"
    assert result.chat_turn is not None
    assert result.cognitive_outcome is brain
    assert len(cognitive.calls) == 1
    assert planner.calls == []
    assert guard.calls == []
    assert runtime.calls == []
    assert conversation.calls == []
    assert len(observer.outcomes) == 1
    assert observer.outcomes[0]["outcome"] is brain


def test_d178_bounded_insufficient_result_is_handed_off_without_reinterpretation() -> None:
    brain = d136.outcome(CognitiveTurnState.INSUFFICIENT)
    cognitive = d140._FakeCognitive(outcome=brain)
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator(
        cognitive=cognitive,
    )

    result = orchestrator.process_chat(d140._command())

    assert result.response.result.status == "succeeded"
    assert result.chat_turn is not None
    assert result.cognitive_outcome is brain
    assert result.cognitive_outcome.terminal_state is CognitiveTurnState.INSUFFICIENT
    assert result.cognitive_outcome.publication_disposition == "bounded_insufficiency_only"
    assert len(cognitive.calls) == 1
    assert planner.calls == []
    assert guard.calls == []
    assert runtime.calls == []
    assert conversation.calls == []


@pytest.mark.parametrize("mode", (None, AIMode.AUTO, AIMode.LOCAL_AI, AIMode.CLOUD_AI))
def test_d178_legacy_lane_has_no_cognitive_handoff(mode) -> None:
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator()

    result = orchestrator.process_chat(d140._command(), ai_mode=mode)

    assert result.response.result.status == "succeeded"
    assert result.response.message == "legacy answer"
    assert result.chat_turn is not None
    assert result.cognitive_outcome is None
    assert len(planner.calls) == 1
    assert len(guard.calls) == 1
    assert len(runtime.calls) == 1
    assert len(conversation.calls) == 1


def test_d178_d144_control_lane_has_no_cognitive_handoff() -> None:
    observer = d140._RecordingObserver()
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator(
        observer=observer,
    )
    binding = SimpleNamespace(
        conversation_id=d140.CONVERSATION_ID,
        project_id=d140.PROJECT_ID,
    )

    result = orchestrator._d144_control_turn(
        command=d140._command(),
        message="hello",
        binding=binding,
        ai_mode=None,
        task_kind=AITaskKind.GENERAL_CHAT,
    )

    assert result.response.result.status == "succeeded"
    assert result.response.message == "legacy answer"
    assert result.chat_turn is not None
    assert result.cognitive_outcome is None
    assert len(planner.calls) == 1
    assert len(guard.calls) == 1
    assert len(runtime.calls) == 1
    assert len(conversation.calls) == 1
    assert observer.outcomes == []


@pytest.mark.parametrize(
    "failure",
    (
        CognitiveFailureCode.TURN_IN_PROGRESS,
        CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
        CognitiveFailureCode.INVALID_COGNITION,
        CognitiveFailureCode.CONTRACT_VIOLATION,
    ),
)
def test_d178_cognitive_failure_keeps_existing_error_path_without_handoff(
    failure: CognitiveFailureCode,
) -> None:
    failed = d140._failed(failure)
    cognitive = d140._FakeCognitive(failure=failed)
    observer = d140._RecordingObserver()
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator(
        cognitive=cognitive,
        observer=observer,
    )

    result = orchestrator.process_chat(d140._command())

    assert result.response.result.status == "failed"
    assert result.chat_turn is None
    assert result.cognitive_outcome is None
    assert len(cognitive.calls) == 1
    assert planner.calls == []
    assert guard.calls == []
    assert runtime.calls == []
    assert conversation.calls == []
    assert len(observer.outcomes) == 1
    assert observer.outcomes[0]["outcome"] is failed


def test_d178_observer_failure_does_not_change_exact_handoff() -> None:
    brain = d136.outcome()
    cognitive = d140._FakeCognitive(outcome=brain)
    observer = d140._RecordingObserver(fail=True)
    orchestrator, planner, guard, runtime, conversation = d140._orchestrator(
        cognitive=cognitive,
        observer=observer,
    )

    result = orchestrator.process_chat(d140._command())

    assert result.response.result.status == "succeeded"
    assert result.cognitive_outcome is brain
    assert len(cognitive.calls) == 1
    assert planner.calls == []
    assert guard.calls == []
    assert runtime.calls == []
    assert conversation.calls == []


def test_d178_manual_outcome_default_remains_none_for_compatibility() -> None:
    orchestrator, *_ = d140._orchestrator()
    legacy = orchestrator.process_chat(d140._command())
    copied_shape = CommandOrchestrationOutcome(
        response=legacy.response,
        chat_turn=legacy.chat_turn,
    )
    assert copied_shape.cognitive_outcome is None


def test_d178_handoff_is_exact_cognitive_executive_outcome_type() -> None:
    brain = d136.outcome()
    cognitive = d140._FakeCognitive(outcome=brain)
    orchestrator, *_ = d140._orchestrator(cognitive=cognitive)

    result = orchestrator.process_chat(d140._command())

    assert isinstance(result.cognitive_outcome, CognitiveExecutiveOutcome)
    assert result.cognitive_outcome is brain
