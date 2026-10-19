"""D154 deterministic Experience-Informed Critic / Verification V1 service."""

from __future__ import annotations

from app.contracts.cognitive_trusted_experience_reasoning import (
    CognitiveTrustedExperienceReasoningInfluence,
)
from app.contracts.cognitive_trusted_experience_verification import (
    D154_CONTRACT_VERSION,
    D154_CRITIC_DIRECTIVE_ID,
    D154_REFERENCE_BASELINE,
    D154_VERIFICATION_POLICY,
    CognitiveTrustedExperienceVerificationInfluence,
    compute_cognitive_trusted_experience_verification_fingerprint,
)


class CognitiveTrustedExperienceVerificationInfluenceService:
    @staticmethod
    def evaluate(
        *,
        reasoning: CognitiveTrustedExperienceReasoningInfluence,
    ) -> CognitiveTrustedExperienceVerificationInfluence:
        if type(reasoning) is not CognitiveTrustedExperienceReasoningInfluence:
            raise ValueError("trusted_experience_verification_reasoning_invalid")
        reasoning.__post_init__()
        verification_status = (
            "active" if reasoning.reasoning_status == "active" else "inactive"
        )
        directive_id = (
            D154_CRITIC_DIRECTIVE_ID
            if verification_status == "active"
            else None
        )
        fingerprint = compute_cognitive_trusted_experience_verification_fingerprint(
            contract_version=D154_CONTRACT_VERSION,
            reference_baseline=D154_REFERENCE_BASELINE,
            verification_policy=D154_VERIFICATION_POLICY,
            workspace_id=reasoning.workspace_id,
            source_reasoning_status=reasoning.reasoning_status,
            source_reasoning_fingerprint=reasoning.reasoning_fingerprint,
            verification_status=verification_status,
            directive_id=directive_id,
        )
        return CognitiveTrustedExperienceVerificationInfluence(
            contract_version=D154_CONTRACT_VERSION,
            reference_baseline=D154_REFERENCE_BASELINE,
            verification_policy=D154_VERIFICATION_POLICY,
            workspace_id=reasoning.workspace_id,
            source_reasoning_status=reasoning.reasoning_status,
            source_reasoning_fingerprint=reasoning.reasoning_fingerprint,
            verification_status=verification_status,
            directive_id=directive_id,
            verification_fingerprint=fingerprint,
        )


__all__ = ["CognitiveTrustedExperienceVerificationInfluenceService"]
