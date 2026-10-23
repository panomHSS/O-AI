from __future__ import annotations

from dataclasses import replace

from app.contracts.governed_execution_experience_advisory import (
    ExecutionExperienceAdvisory,
    compute_execution_experience_advisory_fingerprint,
)
from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidenceSet,
    compute_trusted_execution_experience_evidence_set_fingerprint,
)
from app.services.trusted_execution_experience_advisory import (
    TrustedExecutionExperienceAdvisoryEvaluator,
)
from tests.test_d189_execution_experience_advisory import (
    digest,
    evaluate,
    make_item,
    make_query,
    make_set,
)


def test_d189_identical_valid_input_is_reproducible():
    source = make_set((0, 1, 3))
    assert evaluate(source) == evaluate(source)


def test_d189_evaluator_instances_are_stateless():
    source = make_set((0, 2))
    left = TrustedExecutionExperienceAdvisoryEvaluator()
    right = TrustedExecutionExperienceAdvisoryEvaluator()
    assert left.evaluate(evidence_set=source) == right.evaluate(
        evidence_set=source
    )
    assert vars(left) == vars(right) == {}


def test_d189_fingerprint_recomputes_from_frozen_payload():
    result = evaluate(make_set((1, 3)))
    expected = compute_execution_experience_advisory_fingerprint(
        workspace_id=result.workspace_id,
        source_evidence_set_fingerprint=(
            result.source_evidence_set_fingerprint
        ),
        source_selected_count=result.source_selected_count,
        source_truncated=result.source_truncated,
        advisory_status=result.advisory_status,
        best_relevance_tier=result.best_relevance_tier,
        mixed_relevance=result.mixed_relevance,
    )
    assert result.advisory_fingerprint == expected


def test_d189_source_identity_change_changes_advisory_fingerprint():
    query = make_query()
    first = make_item(1, tier=0, promotion_seed="alpha")
    second = replace(
        first,
        promotion_fingerprint=digest("beta"),
    )
    left_fp = compute_trusted_execution_experience_evidence_set_fingerprint(
        query=query,
        evidence=(first,),
    )
    right_fp = compute_trusted_execution_experience_evidence_set_fingerprint(
        query=query,
        evidence=(second,),
    )
    left = TrustedExecutionExperienceEvidenceSet(
        workspace_id=query.workspace_id,
        query=query,
        evidence=(first,),
        selected_count=1,
        truncated=False,
        evidence_set_fingerprint=left_fp,
    )
    right = TrustedExecutionExperienceEvidenceSet(
        workspace_id=query.workspace_id,
        query=query,
        evidence=(second,),
        selected_count=1,
        truncated=False,
        evidence_set_fingerprint=right_fp,
    )
    assert evaluate(left).advisory_status == "exact_match"
    assert evaluate(right).advisory_status == "exact_match"
    assert evaluate(left).advisory_fingerprint != (
        evaluate(right).advisory_fingerprint
    )


def test_d189_source_count_changes_advisory_fingerprint():
    one = evaluate(make_set((0,)))
    many = evaluate(make_set((0, 0, 0)))
    assert one.advisory_status == many.advisory_status == "exact_match"
    assert one.advisory_fingerprint != many.advisory_fingerprint


def test_d189_truncation_changes_advisory_fingerprint():
    normal = evaluate(make_set((0,) * 16, truncated=False))
    truncated = evaluate(make_set((0,) * 16, truncated=True))
    assert normal.source_evidence_set_fingerprint == (
        truncated.source_evidence_set_fingerprint
    )
    assert normal.advisory_status == truncated.advisory_status
    assert normal.advisory_fingerprint != truncated.advisory_fingerprint


def test_d189_ordered_d188_evidence_identity_propagates_to_fingerprint():
    source = make_set((0, 1, 2))
    reordered_evidence = tuple(reversed(source.evidence))
    reordered_fp = (
        compute_trusted_execution_experience_evidence_set_fingerprint(
            query=source.query,
            evidence=reordered_evidence,
        )
    )
    reordered = TrustedExecutionExperienceEvidenceSet(
        workspace_id=source.workspace_id,
        query=source.query,
        evidence=reordered_evidence,
        selected_count=source.selected_count,
        truncated=False,
        evidence_set_fingerprint=reordered_fp,
    )
    assert evaluate(source).advisory_status == (
        evaluate(reordered).advisory_status
    )
    assert evaluate(source).advisory_fingerprint != (
        evaluate(reordered).advisory_fingerprint
    )


def test_d189_invalid_inputs_share_one_canonical_result():
    values = (None, object(), True, 1, "invalid", {"evidence": ()})
    results = [evaluate(value) for value in values]
    assert all(result == results[0] for result in results)


def test_d189_contract_rejects_fingerprint_tampering():
    result = evaluate(make_set((0,)))
    try:
        replace(result, advisory_fingerprint="0" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered advisory fingerprint was accepted")


def test_d189_manual_fingerprint_function_is_deterministic():
    result = evaluate(make_set())
    first = compute_execution_experience_advisory_fingerprint(
        workspace_id=result.workspace_id,
        source_evidence_set_fingerprint=result.source_evidence_set_fingerprint,
        source_selected_count=result.source_selected_count,
        source_truncated=result.source_truncated,
        advisory_status=result.advisory_status,
        best_relevance_tier=result.best_relevance_tier,
        mixed_relevance=result.mixed_relevance,
    )
    second = compute_execution_experience_advisory_fingerprint(
        workspace_id=result.workspace_id,
        source_evidence_set_fingerprint=result.source_evidence_set_fingerprint,
        source_selected_count=result.source_selected_count,
        source_truncated=result.source_truncated,
        advisory_status=result.advisory_status,
        best_relevance_tier=result.best_relevance_tier,
        mixed_relevance=result.mixed_relevance,
    )
    assert first == second == result.advisory_fingerprint
