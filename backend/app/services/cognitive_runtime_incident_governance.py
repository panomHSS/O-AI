"""D145 deterministic incident / degradation governance evaluator."""

from __future__ import annotations

from app.contracts.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentAssessment,
)
from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionAdvisory,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.contracts.cognitive_runtime_rollout import (
    D144_REFERENCE_BASELINE,
    D144_ROLLOUT_BUCKET_COUNT,
    D144_SELECTION_SCOPE,
    D144_SELECTION_STRATEGY,
    D144_STAGE_BPS,
)
from app.schemas.diagnostics import CognitiveRuntimeRolloutDiagnostics

_EXPECTED_ADVISORY = {
    "disabled": ("no_action", "runtime_disabled"),
    "collecting": ("hold_for_evidence", "insufficient_evidence"),
    "ready": ("eligible_for_promotion", "readiness_thresholds_satisfied"),
    "degraded": ("rollback_review", "readiness_degraded"),
    "unavailable": ("fail_closed", "readiness_unavailable"),
}

_BLAST_RADIUS_BY_STAGE = {
    "control_only": "zero",
    "canary_1": "limited",
    "canary_5": "limited",
    "canary_10": "limited",
    "canary_25": "elevated",
    "canary_50": "elevated",
    "full": "full",
}


class CognitiveRuntimeIncidentGovernanceEvaluator:
    """Pure D145 classifier over one validated D142â†’D143â†’D144 evidence chain."""

    @staticmethod
    def _invalid() -> CognitiveRuntimeIncidentAssessment:
        return CognitiveRuntimeIncidentAssessment(
            status="invalid_evidence",
            severity="critical",
            incident_active=True,
            blast_radius="unknown",
            recommended_owner_action="evidence_integrity_review",
            source_readiness_status=None,
            source_promotion_recommendation=None,
            source_promotion_reason_code=None,
            source_rollout_stage=None,
            source_rollout_bps=None,
        )

    @classmethod
    def evaluate(
        cls,
        *,
        readiness: object | None,
        advisory: object | None,
        rollout: object | None,
    ) -> CognitiveRuntimeIncidentAssessment:
        if type(readiness) is not CognitiveRuntimeReadinessAssessment:
            return cls._invalid()
        if type(advisory) is not CognitiveRuntimePromotionAdvisory:
            return cls._invalid()
        if type(rollout) is not CognitiveRuntimeRolloutDiagnostics:
            return cls._invalid()

        try:
            readiness.__post_init__()
            advisory.__post_init__()

            expected_advisory = _EXPECTED_ADVISORY[readiness.status]
            if (advisory.recommendation, advisory.reason_code) != expected_advisory:
                raise ValueError("d145_d142_d143_mapping_invalid")
            if advisory.source_readiness_status != readiness.status:
                raise ValueError("d145_d143_source_status_invalid")

            if rollout.reference_baseline != D144_REFERENCE_BASELINE:
                raise ValueError("d145_d144_baseline_invalid")
            if rollout.bucket_count != D144_ROLLOUT_BUCKET_COUNT:
                raise ValueError("d145_d144_bucket_count_invalid")
            if rollout.selection_scope != D144_SELECTION_SCOPE:
                raise ValueError("d145_d144_selection_scope_invalid")
            if rollout.selection_strategy != D144_SELECTION_STRATEGY:
                raise ValueError("d145_d144_selection_strategy_invalid")
            if rollout.sticky_by_conversation is not True:
                raise ValueError("d145_d144_sticky_invalid")
            if rollout.owner_controlled is not True:
                raise ValueError("d145_d144_owner_control_invalid")

            expected_bps = D144_STAGE_BPS.get(rollout.stage)
            if expected_bps is None or rollout.rollout_bps != expected_bps:
                raise ValueError("d145_d144_stage_bps_invalid")

            if (
                rollout.source_promotion_recommendation
                != advisory.recommendation
            ):
                raise ValueError("d145_d144_recommendation_source_invalid")
            if rollout.source_promotion_reason_code != advisory.reason_code:
                raise ValueError("d145_d144_reason_source_invalid")

            for name in (
                "automatic_stage_increase",
                "automatic_stage_decrease",
                "execution_authority",
                "routing_authority",
                "configuration_authority",
            ):
                if getattr(rollout, name) is not False:
                    raise ValueError(f"d145_d144_{name}_invalid")

            blast_radius = _BLAST_RADIUS_BY_STAGE[rollout.stage]
        except (AttributeError, KeyError, TypeError, ValueError):
            return cls._invalid()

        if readiness.status == "disabled":
            values = ("disabled", "none", False, "no_action")
        elif readiness.status == "collecting":
            values = ("collecting", "info", False, "continue_collecting")
        elif readiness.status == "ready":
            values = ("healthy", "none", False, "no_action")
        elif readiness.status == "degraded":
            if blast_radius == "zero":
                values = ("degraded", "warning", True, "hold_current_stage")
            elif blast_radius == "limited":
                values = ("degraded", "major", True, "rollback_review")
            else:
                values = ("degraded", "critical", True, "rollback_review")
        elif readiness.status == "unavailable":
            severity = "major" if blast_radius == "zero" else "critical"
            values = (
                "unavailable",
                severity,
                True,
                "runtime_disable_review",
            )
        else:
            return cls._invalid()

        status, severity, incident_active, owner_action = values
        return CognitiveRuntimeIncidentAssessment(
            status=status,
            severity=severity,
            incident_active=incident_active,
            blast_radius=blast_radius,
            recommended_owner_action=owner_action,
            source_readiness_status=readiness.status,
            source_promotion_recommendation=advisory.recommendation,
            source_promotion_reason_code=advisory.reason_code,
            source_rollout_stage=rollout.stage,
            source_rollout_bps=rollout.rollout_bps,
        )


__all__ = ["CognitiveRuntimeIncidentGovernanceEvaluator"]
