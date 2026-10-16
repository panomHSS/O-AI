from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest

from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveTurnState,
)
from app.contracts.cognitive_runtime_adoption import CognitiveRuntimeObservation
from app.contracts.response_composition import NormalizedError
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_runtime_observability import CognitiveRuntimeObserver
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer

from tests import test_d136_cognitive_executive as d136


CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")


class _CaptureLogger:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def info(self, _message, *, extra):
        self.payloads.append(dict(extra["cognitive_runtime"]))


_FAILURES = (
    CognitiveFailureCode.TURN_IN_PROGRESS,
    CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
    CognitiveFailureCode.CONTEXT_UNSTABLE,
    CognitiveFailureCode.CRITIC_UNAVAILABLE,
    CognitiveFailureCode.STALE_LATE_RESULT,
    CognitiveFailureCode.INVALID_COGNITION,
    CognitiveFailureCode.CONTRACT_VIOLATION,
)


def _failed(code: CognitiveFailureCode):
    return replace(
        d136.outcome(CognitiveTurnState.FAILED),
        failure_code=code,
    )


def _legacy_event(index: int) -> CognitiveRuntimeObservation:
    return CognitiveRuntimeObservation(
        request_id=f"request-{index}",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=str(CONVERSATION_ID),
        project_id=str(PROJECT_ID),
        selected_lane="legacy",
        task_kind=AITaskKind.GENERAL_CHAT,
    )


def run_case(case: int) -> None:
    if 1 <= case <= 16:
        index = ((case - 1) % 4) + 1
        first = _legacy_event(index)
        second = _legacy_event(index)
        assert first == second
        assert repr(first) == repr(second)
        assert first.contract_version == second.contract_version
    elif 17 <= case <= 30:
        failure = _FAILURES[(case - 17) % len(_FAILURES)]
        normalizer = OrchestrationErrorNormalizer()
        first = normalizer.normalize_cognitive_outcome(
            "request-1",
            _failed(failure),
        )
        second = normalizer.normalize_cognitive_outcome(
            "request-1",
            _failed(failure),
        )
        assert first == second
        assert first.code in {
            "COGNITIVE_RUNTIME_BUSY",
            "COGNITIVE_RUNTIME_UNAVAILABLE",
            "COGNITIVE_RESPONSE_BLOCKED",
        }
    elif 31 <= case <= 40:
        code = (
            "COGNITIVE_RUNTIME_BUSY",
            "COGNITIVE_RUNTIME_UNAVAILABLE",
            "COGNITIVE_RESPONSE_BLOCKED",
        )[(case - 31) % 3]
        composer = ResponseComposer()
        first = composer.compose_error(
            NormalizedError("request-1", code, "failed")  # type: ignore[arg-type]
        )
        second = composer.compose_error(
            NormalizedError("request-1", code, "failed")  # type: ignore[arg-type]
        )
        assert first == second
        assert first.result.error == second.result.error
        assert first.message == second.message
    elif 41 <= case <= 48:
        logger = _CaptureLogger()
        observer = CognitiveRuntimeObserver(
            workspace_id=WorkspaceId.PERSONAL,
            logger=logger,  # type: ignore[arg-type]
        )
        outcome = d136.outcome()
        assert observer.try_record_cognitive_outcome(
            request_id="request-1",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
            task_kind=AITaskKind.GENERAL_CHAT,
            outcome=outcome,
        )
        assert observer.try_record_cognitive_outcome(
            request_id="request-1",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
            task_kind=AITaskKind.GENERAL_CHAT,
            outcome=outcome,
        )
        assert logger.payloads[0] == logger.payloads[1]
        key = (
            "request_id",
            "workspace_id",
            "selected_lane",
            "task_kind",
            "terminal_state",
            "adapter_id",
            "model_id",
            "publication_disposition",
        )[case - 41]
        assert logger.payloads[0][key] == logger.payloads[1][key]
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d140_reproducibility_matrix(case: int) -> None:
    run_case(case)
