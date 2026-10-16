from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_runtime_adoption import CognitiveRuntimeObservation
from app.contracts.cognitive_runtime_assurance import D141_COUNTER_MAX
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.core.config import Settings
from app.services.cognitive_runtime_assurance import CognitiveRuntimeAssurance
from app.services.runtime_diagnostics import RuntimeDiagnosticsService

FAILURES = (
    CognitiveFailureCode.TURN_IN_PROGRESS,
    CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
    CognitiveFailureCode.CONTEXT_UNSTABLE,
    CognitiveFailureCode.CRITIC_UNAVAILABLE,
    CognitiveFailureCode.STALE_LATE_RESULT,
    CognitiveFailureCode.INVALID_COGNITION,
    CognitiveFailureCode.CONTRACT_VIOLATION,
)


def _selection() -> CognitiveRuntimeObservation:
    return CognitiveRuntimeObservation(
        request_id="request-1",
        workspace_id=WorkspaceId.PERSONAL,
        selected_lane="cognitive",
        task_kind=AITaskKind.GENERAL_CHAT,
    )


def _failed(code: CognitiveFailureCode) -> CognitiveRuntimeObservation:
    return CognitiveRuntimeObservation(
        request_id="request-1",
        workspace_id=WorkspaceId.PERSONAL,
        selected_lane="cognitive",
        task_kind=AITaskKind.GENERAL_CHAT,
        terminal_state=CognitiveTurnState.FAILED,
        revision_count=0,
        invocation_count=0,
        draft_generation_count=0,
        failure_code=code,
        publication_disposition=None,
    )


def _diag(assurance: CognitiveRuntimeAssurance) -> RuntimeDiagnosticsService:
    return RuntimeDiagnosticsService(
        settings=Settings(oai_cognitive_runtime_enabled=True, _env_file=None),
        google_oauth_status_reader=None,  # type: ignore[arg-type]
        google_oauth_config_factory=lambda: SimpleNamespace(
            configuration_present=False
        ),
        cognitive_runtime_assurance=assurance,
    )


def run_case(case: int) -> None:
    if 1 <= case <= 16:
        first, second = CognitiveRuntimeAssurance(), CognitiveRuntimeAssurance()
        count = ((case - 1) % 5) + 1
        for _ in range(count):
            first.record_selection(_selection())
            second.record_selection(_selection())
        assert first.snapshot() == second.snapshot()
        assert repr(first.snapshot()) == repr(second.snapshot())
    elif 17 <= case <= 28:
        code = FAILURES[(case - 17) % len(FAILURES)]
        first, second = CognitiveRuntimeAssurance(), CognitiveRuntimeAssurance()
        for service in (first, second):
            service.record_selection(_selection())
            service.record_outcome(_failed(code))
        assert first.snapshot() == second.snapshot()
    elif 29 <= case <= 36:
        value = D141_COUNTER_MAX - ((case - 29) % 3)
        assert CognitiveRuntimeAssurance._saturating_increment(
            value
        ) == CognitiveRuntimeAssurance._saturating_increment(value)
    elif 37 <= case <= 42:
        first, second = CognitiveRuntimeAssurance(), CognitiveRuntimeAssurance()
        first.record_selection(_selection())
        second.record_selection(_selection())
        left = _diag(first).snapshot(database_revision="rev").model_dump()
        right = _diag(second).snapshot(database_revision="rev").model_dump()
        assert left == right
        assert left["cognitive_runtime"]["status"] == "observing"
    elif 43 <= case <= 48:
        service = CognitiveRuntimeAssurance()
        assert service.snapshot() == service.snapshot()
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d141_reproducibility_matrix(case: int) -> None:
    run_case(case)
