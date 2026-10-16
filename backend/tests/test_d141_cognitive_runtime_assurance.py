from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_runtime_adoption import CognitiveRuntimeObservation
from app.contracts.cognitive_runtime_assurance import (
    D141_COUNTER_MAX,
    D141_REFERENCE_BASELINE,
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.core.config import Settings
from app.services.cognitive_runtime_assurance import CognitiveRuntimeAssurance
from app.services.cognitive_runtime_observability import CognitiveRuntimeObserver
from app.services.runtime_diagnostics import RuntimeDiagnosticsService

ROOT = Path(__file__).resolve().parents[2]
CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
FAILURES = (
    CognitiveFailureCode.TURN_IN_PROGRESS,
    CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
    CognitiveFailureCode.CONTEXT_UNSTABLE,
    CognitiveFailureCode.CRITIC_UNAVAILABLE,
    CognitiveFailureCode.STALE_LATE_RESULT,
    CognitiveFailureCode.INVALID_COGNITION,
    CognitiveFailureCode.CONTRACT_VIOLATION,
)


def _selection(lane: str = "cognitive") -> CognitiveRuntimeObservation:
    return CognitiveRuntimeObservation(
        request_id="request-1",
        workspace_id=WorkspaceId.PERSONAL,
        selected_lane=lane,  # type: ignore[arg-type]
        task_kind=AITaskKind.GENERAL_CHAT,
    )


def _terminal(
    state: CognitiveTurnState,
    failure: CognitiveFailureCode | None = None,
) -> CognitiveRuntimeObservation:
    publication = {
        CognitiveTurnState.COMPLETED: "eligible",
        CognitiveTurnState.INSUFFICIENT: "bounded_insufficiency_only",
        CognitiveTurnState.FAILED: None,
    }[state]
    if state is CognitiveTurnState.INSUFFICIENT:
        failure = CognitiveFailureCode.INSUFFICIENT_EVIDENCE
    return CognitiveRuntimeObservation(
        request_id="request-1",
        workspace_id=WorkspaceId.PERSONAL,
        selected_lane="cognitive",
        task_kind=AITaskKind.GENERAL_CHAT,
        terminal_state=state,
        revision_count=0,
        invocation_count=0,
        draft_generation_count=0,
        failure_code=failure,
        publication_disposition=publication,  # type: ignore[arg-type]
    )


class _Logger:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def info(self, *_args, **_kwargs) -> None:
        self.calls += 1
        if self.fail:
            raise RuntimeError("logger unavailable")


class _Assurance:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.selection_calls = 0

    def record_selection(self, _event) -> None:
        self.selection_calls += 1
        if self.fail:
            raise RuntimeError("assurance unavailable")

    def record_outcome(self, _event) -> None:
        if self.fail:
            raise RuntimeError("assurance unavailable")


class _UnavailableAssurance:
    def snapshot(self):
        raise RuntimeError("assurance unavailable")


def _settings(enabled: bool) -> Settings:
    return Settings(oai_cognitive_runtime_enabled=enabled, _env_file=None)


def _diagnostics(enabled: bool, assurance) -> RuntimeDiagnosticsService:
    return RuntimeDiagnosticsService(
        settings=_settings(enabled),
        google_oauth_status_reader=None,  # type: ignore[arg-type]
        google_oauth_config_factory=lambda: SimpleNamespace(
            configuration_present=False
        ),
        cognitive_runtime_assurance=assurance,
    )


def run_case(case: int) -> None:
    if 1 <= case <= 8:
        snap = CognitiveRuntimeAssuranceSnapshot()
        names = (
            "cognitive_selected", "legacy_selected", "completed", "insufficient",
            "failed", "runtime_busy", "runtime_unavailable", "response_blocked",
        )
        assert getattr(snap, names[case - 1]) == 0
        assert snap.reference_baseline == D141_REFERENCE_BASELINE
    elif 9 <= case <= 16:
        service = CognitiveRuntimeAssurance()
        count = ((case - 9) % 4) + 1
        lane = "cognitive" if case % 2 else "legacy"
        for _ in range(count):
            service.record_selection(_selection(lane))
        assert getattr(service.snapshot(), f"{lane}_selected") == count
    elif 17 <= case <= 24:
        service = CognitiveRuntimeAssurance()
        service.record_selection(_selection())
        service.record_outcome(_terminal(CognitiveTurnState.COMPLETED))
        snap = service.snapshot()
        assert (snap.completed, snap.insufficient, snap.failed) == (1, 0, 0)
    elif 25 <= case <= 32:
        service = CognitiveRuntimeAssurance()
        service.record_selection(_selection())
        service.record_outcome(_terminal(CognitiveTurnState.INSUFFICIENT))
        snap = service.snapshot()
        assert (snap.completed, snap.insufficient, snap.failed) == (0, 1, 0)
    elif 33 <= case <= 40:
        failure = FAILURES[(case - 33) % len(FAILURES)]
        service = CognitiveRuntimeAssurance()
        service.record_selection(_selection())
        service.record_outcome(_terminal(CognitiveTurnState.FAILED, failure))
        snap = service.snapshot()
        expected = {
            CognitiveFailureCode.TURN_IN_PROGRESS: "runtime_busy",
            CognitiveFailureCode.TURN_DEADLINE_EXCEEDED: "runtime_unavailable",
            CognitiveFailureCode.CONTEXT_UNSTABLE: "runtime_unavailable",
            CognitiveFailureCode.CRITIC_UNAVAILABLE: "runtime_unavailable",
            CognitiveFailureCode.STALE_LATE_RESULT: "runtime_unavailable",
            CognitiveFailureCode.INVALID_COGNITION: "response_blocked",
            CognitiveFailureCode.CONTRACT_VIOLATION: "response_blocked",
        }[failure]
        assert snap.failed == 1 and getattr(snap, expected) == 1
    elif 41 <= case <= 48:
        assert CognitiveRuntimeAssurance._saturating_increment(
            D141_COUNTER_MAX
        ) == D141_COUNTER_MAX
        assert CognitiveRuntimeAssurance._saturating_increment(
            D141_COUNTER_MAX - 1
        ) == D141_COUNTER_MAX
    elif 49 <= case <= 56:
        logger_fail = bool(case & 1)
        assurance_fail = bool(case & 2)
        logger = _Logger(logger_fail)
        assurance = _Assurance(assurance_fail)
        observer = CognitiveRuntimeObserver(
            workspace_id=WorkspaceId.PERSONAL,
            logger=logger,  # type: ignore[arg-type]
            assurance=assurance,  # type: ignore[arg-type]
        )
        ok = observer.try_record_selection(
            request_id="request-1",
            conversation_id=CONVERSATION_ID,
            project_id=PROJECT_ID,
            selected_lane="cognitive",
            task_kind=AITaskKind.GENERAL_CHAT,
        )
        assert logger.calls == 1
        assert assurance.selection_calls == 1
        assert ok is (not logger_fail and not assurance_fail)
    elif 57 <= case <= 64:
        mode = (case - 57) % 4
        if mode == 0:
            item = _diagnostics(
                False, CognitiveRuntimeAssurance()
            ).snapshot(database_revision="rev").cognitive_runtime
            assert item.status == "disabled" and item.cognitive_selected == 0
        elif mode == 1:
            item = _diagnostics(
                True, CognitiveRuntimeAssurance()
            ).snapshot(database_revision="rev").cognitive_runtime
            assert item.status == "idle" and item.cognitive_selected == 0
        elif mode == 2:
            assurance = CognitiveRuntimeAssurance()
            assurance.record_selection(_selection())
            item = _diagnostics(
                True, assurance
            ).snapshot(database_revision="rev").cognitive_runtime
            assert item.status == "observing" and item.cognitive_selected == 1
        else:
            item = _diagnostics(
                True, _UnavailableAssurance()
            ).snapshot(database_revision="rev").cognitive_runtime
            assert item.status == "unavailable"
            assert item.cognitive_selected is None and item.failed is None
    elif 65 <= case <= 72:
        text = (ROOT / "backend/app/api/dependencies.py").read_text(encoding="utf-8")
        checks = (
            "def get_cognitive_runtime_assurance(",
            "get_cognitive_runtime_assurance()",
            "cognitive_runtime_assurance=",
            "settings.oai_cognitive_runtime_enabled",
            "get_conversation_service not in request.app.dependency_overrides",
            "def get_cognitive_runtime_observer(",
            "RuntimeDiagnosticsService(",
            "CognitiveRuntimeObserver(",
        )
        assert checks[case - 65] in text
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 73), ids=[f"F{i:02d}" for i in range(1, 73)])
def test_d141_functional_matrix(case: int) -> None:
    run_case(case)
