"D189 deterministic Execution Experience Advisory V1 evaluator."

from __future__ import annotations

from app.contracts.governed_execution_experience_advisory import (
    ExecutionExperienceAdvisory,
    ExecutionExperienceAdvisoryStatus,
    compute_execution_experience_advisory_fingerprint,
)
from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidence,
    TrustedExecutionExperienceEvidenceSet,
    TrustedExecutionExperienceRetrievalQuery,
)


def _invalid() -> ExecutionExperienceAdvisory:
    fingerprint = compute_execution_experience_advisory_fingerprint(
        workspace_id=None,
        source_evidence_set_fingerprint=None,
        source_selected_count=None,
        source_truncated=None,
        advisory_status="invalid_evidence",
        best_relevance_tier=None,
        mixed_relevance=False,
    )
    return ExecutionExperienceAdvisory(
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
    item: TrustedExecutionExperienceEvidence,
    query: TrustedExecutionExperienceRetrievalQuery,
) -> int:
    if (
        item.target_kind != query.target_kind
        or item.capability_id != query.capability_id
        or item.effect != query.effect
        or item.risk_class != query.risk_class
    ):
        raise ValueError("execution_experience_advisory_primary_match_invalid")

    adapter_match = item.adapter_id == query.adapter_id
    operation_match = item.operation == query.operation

    if adapter_match and operation_match:
        return 0
    if operation_match:
        return 1
    if adapter_match:
        return 2
    return 3


class TrustedExecutionExperienceAdvisoryEvaluator:
    """Pure stateless interpretation of one validated D188 evidence set."""

    @classmethod
    def evaluate(
        cls,
        *,
        evidence_set: object | None,
    ) -> ExecutionExperienceAdvisory:
        if type(evidence_set) is not TrustedExecutionExperienceEvidenceSet:
            return _invalid()

        try:
            if (
                type(evidence_set.query)
                is not TrustedExecutionExperienceRetrievalQuery
            ):
                raise ValueError(
                    "execution_experience_advisory_query_invalid"
                )
            evidence_set.query.__post_init__()
            for item in evidence_set.evidence:
                if type(item) is not TrustedExecutionExperienceEvidence:
                    raise ValueError(
                        "execution_experience_advisory_item_invalid"
                    )
                item.__post_init__()
            evidence_set.__post_init__()
            tiers = tuple(
                _tier(item, evidence_set.query)
                for item in evidence_set.evidence
            )
        except (AttributeError, TypeError, ValueError):
            return _invalid()

        if not tiers:
            status: ExecutionExperienceAdvisoryStatus = "no_evidence"
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
            elif best_tier == 1:
                status = "operation_match"
            elif best_tier == 2:
                status = "adapter_match"
            else:
                status = "capability_only"

        fingerprint = compute_execution_experience_advisory_fingerprint(
            workspace_id=evidence_set.workspace_id,
            source_evidence_set_fingerprint=(
                evidence_set.evidence_set_fingerprint
            ),
            source_selected_count=evidence_set.selected_count,
            source_truncated=evidence_set.truncated,
            advisory_status=status,
            best_relevance_tier=best_tier,
            mixed_relevance=mixed,
        )
        return ExecutionExperienceAdvisory(
            workspace_id=evidence_set.workspace_id,
            source_evidence_set_fingerprint=(
                evidence_set.evidence_set_fingerprint
            ),
            source_selected_count=evidence_set.selected_count,
            source_truncated=evidence_set.truncated,
            advisory_status=status,
            best_relevance_tier=best_tier,
            mixed_relevance=mixed,
            advisory_fingerprint=fingerprint,
        )


__all__ = ["TrustedExecutionExperienceAdvisoryEvaluator"]
