from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_runtime_incident_governance import (
    D145_REFERENCE_BASELINE,
    CognitiveRuntimeIncidentAssessment,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.contracts.cognitive_runtime_rollout import D144_STAGE_BPS
from app.schemas.diagnostics import (
    CognitiveRuntimeIncidentGovernanceDiagnostics,
    CognitiveRuntimeRolloutDiagnostics,
)
from app.services.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentGovernanceEvaluator,
)
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)

ROOT = Path(__file__).resolve().parents[2]
STAGES = (
    "control_only", "canary_1", "canary_5", "canary_10",
    "canary_25", "canary_50", "full",
)


def chain(status="ready", stage="full"):
    readiness = CognitiveRuntimeReadinessAssessment(status=status)
    advisory = CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
        readiness=readiness
    )
    rollout = CognitiveRuntimeRolloutDiagnostics(
        stage=stage,
        rollout_bps=D144_STAGE_BPS[stage],
        source_promotion_recommendation=advisory.recommendation,
        source_promotion_reason_code=advisory.reason_code,
    )
    return readiness, advisory, rollout


def assess(status="ready", stage="full"):
    readiness, advisory, rollout = chain(status, stage)
    return CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
        readiness=readiness, advisory=advisory, rollout=rollout
    )


def invalid_rollout(**updates):
    readiness, advisory, rollout = chain()
    rollout = rollout.model_copy(update=updates)
    return CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
        readiness=readiness, advisory=advisory, rollout=rollout
    )


