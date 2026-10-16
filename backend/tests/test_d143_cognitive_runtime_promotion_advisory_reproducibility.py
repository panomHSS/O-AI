from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.contracts.cognitive_runtime_assurance import (
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionAdvisory,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.schemas.diagnostics import CognitiveRuntimePromotionAdvisoryDiagnostics
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)
from app.services.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessEvaluator,
)
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


STATUSES = ("disabled", "collecting", "ready", "degraded", "unavailable")


def _assessment(status: str) -> CognitiveRuntimeReadinessAssessment:
    kwargs: dict[str, object] = {"status": status}
    if status != "unavailable":
        kwargs.update(
            terminal_samples=100,
            failed_rate_bps=0,
            insufficient_rate_bps=0,
            runtime_busy_rate_bps=0,
            runtime_unavailable_rate_bps=0,
            response_blocked_rate_bps=0,
        )
    return CognitiveRuntimeReadinessAssessment(**kwargs)  # type: ignore[arg-type]


def _evaluate(
    readiness: CognitiveRuntimeReadinessAssessment,
) -> CognitiveRuntimePromotionAdvisory:
    return CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
        readiness=readiness
    )


class _ChangingAssurance:
    def __init__(self) -> None:
        self.calls = 0

    def snapshot(self) -> CognitiveRuntimeAssuranceSnapshot:
        self.calls += 1
        if self.calls == 1:
            return CognitiveRuntimeAssuranceSnapshot(
                cognitive_selected=99,
                completed=99,
            )
        return CognitiveRuntimeAssuranceSnapshot(
            cognitive_selected=100,
            completed=100,
        )


def _service(assurance: _ChangingAssurance) -> RuntimeDiagnosticsService:
    settings = SimpleNamespace(
        app_name="O-AI",
        environment="test",
        oai_cognitive_runtime_enabled=True,
        oai_google_calendar_connector_enabled=False,
        oai_gmail_connector_enabled=False,
        oai_gmail_send_enabled=False,
        oai_cross_connector_ai_context_enabled=False,
        oai_automation_enabled=False,
    )
    return RuntimeDiagnosticsService(
        settings=settings,  # type: ignore[arg-type]
        google_oauth_status_reader=object(),  # type: ignore[arg-type]
        google_oauth_config_factory=lambda: SimpleNamespace(
            configuration_present=False
        ),  # type: ignore[arg-type]
        cognitive_runtime_assurance=assurance,  # type: ignore[arg-type]
    )


def run_case(case: int) -> None:
    if 1 <= case <= 12:
        status = STATUSES[(case - 1) % len(STATUSES)]
        source = _assessment(status)
        first = _evaluate(source)
        second = _evaluate(source)
        assert first == second
        assert repr(first) == repr(second)

    elif 13 <= case <= 24:
        status = STATUSES[(case - 13) % len(STATUSES)]
        source = _assessment(status)
        before = repr(source)
        first = _evaluate(source)
        second = _evaluate(source)
        assert first == second
        assert repr(source) == before

    elif 25 <= case <= 36:
        first_evaluator = CognitiveRuntimePromotionGovernanceEvaluator()
        second_evaluator = CognitiveRuntimePromotionGovernanceEvaluator()
        order = STATUSES if case % 2 else tuple(reversed(STATUSES))
        first = [
            first_evaluator.evaluate(readiness=_assessment(status))
            for status in order
        ]
        second = [
            second_evaluator.evaluate(readiness=_assessment(status))
            for status in order
        ]
        assert first == second
        assert vars(first_evaluator) == {}
        assert vars(second_evaluator) == {}

    elif 37 <= case <= 42:
        advisory = _evaluate(_assessment("ready"))
        first = CognitiveRuntimePromotionAdvisoryDiagnostics(
            recommendation=advisory.recommendation,
            reason_code=advisory.reason_code,
            source_readiness_status=advisory.source_readiness_status,
            owner_decision_required=advisory.owner_decision_required,
        )
        second = CognitiveRuntimePromotionAdvisoryDiagnostics(
            recommendation=advisory.recommendation,
            reason_code=advisory.reason_code,
            source_readiness_status=advisory.source_readiness_status,
            owner_decision_required=advisory.owner_decision_required,
        )
        assert first.model_dump() == second.model_dump()
        assert first.model_dump_json() == second.model_dump_json()

    elif 43 <= case <= 48:
        assurance = _ChangingAssurance()
        readiness_results: list[CognitiveRuntimeReadinessAssessment] = []
        promotion_inputs: list[object] = []
        original_readiness = CognitiveRuntimeReadinessEvaluator.evaluate
        original_promotion = (
            CognitiveRuntimePromotionGovernanceEvaluator.evaluate
        )

        def readiness_side_effect(**kwargs: object) -> CognitiveRuntimeReadinessAssessment:
            result = original_readiness(**kwargs)  # type: ignore[arg-type]
            readiness_results.append(result)
            return result

        def promotion_side_effect(**kwargs: object) -> CognitiveRuntimePromotionAdvisory:
            promotion_inputs.append(kwargs["readiness"])
            return original_promotion(**kwargs)

        with patch.object(
            CognitiveRuntimeReadinessEvaluator,
            "evaluate",
            side_effect=readiness_side_effect,
        ) as readiness_mock, patch.object(
            CognitiveRuntimePromotionGovernanceEvaluator,
            "evaluate",
            side_effect=promotion_side_effect,
        ) as promotion_mock:
            snapshot = _service(assurance).snapshot(
                database_revision=f"r{case}"
            )

        assert assurance.calls == 1
        assert readiness_mock.call_count == 1
        assert promotion_mock.call_count == 1
        assert promotion_inputs == [readiness_results[0]]
        assert snapshot.cognitive_runtime.completed == 99
        assert snapshot.cognitive_runtime_readiness.terminal_samples == 99
        assert snapshot.cognitive_runtime_readiness.status == "collecting"
        assert (
            snapshot.cognitive_runtime_promotion_advisory.recommendation
            == "hold_for_evidence"
        )
        assert (
            snapshot.cognitive_runtime_promotion_advisory.source_readiness_status
            == "collecting"
        )

    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d143_reproducibility_matrix(case: int) -> None:
    run_case(case)
