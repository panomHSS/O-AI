"""D145 immutable incident / degradation governance contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionReasonCode,
    CognitiveRuntimePromotionRecommendation,
)
from app.contracts.cognitive_runtime_readiness import CognitiveRuntimeReadinessStatus
from app.contracts.cognitive_runtime_rollout import (
    D144_RATE_SCALE_BPS,
    CognitiveRuntimeRolloutStage,
)

D145_REFERENCE_BASELINE = "b30d15befe3a53ccab1946411c9cf4be3a0c147a"

CognitiveRuntimeIncidentStatus: TypeAlias = Literal[
    "disabled", "collecting", "healthy", "degraded", "unavailable",
    "invalid_evidence",
]
CognitiveRuntimeIncidentSeverity: TypeAlias = Literal[
    "none", "info", "warning", "major", "critical",
]
CognitiveRuntimeIncidentBlastRadius: TypeAlias = Literal[
    "zero", "limited", "elevated", "full", "unknown",
]
CognitiveRuntimeIncidentOwnerAction: TypeAlias = Literal[
    "no_action",
    "continue_collecting",
    "hold_current_stage",
    "rollback_review",
    "runtime_disable_review",
    "evidence_integrity_review",
]

_VALID_STATUS_SEVERITY_ACTION = {
    ("disabled", "none", False, "no_action"),
    ("collecting", "info", False, "continue_collecting"),
    ("healthy", "none", False, "no_action"),
    ("degraded", "warning", True, "hold_current_stage"),
    ("degraded", "major", True, "rollback_review"),
    ("degraded", "critical", True, "rollback_review"),
    ("unavailable", "major", True, "runtime_disable_review"),
    ("unavailable", "critical", True, "runtime_disable_review"),
    ("invalid_evidence", "critical", True, "evidence_integrity_review"),
}


@dataclass(frozen=True, slots=True)
class CognitiveRuntimeIncidentAssessment:
    """Read-only incident posture; never containment or rollback authority."""

    status: CognitiveRuntimeIncidentStatus
    severity: CognitiveRuntimeIncidentSeverity
    incident_active: bool
    blast_radius: CognitiveRuntimeIncidentBlastRadius
    recommended_owner_action: CognitiveRuntimeIncidentOwnerAction

    source_readiness_status: CognitiveRuntimeReadinessStatus | None
    source_promotion_recommendation: CognitiveRuntimePromotionRecommendation | None
    source_promotion_reason_code: CognitiveRuntimePromotionReasonCode | None
    source_rollout_stage: CognitiveRuntimeRolloutStage | None
    source_rollout_bps: int | None

    reference_baseline: str = D145_REFERENCE_BASELINE

    rollback_authority: Literal[False] = False
    rollout_stage_authority: Literal[False] = False
    runtime_disable_authority: Literal[False] = False
    promotion_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False

    automatic_containment: Literal[False] = False
    automatic_rollback: Literal[False] = False
    automatic_runtime_disable: Literal[False] = False

    def __post_init__(self) -> None:
        if self.reference_baseline != D145_REFERENCE_BASELINE:
            raise ValueError("cognitive_runtime_incident_baseline_invalid")
        if type(self.incident_active) is not bool:
            raise ValueError("cognitive_runtime_incident_active_invalid")

        combination = (
            self.status,
            self.severity,
            self.incident_active,
            self.recommended_owner_action,
        )
        if combination not in _VALID_STATUS_SEVERITY_ACTION:
            raise ValueError("cognitive_runtime_incident_combination_invalid")

        if self.blast_radius not in {
            "zero", "limited", "elevated", "full", "unknown"
        }:
            raise ValueError("cognitive_runtime_incident_blast_radius_invalid")

        if self.status == "invalid_evidence":
            if self.blast_radius != "unknown":
                raise ValueError(
                    "cognitive_runtime_incident_invalid_evidence_radius_invalid"
                )
        else:
            if self.blast_radius == "unknown":
                raise ValueError(
                    "cognitive_runtime_incident_valid_evidence_radius_invalid"
                )
            if any(
                value is None
                for value in (
                    self.source_readiness_status,
                    self.source_promotion_recommendation,
                    self.source_promotion_reason_code,
                    self.source_rollout_stage,
                    self.source_rollout_bps,
                )
            ):
                raise ValueError(
                    "cognitive_runtime_incident_source_evidence_missing"
                )

        if self.status == "degraded":
            expected = {
                "zero": ("warning", "hold_current_stage"),
                "limited": ("major", "rollback_review"),
                "elevated": ("critical", "rollback_review"),
                "full": ("critical", "rollback_review"),
            }.get(self.blast_radius)
            if expected != (self.severity, self.recommended_owner_action):
                raise ValueError(
                    "cognitive_runtime_incident_degraded_mapping_invalid"
                )

        if self.status == "unavailable":
            expected_severity = (
                "major" if self.blast_radius == "zero" else "critical"
            )
            if self.severity != expected_severity:
                raise ValueError(
                    "cognitive_runtime_incident_unavailable_mapping_invalid"
                )

        if self.source_rollout_bps is not None:
            if (
                isinstance(self.source_rollout_bps, bool)
                or type(self.source_rollout_bps) is not int
                or not 0 <= self.source_rollout_bps <= D144_RATE_SCALE_BPS
            ):
                raise ValueError(
                    "cognitive_runtime_incident_source_rollout_bps_invalid"
                )

        for name in (
            "rollback_authority",
            "rollout_stage_authority",
            "runtime_disable_authority",
            "promotion_authority",
            "routing_authority",
            "execution_authority",
            "configuration_authority",
            "automatic_containment",
            "automatic_rollback",
            "automatic_runtime_disable",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_runtime_incident_{name}_invalid")


__all__ = [
    "D145_REFERENCE_BASELINE",
    "CognitiveRuntimeIncidentAssessment",
    "CognitiveRuntimeIncidentBlastRadius",
    "CognitiveRuntimeIncidentOwnerAction",
    "CognitiveRuntimeIncidentSeverity",
    "CognitiveRuntimeIncidentStatus",
]