def run_case(case):
    if 1 <= case <= 6:
        scenarios = (
            ("disabled", "disabled"),
            ("collecting", "collecting"),
            ("ready", "healthy"),
            ("degraded", "degraded"),
            ("unavailable", "unavailable"),
        )
        if case <= 5:
            source, expected = scenarios[case - 1]
            assert assess(source).status == expected
        else:
            assert CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
                readiness=object(), advisory=object(), rollout=object()
            ).status == "invalid_evidence"

    elif 7 <= case <= 11:
        scenarios = (
            ("disabled", "full", "none"),
            ("collecting", "full", "info"),
            ("degraded", "control_only", "warning"),
            ("degraded", "canary_5", "major"),
            ("unavailable", "full", "critical"),
        )
        status, stage, expected = scenarios[case - 7]
        assert assess(status, stage).severity == expected

    elif 12 <= case <= 16:
        scenarios = (
            ("control_only", "zero"),
            ("canary_1", "limited"),
            ("canary_25", "elevated"),
            ("full", "full"),
        )
        if case <= 15:
            stage, expected = scenarios[case - 12]
            assert assess("ready", stage).blast_radius == expected
        else:
            assert invalid_rollout(stage="bogus").blast_radius == "unknown"

    elif 17 <= case <= 22:
        scenarios = (
            ("disabled", "full", "no_action"),
            ("collecting", "full", "continue_collecting"),
            ("degraded", "control_only", "hold_current_stage"),
            ("degraded", "canary_10", "rollback_review"),
            ("unavailable", "full", "runtime_disable_review"),
        )
        if case <= 21:
            status, stage, expected = scenarios[case - 17]
            assert assess(status, stage).recommended_owner_action == expected
        else:
            result = CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
                readiness=None, advisory=None, rollout=None
            )
            assert (
                result.recommended_owner_action
                == "evidence_integrity_review"
            )

    elif 23 <= case <= 27:
        status = ("disabled", "collecting", "ready", "degraded", "unavailable")[
            case - 23
        ]
        readiness, advisory, rollout = chain(status)
        result = CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
            readiness=readiness, advisory=advisory, rollout=rollout
        )
        assert result.status != "invalid_evidence"
        assert result.source_readiness_status == status

    elif 28 <= case <= 32:
        readiness, advisory, rollout = chain()
        if case == 28:
            rollout = rollout.model_copy(
                update={"source_promotion_recommendation": "rollback_review"}
            )
        elif case == 29:
            rollout = rollout.model_copy(
                update={"source_promotion_reason_code": "readiness_degraded"}
            )
        elif case == 30:
            rollout = rollout.model_copy(update={"reference_baseline": "invalid"})
        elif case == 31:
            rollout = rollout.model_copy(update={"rollout_bps": 9999})
        else:
            rollout = rollout.model_copy(update={"owner_controlled": False})
        result = CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
            readiness=readiness, advisory=advisory, rollout=rollout
        )
        assert result.status == "invalid_evidence"
        assert result.severity == "critical"

    elif 33 <= case <= 44:
        matrix = (
            ("disabled", "control_only", "disabled", "none", "no_action"),
            ("collecting", "canary_1", "collecting", "info", "continue_collecting"),
            ("ready", "full", "healthy", "none", "no_action"),
            ("degraded", "control_only", "degraded", "warning", "hold_current_stage"),
            ("degraded", "canary_1", "degraded", "major", "rollback_review"),
            ("degraded", "canary_10", "degraded", "major", "rollback_review"),
            ("degraded", "canary_25", "degraded", "critical", "rollback_review"),
            ("degraded", "full", "degraded", "critical", "rollback_review"),
            ("unavailable", "control_only", "unavailable", "major", "runtime_disable_review"),
            ("unavailable", "canary_5", "unavailable", "critical", "runtime_disable_review"),
            ("unavailable", "canary_50", "unavailable", "critical", "runtime_disable_review"),
            ("unavailable", "full", "unavailable", "critical", "runtime_disable_review"),
        )
        source, stage, status, severity, action = matrix[case - 33]
        result = assess(source, stage)
        assert (
            result.status,
            result.severity,
            result.recommended_owner_action,
        ) == (status, severity, action)

    elif 45 <= case <= 52:
        scenarios = (
            ("disabled", "full", False),
            ("collecting", "full", False),
            ("ready", "full", False),
            ("degraded", "control_only", True),
            ("degraded", "full", True),
            ("unavailable", "control_only", True),
            ("unavailable", "full", True),
        )
        if case <= 51:
            status, stage, expected = scenarios[case - 45]
            assert assess(status, stage).incident_active is expected
        else:
            result = CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
                readiness=object(), advisory=None, rollout=None
            )
            assert result.incident_active is True

    elif 53 <= case <= 60:
        readiness, advisory, rollout = chain()
        if case == 53:
            args = dict(readiness=None, advisory=advisory, rollout=rollout)
        elif case == 54:
            args = dict(readiness=readiness, advisory=None, rollout=rollout)
        elif case == 55:
            args = dict(readiness=readiness, advisory=advisory, rollout=None)
        elif case == 56:
            bad = advisory.__class__(
                recommendation="rollback_review",
                reason_code="readiness_degraded",
                source_readiness_status="degraded",
                owner_decision_required=True,
            )
            args = dict(readiness=readiness, advisory=bad, rollout=rollout)
        elif case == 57:
            rollout = rollout.model_copy(update={"bucket_count": 9999})
            args = dict(readiness=readiness, advisory=advisory, rollout=rollout)
        elif case == 58:
            rollout = rollout.model_copy(update={"sticky_by_conversation": False})
            args = dict(readiness=readiness, advisory=advisory, rollout=rollout)
        elif case == 59:
            rollout = rollout.model_copy(update={"automatic_stage_increase": True})
            args = dict(readiness=readiness, advisory=advisory, rollout=rollout)
        else:
            rollout = rollout.model_copy(update={"configuration_authority": True})
            args = dict(readiness=readiness, advisory=advisory, rollout=rollout)
        result = CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(**args)
        assert (
            result.status,
            result.severity,
            result.incident_active,
            result.blast_radius,
            result.recommended_owner_action,
        ) == (
            "invalid_evidence",
            "critical",
            True,
            "unknown",
            "evidence_integrity_review",
        )

    elif 61 <= case <= 68:
        result = assess("degraded", "full")
        names = (
            "rollback_authority",
            "rollout_stage_authority",
            "runtime_disable_authority",
            "promotion_authority",
            "routing_authority",
            "execution_authority",
            "configuration_authority",
        )
        if case <= 67:
            assert getattr(result, names[case - 61]) is False
        else:
            assert all(getattr(result, name) is False for name in names)

    elif 69 <= case <= 72:
        result = assess("unavailable", "full")
        names = (
            "automatic_containment",
            "automatic_rollback",
            "automatic_runtime_disable",
        )
        if case <= 71:
            assert getattr(result, names[case - 69]) is False
        else:
            assert all(getattr(result, name) is False for name in names)

    elif 73 <= case <= 76:
        result = assess("disabled", "full")
        diag = CognitiveRuntimeIncidentGovernanceDiagnostics(
            status=result.status,
            severity=result.severity,
            incident_active=result.incident_active,
            blast_radius=result.blast_radius,
            recommended_owner_action=result.recommended_owner_action,
            source_readiness_status=result.source_readiness_status,
            source_promotion_recommendation=result.source_promotion_recommendation,
            source_promotion_reason_code=result.source_promotion_reason_code,
            source_rollout_stage=result.source_rollout_stage,
            source_rollout_bps=result.source_rollout_bps,
        )
        rendered = diag.model_dump()
        if case == 73:
            assert rendered["contract_version"] == "1"
        elif case == 74:
            assert rendered["implemented"] is True
        elif case == 75:
            assert rendered["reference_baseline"] == D145_REFERENCE_BASELINE
        else:
            assert {
                "status", "severity", "incident_active", "blast_radius",
                "recommended_owner_action",
            } <= set(rendered)

    elif 77 <= case <= 80:
        if case == 77:
            assert D145_REFERENCE_BASELINE == (
                "b30d15befe3a53ccab1946411c9cf4be3a0c147a"
            )
        elif case == 78:
            assert len(fields(CognitiveRuntimeIncidentAssessment)) == 21
        elif case == 79:
            assert set(STAGES) == set(D144_STAGE_BPS)
        else:
            source = (
                ROOT
                / "backend/app/services/cognitive_runtime_incident_governance.py"
            ).read_text(encoding="utf-8")
            assert "D142_MAX_" not in source and "D142_MIN_" not in source
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case", range(1, 81), ids=[f"F{i:02d}" for i in range(1, 81)]
)
def test_d145_functional_matrix(case):
    run_case(case)
