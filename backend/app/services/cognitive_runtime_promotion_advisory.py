"""D143 deterministic owner-controlled promotion/rollback governance advisory."""

from __future__ import annotations

from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionAdvisory,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)


class CognitiveRuntimePromotionGovernanceEvaluator:
    """Pure, stateless mapping from validated D142 readiness to D143 advisory."""

    @staticmethod
    def _invalid() -> CognitiveRuntimePromotionAdvisory:
        return CognitiveRuntimePromotionAdvisory(
            recommendation="fail_closed",
            reason_code="invalid_readiness_evidence",
            source_readiness_status=None,
            owner_decision_required=False,
        )

    @classmethod
    def evaluate(
        cls,
        *,
        readiness: object | None,
    ) -> CognitiveRuntimePromotionAdvisory:
        if type(readiness) is not CognitiveRuntimeReadinessAssessment:
            return cls._invalid()

        try:
            # Re-run only D142's immutable contract validation. D143 never
            # recalculates readiness thresholds or interprets D142 rates.
            readiness.__post_init__()
        except (AttributeError, TypeError, ValueError):
            return cls._invalid()

        if readiness.status == "disabled":
            recommendation = "no_action"
            reason_code = "runtime_disabled"
            owner_decision_required = False
        elif readiness.status == "collecting":
            recommendation = "hold_for_evidence"
            reason_code = "insufficient_evidence"
            owner_decision_required = False
        elif readiness.status == "ready":
            recommendation = "eligible_for_promotion"
            reason_code = "readiness_thresholds_satisfied"
            owner_decision_required = True
        elif readiness.status == "degraded":
            recommendation = "rollback_review"
            reason_code = "readiness_degraded"
            owner_decision_required = True
        elif readiness.status == "unavailable":
            recommendation = "fail_closed"
            reason_code = "readiness_unavailable"
            owner_decision_required = False
        else:
            return cls._invalid()

        return CognitiveRuntimePromotionAdvisory(
            recommendation=recommendation,
            reason_code=reason_code,
            source_readiness_status=readiness.status,
            owner_decision_required=owner_decision_required,
        )


__all__ = ["CognitiveRuntimePromotionGovernanceEvaluator"]
