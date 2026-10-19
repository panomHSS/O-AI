"""D153 deterministic Experience-Informed Reasoning V1 service."""

from __future__ import annotations

from app.contracts.cognitive_trusted_experience_context_projection import (
    CognitiveTrustedExperienceContextProjection,
)
from app.contracts.cognitive_trusted_experience_reasoning import (
    D153_CONTRACT_VERSION,
    D153_PRIMARY_REASONING_DIRECTIVE_ID,
    D153_REASONING_POLICY,
    D153_REFERENCE_BASELINE,
    CognitiveTrustedExperienceReasoningInfluence,
    compute_cognitive_trusted_experience_reasoning_fingerprint,
)


class CognitiveTrustedExperienceReasoningInfluenceService:
    """Map D152 projection metadata to bounded primary-reasoning awareness."""

    @staticmethod
    def evaluate(
        *,
        projection: CognitiveTrustedExperienceContextProjection,
    ) -> CognitiveTrustedExperienceReasoningInfluence:
        if type(projection) is not CognitiveTrustedExperienceContextProjection:
            raise ValueError("trusted_experience_reasoning_projection_invalid")
        projection.__post_init__()

        reasoning_status = (
            "active" if projection.projection_status == "projected" else "inactive"
        )
        directive_id = (
            D153_PRIMARY_REASONING_DIRECTIVE_ID
            if reasoning_status == "active"
            else None
        )
        fingerprint = compute_cognitive_trusted_experience_reasoning_fingerprint(
            contract_version=D153_CONTRACT_VERSION,
            reference_baseline=D153_REFERENCE_BASELINE,
            reasoning_policy=D153_REASONING_POLICY,
            workspace_id=projection.workspace_id,
            source_projection_status=projection.projection_status,
            source_projection_fingerprint=projection.projection_fingerprint,
            reasoning_status=reasoning_status,
            directive_id=directive_id,
        )
        return CognitiveTrustedExperienceReasoningInfluence(
            contract_version=D153_CONTRACT_VERSION,
            reference_baseline=D153_REFERENCE_BASELINE,
            reasoning_policy=D153_REASONING_POLICY,
            workspace_id=projection.workspace_id,
            source_projection_status=projection.projection_status,
            source_projection_fingerprint=projection.projection_fingerprint,
            reasoning_status=reasoning_status,
            directive_id=directive_id,
            reasoning_fingerprint=fingerprint,
        )


__all__ = ["CognitiveTrustedExperienceReasoningInfluenceService"]
