"""D152 deterministic Bounded Experience Context Projection V1 service."""

from __future__ import annotations

from app.contracts.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionDecision,
)
from app.contracts.cognitive_trusted_experience_context_projection import (
    D152_CONTRACT_VERSION,
    D152_PROJECTION_POLICY,
    D152_REFERENCE_BASELINE,
    CognitiveTrustedExperienceContextProjection,
    compute_cognitive_trusted_experience_projection_fingerprint,
)


class CognitiveTrustedExperienceContextProjectionService:
    """Project D151 policy metadata without behavioral consumption."""

    @staticmethod
    def project(
        *,
        decision: CognitiveTrustedExperienceConsumptionDecision,
    ) -> CognitiveTrustedExperienceContextProjection:
        if type(decision) is not CognitiveTrustedExperienceConsumptionDecision:
            raise ValueError("trusted_experience_projection_decision_invalid")
        decision.__post_init__()

        if decision.consumption_status == "denied":
            projection_status = "unavailable"
        elif decision.consumption_status == "allowed":
            if decision.source_advisory_status == "no_evidence":
                projection_status = "empty"
            elif (
                decision.source_advisory_status == "exact_match"
                and decision.source_truncated is False
            ):
                projection_status = "projected"
            else:
                raise ValueError(
                    "trusted_experience_projection_allowed_source_invalid"
                )
        elif decision.consumption_status == "restricted":
            projection_status = "restricted"
        else:
            raise ValueError(
                "trusted_experience_projection_consumption_status_invalid"
            )

        fingerprint = (
            compute_cognitive_trusted_experience_projection_fingerprint(
                contract_version=D152_CONTRACT_VERSION,
                reference_baseline=D152_REFERENCE_BASELINE,
                projection_policy=D152_PROJECTION_POLICY,
                workspace_id=decision.workspace_id,
                source_consumption_status=decision.consumption_status,
                source_policy_fingerprint=decision.policy_fingerprint,
                source_advisory_status=decision.source_advisory_status,
                source_truncated=decision.source_truncated,
                projection_status=projection_status,
                restriction_reasons=decision.restriction_reasons,
            )
        )

        return CognitiveTrustedExperienceContextProjection(
            contract_version=D152_CONTRACT_VERSION,
            reference_baseline=D152_REFERENCE_BASELINE,
            projection_policy=D152_PROJECTION_POLICY,
            workspace_id=decision.workspace_id,
            source_consumption_status=decision.consumption_status,
            source_policy_fingerprint=decision.policy_fingerprint,
            source_advisory_status=decision.source_advisory_status,
            source_truncated=decision.source_truncated,
            projection_status=projection_status,
            restriction_reasons=decision.restriction_reasons,
            projection_fingerprint=fingerprint,
        )


__all__ = ["CognitiveTrustedExperienceContextProjectionService"]
