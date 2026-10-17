from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.cognitive_trusted_experience_advisory import (
    compute_cognitive_trusted_experience_advisory_fingerprint,
)
from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidenceSet,
    compute_cognitive_trusted_experience_evidence_set_fingerprint,
)
from app.services.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisoryEvaluator,
)
from tests.test_d149_cognitive_trusted_experience_advisory import (
    evaluate,
    make_item,
    make_query,
    make_set,
)


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    variant = (case - 1) // 8

    if slot == 0:
        source = make_set((variant % 4,))
        assert evaluate(source) == evaluate(source)
    elif slot == 1:
        source = make_set((0, 1, 3))
        first = CognitiveTrustedExperienceAdvisoryEvaluator()
        second = CognitiveTrustedExperienceAdvisoryEvaluator()
        assert first.evaluate(evidence_set=source) == second.evaluate(evidence_set=source)
        assert vars(first) == vars(second) == {}
    elif slot == 2:
        result = evaluate(make_set((0, 1)))
        expected = compute_cognitive_trusted_experience_advisory_fingerprint(
            workspace_id=result.workspace_id,
            source_evidence_set_fingerprint=result.source_evidence_set_fingerprint,
            source_selected_count=result.source_selected_count,
            source_truncated=result.source_truncated,
            advisory_status=result.advisory_status,
            best_relevance_tier=result.best_relevance_tier,
            mixed_relevance=result.mixed_relevance,
        )
        assert result.advisory_fingerprint == expected
    elif slot == 3:
        query = make_query()
        first = make_item(1, tier=0, proposal_seed="alpha")
        second = make_item(1, tier=0, proposal_seed=f"beta-{variant}")
        left_fp = compute_cognitive_trusted_experience_evidence_set_fingerprint(query=query, evidence=(first,))
        right_fp = compute_cognitive_trusted_experience_evidence_set_fingerprint(query=query, evidence=(second,))
        left = CognitiveTrustedExperienceEvidenceSet(
            workspace_id=query.workspace_id, query=query, evidence=(first,),
            selected_count=1, truncated=False, evidence_set_fingerprint=left_fp,
        )
        right = CognitiveTrustedExperienceEvidenceSet(
            workspace_id=query.workspace_id, query=query, evidence=(second,),
            selected_count=1, truncated=False, evidence_set_fingerprint=right_fp,
        )
        assert evaluate(left).advisory_status == evaluate(right).advisory_status
        assert evaluate(left).advisory_fingerprint != evaluate(right).advisory_fingerprint
    elif slot == 4:
        query = make_query()
        original = make_item(1, tier=0, model="model-a")
        changed = replace(original, authorized_model_id=f"model-{variant}")
        fp = compute_cognitive_trusted_experience_evidence_set_fingerprint(query=query, evidence=(original,))
        left = CognitiveTrustedExperienceEvidenceSet(
            workspace_id=query.workspace_id, query=query, evidence=(original,),
            selected_count=1, truncated=False, evidence_set_fingerprint=fp,
        )
        right = CognitiveTrustedExperienceEvidenceSet(
            workspace_id=query.workspace_id, query=query, evidence=(changed,),
            selected_count=1, truncated=False, evidence_set_fingerprint=fp,
        )
        assert evaluate(left) == evaluate(right)
    elif slot == 5:
        one = evaluate(make_set((0,)))
        many = evaluate(make_set((0,) * (variant + 2)))
        assert one.advisory_status == many.advisory_status == "exact_match"
        assert one.best_relevance_tier == many.best_relevance_tier == 0
        assert one.advisory_fingerprint != many.advisory_fingerprint
    elif slot == 6:
        normal = evaluate(make_set((0,) * 16, truncated=False))
        truncated = evaluate(make_set((0,) * 16, truncated=True))
        assert normal.advisory_status == truncated.advisory_status
        assert normal.best_relevance_tier == truncated.best_relevance_tier
        assert normal.source_evidence_set_fingerprint == truncated.source_evidence_set_fingerprint
        assert normal.advisory_fingerprint != truncated.advisory_fingerprint
    else:
        values = (None, object(), True, 1, "invalid", {"evidence": ()})
        assert evaluate(values[variant]) == evaluate(values[(variant + 1) % len(values)])


@pytest.mark.parametrize("case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d149_reproducibility_matrix(case: int) -> None:
    run_case(case)
