from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.contracts.cognitive_runtime_assurance import (
    D141_COUNTER_MAX,
    CognitiveRuntimeAssuranceSnapshot,
)
from app.schemas.diagnostics import CognitiveRuntimeReadinessDiagnostics
from app.services.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessEvaluator,
)
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


def _snap(
    *,
    completed: int = 0,
    insufficient: int = 0,
    failed: int = 0,
    runtime_busy: int = 0,
    runtime_unavailable: int = 0,
    response_blocked: int = 0,
    cognitive_selected: int | None = None,
) -> CognitiveRuntimeAssuranceSnapshot:
    terminal = completed + insufficient + failed
    return CognitiveRuntimeAssuranceSnapshot(
        cognitive_selected=(
            terminal if cognitive_selected is None else cognitive_selected
        ),
        completed=completed,
        insufficient=insufficient,
        failed=failed,
        runtime_busy=runtime_busy,
        runtime_unavailable=runtime_unavailable,
        response_blocked=response_blocked,
    )


class _ChangingAssurance:
    def __init__(self) -> None:
        self.calls = 0

    def snapshot(self) -> CognitiveRuntimeAssuranceSnapshot:
        self.calls += 1
        if self.calls == 1:
            return _snap(completed=99)
        return _snap(completed=100)


def _service(assurance: object) -> RuntimeDiagnosticsService:
    settings = SimpleNamespace(
        app_name="O-AI",
        environment="test",
        oai_cognitive_runtime_enabled=True,
        oai_google_calendar_connector_enabled=False,
        oai_gmail_connector_enabled=False,
        oai_cross_connector_ai_context_enabled=False,
        oai_automation_enabled=False,
    )
    return RuntimeDiagnosticsService(
        settings=settings,  # type: ignore[arg-type]
        google_oauth_status_reader=None,  # type: ignore[arg-type]
        google_oauth_config_factory=lambda: SimpleNamespace(
            configuration_present=False
        ),  # type: ignore[arg-type]
        cognitive_runtime_assurance=assurance,  # type: ignore[arg-type]
    )


def run_case(case: int) -> None:
    if 1 <= case <= 12:
        count = ((case - 1) % 6) * 20
        snapshot = _snap(
            completed=count,
            cognitive_selected=count,
        )
        first = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        )
        second = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        )
        assert first == second
        assert repr(first) == repr(second)

    elif 13 <= case <= 20:
        numerator, denominator = (
            (0, 100),
            (1, 100),
            (2, 100),
            (50, 100),
            (99, 100),
            (1, 10_000),
            (50, 10_000),
            (9_999, 10_000),
        )[case - 13]
        first = CognitiveRuntimeReadinessEvaluator._rate_bps(
            numerator=numerator,
            denominator=denominator,
        )
        second = CognitiveRuntimeReadinessEvaluator._rate_bps(
            numerator=numerator,
            denominator=denominator,
        )
        assert first == second
        assert type(first) is int

    elif 21 <= case <= 28:
        vectors = (
            _snap(completed=99),
            _snap(completed=100),
            _snap(completed=101),
            _snap(completed=99, failed=1),
            _snap(completed=98, failed=2),
            _snap(completed=9_950, failed=50, runtime_unavailable=50),
            _snap(completed=9_949, failed=51, runtime_unavailable=51),
            _snap(completed=1, insufficient=99),
        )
        snapshot = vectors[case - 21]
        first = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        )
        second = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        )
        assert first == second

    elif 29 <= case <= 36:
        denominator = D141_COUNTER_MAX
        numerators = (
            0,
            1,
            2,
            denominator // 100,
            denominator // 2,
            denominator - 2,
            denominator - 1,
            denominator,
        )
        numerator = numerators[case - 29]
        first = CognitiveRuntimeReadinessEvaluator._rate_bps(
            numerator=numerator,
            denominator=denominator,
        )
        second = CognitiveRuntimeReadinessEvaluator._rate_bps(
            numerator=numerator,
            denominator=denominator,
        )
        assert first == second
        assert 0 <= first <= 10_000

    elif 37 <= case <= 42:
        snapshot = _snap(
            completed=99,
            failed=1,
            runtime_busy=(case - 37) % 2,
        )
        assessment = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        )
        model = CognitiveRuntimeReadinessDiagnostics(
            status=assessment.status,
            reference_baseline=assessment.reference_baseline,
            sample_scope=assessment.sample_scope,
            reset_on_restart=assessment.reset_on_restart,
            terminal_samples=assessment.terminal_samples,
            failed_rate_bps=assessment.failed_rate_bps,
            insufficient_rate_bps=assessment.insufficient_rate_bps,
            runtime_busy_rate_bps=assessment.runtime_busy_rate_bps,
            runtime_unavailable_rate_bps=assessment.runtime_unavailable_rate_bps,
            response_blocked_rate_bps=assessment.response_blocked_rate_bps,
        )
        assert model.model_dump() == model.model_dump()
        assert model.model_dump_json() == model.model_dump_json()

    elif 43 <= case <= 48:
        assurance = _ChangingAssurance()
        snapshot = _service(assurance).snapshot(database_revision=f"r{case}")
        assert assurance.calls == 1
        assert snapshot.cognitive_runtime.completed == 99
        assert snapshot.cognitive_runtime_readiness.terminal_samples == 99
        assert snapshot.cognitive_runtime_readiness.status == "collecting"

    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d142_reproducibility_matrix(case: int) -> None:
    run_case(case)
