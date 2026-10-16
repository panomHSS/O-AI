from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.contracts.cognitive_runtime_assurance import (
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_runtime_promotion_advisory import (
    D143_REFERENCE_BASELINE,
    CognitiveRuntimePromotionAdvisory,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.schemas.diagnostics import (
    CognitiveRuntimePromotionAdvisoryDiagnostics,
)
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)
from app.services.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessEvaluator,
)
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


VALID = {
    "disabled": ("no_action", "runtime_disabled", False),
    "collecting": ("hold_for_evidence", "insufficient_evidence", False),
    "ready": (
        "eligible_for_promotion",
        "readiness_thresholds_satisfied",
        True,
    ),
    "degraded": ("rollback_review", "readiness_degraded", True),
    "unavailable": ("fail_closed", "readiness_unavailable", False),
}
AUTHORITY_FIELDS = (
    "promotion_authority",
    "rollback_authority",
    "execution_authority",
    "routing_authority",
    "configuration_authority",
    "automatic_promotion",
    "automatic_rollback",
)


def _assessment(status: str, **overrides: object) -> CognitiveRuntimeReadinessAssessment:
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
    kwargs.update(overrides)
    return CognitiveRuntimeReadinessAssessment(**kwargs)  # type: ignore[arg-type]


def _corrupt(
    field: str,
    value: object,
    *,
    status: str = "ready",
) -> CognitiveRuntimeReadinessAssessment:
    item = _assessment(status)
    object.__setattr__(item, field, value)
    return item


def _evaluate(readiness: object | None) -> CognitiveRuntimePromotionAdvisory:
    return CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
        readiness=readiness
    )


class _Assurance:
    def __init__(self) -> None:
        self.calls = 0

    def snapshot(self) -> CognitiveRuntimeAssuranceSnapshot:
        self.calls += 1
        return CognitiveRuntimeAssuranceSnapshot(
            cognitive_selected=100,
            completed=100,
        )


def _runtime_service(assurance: _Assurance) -> RuntimeDiagnosticsService:
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


def _integration_proof() -> None:
    assurance = _Assurance()
    readiness_results: list[CognitiveRuntimeReadinessAssessment] = []
    promotion_inputs: list[object] = []
    original_readiness = CognitiveRuntimeReadinessEvaluator.evaluate
    original_promotion = CognitiveRuntimePromotionGovernanceEvaluator.evaluate

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
        result = _runtime_service(assurance).snapshot(database_revision="d143")

    assert assurance.calls == 1
    assert readiness_mock.call_count == 1
    assert promotion_mock.call_count == 1
    assert len(readiness_results) == 1
    assert promotion_inputs == [readiness_results[0]]
    assert result.cognitive_runtime_readiness.status == "ready"
    assert (
        result.cognitive_runtime_promotion_advisory.recommendation
        == "eligible_for_promotion"
    )


