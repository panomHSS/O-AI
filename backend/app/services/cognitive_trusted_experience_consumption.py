"""D151 deterministic Trusted Experience Consumption Policy evaluator."""

from __future__ import annotations

from app.contracts.cognitive_trusted_experience_consumption import (
    D151_CONSUMPTION_POLICY,
    D151_CONTRACT_VERSION,
    D151_REFERENCE_BASELINE,
    CognitiveTrustedExperienceConsumptionDecision,
    CognitiveTrustedExperienceRestrictionReason,
    compute_cognitive_trusted_experience_consumption_policy_fingerprint,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinding,
)


class CognitiveTrustedExperienceConsumptionPolicyEvaluator:
    """Evaluate D150 binding metadata without consuming it behaviorally."""

    @staticmethod
    def evaluate(
        *,
        binding: CognitiveTrustedExperienceRuntimeBinding,
    ) -> CognitiveTrustedExperienceConsumptionDecision:
        if type(binding) is not CognitiveTrustedExperienceRuntimeBinding:
            raise ValueError("trusted_experience_consumption_binding_invalid")
        binding.__post_init__()

        if binding.binding_status == "unavailable":
            status = "denied"
            reasons: tuple[
                CognitiveTrustedExperienceRestrictionReason, ...
            ] = ("binding_unavailable",)
        elif binding.advisory_status == "no_evidence":
            status = "allowed"
            reasons = ()
        elif binding.advisory_status == "exact_match":
            if binding.source_truncated:
                status = "restricted"
                reasons = ("truncated_source",)
            else:
                status = "allowed"
                reasons = ()
        elif binding.advisory_status == "partial_match":
            status = "restricted"
            reasons = (
                ("partial_relevance", "truncated_source")
                if binding.source_truncated
                else ("partial_relevance",)
            )
        elif binding.advisory_status == "task_only":
            status = "restricted"
            reasons = (
                ("task_only_relevance", "truncated_source")
                if binding.source_truncated
                else ("task_only_relevance",)
            )
        elif binding.advisory_status == "mixed_relevance":
            status = "restricted"
            reasons = (
                ("mixed_relevance", "truncated_source")
                if binding.source_truncated
                else ("mixed_relevance",)
            )
        else:
            raise ValueError("trusted_experience_consumption_advisory_invalid")

        fingerprint = (
            compute_cognitive_trusted_experience_consumption_policy_fingerprint(
                contract_version=D151_CONTRACT_VERSION,
                reference_baseline=D151_REFERENCE_BASELINE,
                consumption_policy=D151_CONSUMPTION_POLICY,
                workspace_id=binding.workspace_id,
                source_binding_status=binding.binding_status,
                source_advisory_status=binding.advisory_status,
                source_advisory_fingerprint=binding.advisory_fingerprint,
                source_truncated=binding.source_truncated,
                consumption_status=status,
                restriction_reasons=reasons,
            )
        )
        return CognitiveTrustedExperienceConsumptionDecision(
            contract_version=D151_CONTRACT_VERSION,
            reference_baseline=D151_REFERENCE_BASELINE,
            consumption_policy=D151_CONSUMPTION_POLICY,
            workspace_id=binding.workspace_id,
            source_binding_status=binding.binding_status,
            source_advisory_status=binding.advisory_status,
            source_advisory_fingerprint=binding.advisory_fingerprint,
            source_truncated=binding.source_truncated,
            consumption_status=status,
            restriction_reasons=reasons,
            policy_fingerprint=fingerprint,
        )


__all__ = ["CognitiveTrustedExperienceConsumptionPolicyEvaluator"]
