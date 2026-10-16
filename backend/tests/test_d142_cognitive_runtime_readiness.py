from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.contracts.cognitive_runtime_assurance import (
    D141_COUNTER_MAX,
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_runtime_readiness import (
    D142_MAX_FAILED_RATE_BPS,
    D142_MAX_RESPONSE_BLOCKED_RATE_BPS,
    D142_MAX_RUNTIME_BUSY_RATE_BPS,
    D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS,
    D142_MIN_TERMINAL_SAMPLES,
    D142_RATE_SCALE_BPS,
    D142_REFERENCE_BASELINE,
    CognitiveRuntimeReadinessAssessment,
)
from app.schemas.diagnostics import RuntimeDiagnosticsResponse
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
    selected = terminal if cognitive_selected is None else cognitive_selected
    return CognitiveRuntimeAssuranceSnapshot(
        cognitive_selected=selected,
        completed=completed,
        insufficient=insufficient,
        failed=failed,
        runtime_busy=runtime_busy,
        runtime_unavailable=runtime_unavailable,
        response_blocked=response_blocked,
    )


class _CountingAssurance:
    def __init__(self, snapshot: CognitiveRuntimeAssuranceSnapshot) -> None:
        self.value = snapshot
        self.calls = 0

    def snapshot(self) -> CognitiveRuntimeAssuranceSnapshot:
        self.calls += 1
        return self.value


def _diagnostics(
    *,
    enabled: bool,
    snapshot: CognitiveRuntimeAssuranceSnapshot,
) -> tuple[RuntimeDiagnosticsResponse, _CountingAssurance]:
    assurance = _CountingAssurance(snapshot)
    settings = SimpleNamespace(
        app_name="O-AI",
        environment="test",
        oai_cognitive_runtime_enabled=enabled,
        oai_google_calendar_connector_enabled=False,
        oai_gmail_connector_enabled=False,
        oai_cross_connector_ai_context_enabled=False,
        oai_automation_enabled=False,
    )
    service = RuntimeDiagnosticsService(
        settings=settings,  # type: ignore[arg-type]
        google_oauth_status_reader=None,  # type: ignore[arg-type]
        google_oauth_config_factory=lambda: SimpleNamespace(
            configuration_present=False
        ),  # type: ignore[arg-type]
        cognitive_runtime_assurance=assurance,  # type: ignore[arg-type]
    )
    return service.snapshot(database_revision="d142-test"), assurance


def run_case(case: int) -> None:
    if 1 <= case <= 8:
        if case == 1:
            assert D142_REFERENCE_BASELINE == "6f8e803da9e77d43e1eeb06a8ae3d5e69fb80299"
        elif case == 2:
            assert D142_MIN_TERMINAL_SAMPLES == 100
        elif case == 3:
            assert D142_MAX_FAILED_RATE_BPS == 100
        elif case == 4:
            assert D142_MAX_RUNTIME_BUSY_RATE_BPS == 100
        elif case == 5:
            assert D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS == 50
        elif case == 6:
            assert D142_MAX_RESPONSE_BLOCKED_RATE_BPS == 100
        elif case == 7:
            assert D142_RATE_SCALE_BPS == 10_000
        else:
            allowed = {"disabled", "collecting", "ready", "degraded", "unavailable"}
            for status in allowed:
                assert CognitiveRuntimeReadinessAssessment(status=status).status == status

    elif 9 <= case <= 16:
        vectors = (
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (33, 33, 34),
            (98, 1, 1),
            (100, 0, 0),
            (D141_COUNTER_MAX, 0, 0),
        )
        completed, insufficient, failed = vectors[case - 9]
        result = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=_snap(
                completed=completed,
                insufficient=insufficient,
                failed=failed,
            ),
        )
        assert result.terminal_samples == completed + insufficient + failed

    elif 17 <= case <= 28:
        vectors = (
            (0, 100, 0),
            (1, 100, 100),
            (1, 200, 50),
            (50, 100, 5000),
            (99, 100, 9900),
            (1, 10_000, 1),
            (50, 10_000, 50),
            (51, 10_000, 51),
            (100, 10_000, 100),
            (101, 10_000, 101),
            (D141_COUNTER_MAX, D141_COUNTER_MAX, 10_000),
            (D141_COUNTER_MAX - 1, D141_COUNTER_MAX, 9_999),
        )
        numerator, denominator, expected = vectors[case - 17]
        actual = CognitiveRuntimeReadinessEvaluator._rate_bps(
            numerator=numerator,
            denominator=denominator,
        )
        assert actual == expected
        assert isinstance(actual, int)

    elif 29 <= case <= 40:
        vectors = (
            (False, None, "disabled"),
            (False, _snap(), "disabled"),
            (True, None, "unavailable"),
            (True, object(), "unavailable"),
            (True, _snap(), "collecting"),
            (True, _snap(completed=99), "collecting"),
            (True, _snap(completed=100), "ready"),
            (True, _snap(completed=99, failed=1), "ready"),
            (True, _snap(completed=98, failed=2), "degraded"),
            (True, _snap(completed=1, insufficient=99), "ready"),
            (
                True,
                _snap(
                    completed=9_950,
                    failed=50,
                    runtime_unavailable=50,
                ),
                "ready",
            ),
            (
                True,
                _snap(
                    completed=9_949,
                    failed=51,
                    runtime_unavailable=51,
                ),
                "degraded",
            ),
        )
        enabled, snapshot, expected = vectors[case - 29]
        result = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=enabled,
            snapshot=snapshot,
        )
        assert result.status == expected

    elif 41 <= case <= 52:
        vectors = (
            (_snap(completed=99, failed=1), "ready"),
            (_snap(completed=98, failed=2), "degraded"),
            (_snap(completed=9_900, failed=100), "ready"),
            (_snap(completed=9_899, failed=101), "degraded"),
            (
                _snap(completed=9_900, failed=100, runtime_busy=100),
                "ready",
            ),
            (
                _snap(completed=9_899, failed=101, runtime_busy=101),
                "degraded",
            ),
            (
                _snap(completed=9_950, failed=50, runtime_unavailable=50),
                "ready",
            ),
            (
                _snap(completed=9_949, failed=51, runtime_unavailable=51),
                "degraded",
            ),
            (
                _snap(completed=9_900, failed=100, response_blocked=100),
                "ready",
            ),
            (
                _snap(completed=9_899, failed=101, response_blocked=101),
                "degraded",
            ),
            (_snap(completed=100), "ready"),
            (_snap(completed=99), "collecting"),
        )
        snapshot, expected = vectors[case - 41]
        assert CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=snapshot,
        ).status == expected

    elif 53 <= case <= 60:
        insufficient = (1, 25, 50, 75, 90, 98, 99, 100)[case - 53]
        completed = 100 - insufficient
        result = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=True,
            snapshot=_snap(completed=completed, insufficient=insufficient),
        )
        assert result.status == "ready"
        assert result.insufficient_rate_bps == insufficient * 100
        assert result.failed_rate_bps == 0

    elif 61 <= case <= 68:
        if case == 61:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=False,
                snapshot=_snap(completed=100),
            )
            assert result.status == "disabled" and result.terminal_samples == 100
        elif case == 62:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=False,
                snapshot=None,
            )
            assert result.status == "disabled" and result.terminal_samples is None
        elif case == 63:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=None,
            )
            assert result.status == "unavailable" and result.terminal_samples is None
        elif case == 64:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=SimpleNamespace(),
            )
            assert result.status == "unavailable"
        elif case == 65:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(completed=1, runtime_busy=2, cognitive_selected=2),
            )
            assert result.status == "unavailable"
        elif case == 66:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=False,
                snapshot=_snap(completed=1, runtime_busy=2, cognitive_selected=2),
            )
            assert result.status == "disabled" and result.terminal_samples is None
        elif case == 67:
            result = CognitiveRuntimeReadinessEvaluator.evaluate(
                enabled=True,
                snapshot=_snap(completed=0, cognitive_selected=1),
            )
            assert result.status == "collecting"
            assert result.failed_rate_bps is None
        else:
            with pytest.raises(ValueError, match="enabled_invalid"):
                CognitiveRuntimeReadinessEvaluator.evaluate(
                    enabled=1,  # type: ignore[arg-type]
                    snapshot=_snap(),
                )

    elif 69 <= case <= 72:
        if case == 69:
            assert RuntimeDiagnosticsResponse.model_fields[
                "contract_version"
            ].default == "1"
            assert RuntimeDiagnosticsResponse.model_fields[
                "cognitive_runtime_readiness"
            ].is_required()
        else:
            snapshot, assurance = _diagnostics(
                enabled=True,
                snapshot=_snap(completed=100),
            )
            if case == 70:
                assert assurance.calls == 1
            elif case == 71:
                assert snapshot.cognitive_runtime_readiness.status == "ready"
                assert snapshot.cognitive_runtime_readiness.terminal_samples == 100
            else:
                assert snapshot.cognitive_runtime.completed == 100
                assert snapshot.cognitive_runtime_readiness.terminal_samples == 100
                assert snapshot.cognitive_runtime.execution_authority is False
                assert (
                    snapshot.cognitive_runtime_readiness.execution_authority
                    is False
                )

    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 73),
    ids=[f"F{i:02d}" for i in range(1, 73)],
)
def test_d142_functional_matrix(case: int) -> None:
    run_case(case)