def run_case(case: int) -> None:
    if 1 <= case <= 5:
        status = tuple(VALID)[case - 1]
        result = _evaluate(_assessment(status))
        assert result.recommendation == VALID[status][0]

    elif 6 <= case <= 10:
        status = tuple(VALID)[case - 6]
        result = _evaluate(_assessment(status))
        assert result.reason_code == VALID[status][1]

    elif 11 <= case <= 15:
        status = tuple(VALID)[case - 11]
        result = _evaluate(_assessment(status))
        assert result.owner_decision_required is VALID[status][2]

    elif 16 <= case <= 22:
        name = AUTHORITY_FIELDS[case - 16]
        result = _evaluate(_assessment("ready"))
        assert getattr(result, name) is False

    elif 23 <= case <= 27:
        status = tuple(VALID)[case - 23]
        result = _evaluate(_assessment(status))
        assert result.source_readiness_status == status

    elif case == 28:
        assert _evaluate(None).source_readiness_status is None

    elif 29 <= case <= 36:
        invalid = (
            None,
            object(),
            True,
            1,
            "ready",
            ["ready"],
            {"status": "ready"},
            CognitiveRuntimePromotionGovernanceEvaluator,
        )[case - 29]
        result = _evaluate(invalid)
        assert result.recommendation == "fail_closed"
        assert result.reason_code == "invalid_readiness_evidence"

    elif 37 <= case <= 45:
        field, value = (
            ("reference_baseline", "wrong"),
            ("sample_scope", "wrong"),
            ("reset_on_restart", False),
            ("execution_authority", True),
            ("routing_authority", True),
            ("promotion_authority", True),
            ("rollback_authority", True),
            ("automatic_promotion", True),
            ("automatic_rollback", True),
        )[case - 37]
        result = _evaluate(_corrupt(field, value))
        assert result.recommendation == "fail_closed"
        assert result.reason_code == "invalid_readiness_evidence"

    elif 46 <= case <= 50:
        variations = (
            {"terminal_samples": 0, "failed_rate_bps": None},
            {"terminal_samples": 100, "failed_rate_bps": 10_000},
            {"terminal_samples": 9_223_372_036_854_775_807},
            {"insufficient_rate_bps": 9_999},
            {"response_blocked_rate_bps": 10_000},
        )
        result = _evaluate(_assessment("ready", **variations[case - 46]))
        assert result.recommendation == "eligible_for_promotion"
        assert result.reason_code == "readiness_thresholds_satisfied"

    elif 51 <= case <= 55:
        readiness: object | None = (
            None,
            object(),
            _corrupt("status", "unknown"),
            _assessment("unavailable"),
            _corrupt("reference_baseline", "bad", status="collecting"),
        )[case - 51]
        result = _evaluate(readiness)
        assert result.recommendation == "fail_closed"
        assert result.owner_decision_required is False
        assert all(getattr(result, name) is False for name in AUTHORITY_FIELDS)

    elif case == 56:
        advisory = _evaluate(_assessment("ready"))
        with pytest.raises(FrozenInstanceError):
            advisory.recommendation = "no_action"  # type: ignore[misc]

    elif case == 57:
        with pytest.raises(ValueError, match="combination_invalid"):
            CognitiveRuntimePromotionAdvisory(
                recommendation="eligible_for_promotion",
                reason_code="runtime_disabled",
                source_readiness_status="ready",
                owner_decision_required=True,
            )

    elif case == 58:
        with pytest.raises(ValueError, match="baseline_invalid"):
            CognitiveRuntimePromotionAdvisory(
                recommendation="no_action",
                reason_code="runtime_disabled",
                source_readiness_status="disabled",
                owner_decision_required=False,
                reference_baseline="wrong",
            )

    elif case == 59:
        with pytest.raises(ValueError, match="owner_decision_invalid"):
            CognitiveRuntimePromotionAdvisory(
                recommendation="no_action",
                reason_code="runtime_disabled",
                source_readiness_status="disabled",
                owner_decision_required=1,  # type: ignore[arg-type]
            )

    elif case == 60:
        with pytest.raises(ValueError, match="promotion_authority_invalid"):
            CognitiveRuntimePromotionAdvisory(
                recommendation="no_action",
                reason_code="runtime_disabled",
                source_readiness_status="disabled",
                owner_decision_required=False,
                promotion_authority=True,  # type: ignore[arg-type]
            )

    elif case == 61:
        model = CognitiveRuntimePromotionAdvisoryDiagnostics(
            recommendation="eligible_for_promotion",
            reason_code="readiness_thresholds_satisfied",
            source_readiness_status="ready",
            owner_decision_required=True,
        )
        assert model.reference_baseline == D143_REFERENCE_BASELINE

    elif case == 62:
        model = CognitiveRuntimePromotionAdvisoryDiagnostics(
            recommendation="fail_closed",
            reason_code="invalid_readiness_evidence",
            source_readiness_status=None,
            owner_decision_required=False,
        )
        assert model.model_dump()["source_readiness_status"] is None

    elif case == 63:
        with pytest.raises(ValidationError):
            CognitiveRuntimePromotionAdvisoryDiagnostics(
                recommendation="promote",  # type: ignore[arg-type]
                reason_code="readiness_thresholds_satisfied",
                source_readiness_status="ready",
                owner_decision_required=True,
            )

    elif case == 64:
        with pytest.raises(ValidationError):
            CognitiveRuntimePromotionAdvisoryDiagnostics(
                recommendation="no_action",
                reason_code="free_text",  # type: ignore[arg-type]
                source_readiness_status="disabled",
                owner_decision_required=False,
            )

    elif case == 65:
        with pytest.raises(ValidationError):
            CognitiveRuntimePromotionAdvisoryDiagnostics(
                recommendation="no_action",
                reason_code="runtime_disabled",
                source_readiness_status="disabled",
                owner_decision_required=False,
                promotion_authority=True,  # type: ignore[arg-type]
            )

    elif case == 66:
        with pytest.raises(ValidationError):
            CognitiveRuntimePromotionAdvisoryDiagnostics(
                recommendation="no_action",
                reason_code="runtime_disabled",
                source_readiness_status="disabled",
                owner_decision_required=1,  # type: ignore[arg-type]
            )

    elif 67 <= case <= 72:
        _integration_proof()

    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    range(1, 73),
    ids=[f"F{i:02d}" for i in range(1, 73)],
)
def test_d143_functional_matrix(case: int) -> None:
    run_case(case)
