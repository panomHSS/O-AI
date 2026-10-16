"""D143 immutable owner-controlled cognitive promotion/rollback advisory contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

D143_REFERENCE_BASELINE = "1b24f231a09bf6f03ad6fb796aeecffa484ed9f0"

CognitiveRuntimePromotionRecommendation: TypeAlias = Literal[
    "no_action",
    "hold_for_evidence",
    "eligible_for_promotion",
    "rollback_review",
    "fail_closed",
]
CognitiveRuntimePromotionReasonCode: TypeAlias = Literal[
    "runtime_disabled",
    "insufficient_evidence",
    "readiness_thresholds_satisfied",
    "readiness_degraded",
    "readiness_unavailable",
    "invalid_readiness_evidence",
]
CognitiveRuntimePromotionSourceStatus: TypeAlias = Literal[
    "disabled",
    "collecting",
    "ready",
    "degraded",
    "unavailable",
]

_VALID_COMBINATIONS = {
    ("no_action", "runtime_disabled", "disabled", False),
    ("hold_for_evidence", "insufficient_evidence", "collecting", False),
    (
        "eligible_for_promotion",
        "readiness_thresholds_satisfied",
        "ready",
        True,
    ),
    ("rollback_review", "readiness_degraded", "degraded", True),
    ("fail_closed", "readiness_unavailable", "unavailable", False),
    ("fail_closed", "invalid_readiness_evidence", None, False),
}


@dataclass(frozen=True, slots=True)
class CognitiveRuntimePromotionAdvisory:
    """Read-only D143 governance recommendation; never operational authority."""

    recommendation: CognitiveRuntimePromotionRecommendation
    reason_code: CognitiveRuntimePromotionReasonCode
    source_readiness_status: CognitiveRuntimePromotionSourceStatus | None
    owner_decision_required: bool
    reference_baseline: str = D143_REFERENCE_BASELINE

    promotion_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_rollback: Literal[False] = False

    def __post_init__(self) -> None:
        if self.reference_baseline != D143_REFERENCE_BASELINE:
            raise ValueError("cognitive_runtime_promotion_advisory_baseline_invalid")
        if type(self.owner_decision_required) is not bool:
            raise ValueError(
                "cognitive_runtime_promotion_advisory_owner_decision_invalid"
            )

        combination = (
            self.recommendation,
            self.reason_code,
            self.source_readiness_status,
            self.owner_decision_required,
        )
        if combination not in _VALID_COMBINATIONS:
            raise ValueError(
                "cognitive_runtime_promotion_advisory_combination_invalid"
            )

        for name in (
            "promotion_authority",
            "rollback_authority",
            "execution_authority",
            "routing_authority",
            "configuration_authority",
            "automatic_promotion",
            "automatic_rollback",
        ):
            if getattr(self, name) is not False:
                raise ValueError(
                    f"cognitive_runtime_promotion_advisory_{name}_invalid"
                )


__all__ = [
    "D143_REFERENCE_BASELINE",
    "CognitiveRuntimePromotionAdvisory",
    "CognitiveRuntimePromotionReasonCode",
    "CognitiveRuntimePromotionRecommendation",
    "CognitiveRuntimePromotionSourceStatus",
]
