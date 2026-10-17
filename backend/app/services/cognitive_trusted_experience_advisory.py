"""D149 deterministic Experience-Informed Advisory V1 evaluator."""

from __future__ import annotations

from app.contracts.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisory,
    CognitiveTrustedExperienceAdvisoryStatus,
    compute_cognitive_trusted_experience_advisory_fingerprint,
)
from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidence,
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
)


def _invalid() -> CognitiveTrustedExperienceAdvisory:
    fingerprint = compute_cognitive_trusted_experience_advisory_fingerprint(
        workspace_id=None,
        source_evidence_set_fingerprint=None,
        source_selected_count=None,
        source_truncated=None,
        advisory_status="invalid_evidence",
        best_relevance_tier=None,
        mixed_relevance=False,
    )
    return CognitiveTrustedExperienceAdvisory(
        workspace_id=None,
        source_evidence_set_fingerprint=None,
        source_selected_count=None,
        source_truncated=None,
        advisory_status="invalid_evidence",
        best_relevance_tier=None,
        mixed_relevance=False,
        advisory_fingerprint=fingerprint,
    )


def _tier(
    item: CognitiveTrustedExperienceEvidence,
    query: CognitiveTrustedExperienceRetrievalQuery,
) -> int:
    if item.authoritative_ai_task_kind is not query.authoritative_ai_task_kind:
        raise ValueError("trusted_experience_advisory_task_kind_mismatch")
    cognitive_match = item.cognitive_intent == query.cognitive_intent
    interaction_match = item.interaction_intent == query.interaction_intent
    if cognitive_match and interaction_match:
        return 0
    if cognitive_match:
        return 1
    if interaction_match:
        return 2
    return 3


class CognitiveTrustedExperienceAdvisoryEvaluator:
    """Pure stateless interpretation of a validated D148 evidence set."""

    @classmethod
    def evaluate(
        cls,
        *,
        evidence_set: object | None,
    ) -> CognitiveTrustedExperienceAdvisory:
        if type(evidence_set) is not CognitiveTrustedExperienceEvidenceSet:
            return _invalid()

        try:
            if (
                type(evidence_set.query)
                is not CognitiveTrustedExperienceRetrievalQuery
            ):
                raise ValueError("trusted_experience_advisory_query_invalid")
            evidence_set.query.__post_init__()
            for item in evidence_set.evidence:
                if type(item) is not CognitiveTrustedExperienceEvidence:
                    raise ValueError("trusted_experience_advisory_item_invalid")
                item.__post_init__()
            evidence_set.__post_init__()
            tiers = tuple(_tier(item, evidence_set.query) for item in evidence_set.evidence)
        except (AttributeError, TypeError, ValueError):
            return _invalid()

        if not tiers:
            status: CognitiveTrustedExperienceAdvisoryStatus = "no_evidence"
            best_tier = None
            mixed = False
        else:
            distinct = frozenset(tiers)
            best_tier = min(distinct)
            mixed = len(distinct) > 1
            if mixed:
                status = "mixed_relevance"
            elif best_tier == 0:
                status = "exact_match"
            elif best_tier in (1, 2):
                status = "partial_match"
            else:
                status = "task_only"

        fingerprint = compute_cognitive_trusted_experience_advisory_fingerprint(
            workspace_id=evidence_set.workspace_id,
            source_evidence_set_fingerprint=evidence_set.evidence_set_fingerprint,
            source_selected_count=evidence_set.selected_count,
            source_truncated=evidence_set.truncated,
            advisory_status=status,
            best_relevance_tier=best_tier,
            mixed_relevance=mixed,
        )
        return CognitiveTrustedExperienceAdvisory(
            workspace_id=evidence_set.workspace_id,
            source_evidence_set_fingerprint=evidence_set.evidence_set_fingerprint,
            source_selected_count=evidence_set.selected_count,
            source_truncated=evidence_set.truncated,
            advisory_status=status,
            best_relevance_tier=best_tier,
            mixed_relevance=mixed,
            advisory_fingerprint=fingerprint,
        )


__all__ = ["CognitiveTrustedExperienceAdvisoryEvaluator"]
