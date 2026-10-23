from __future__ import annotations

import hashlib
from uuid import UUID

import pytest

from app.contracts.governed_execution_experience_advisory import (
    D189_ADVISORY_POLICY,
    D189_CONTRACT_VERSION,
    D189_REFERENCE_BASELINE,
)
from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidence,
    TrustedExecutionExperienceEvidenceSet,
    TrustedExecutionExperienceRetrievalQuery,
    compute_trusted_execution_experience_evidence_set_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.trusted_execution_experience_advisory import (
    TrustedExecutionExperienceAdvisoryEvaluator,
)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def make_query(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    adapter_id: str = "adapter-a",
    operation: str = "read",
) -> TrustedExecutionExperienceRetrievalQuery:
    return TrustedExecutionExperienceRetrievalQuery(
        workspace_id=workspace_id,
        target_kind="tool",
        capability_id="capability.read",
        adapter_id=adapter_id,
        operation=operation,
        effect="read",
        risk_class="R0",
    )


def make_item(
    number: int,
    *,
    tier: int = 0,
    promotion_seed: str | None = None,
) -> TrustedExecutionExperienceEvidence:
    mapping = {
        0: ("adapter-a", "read"),
        1: ("adapter-b", "read"),
        2: ("adapter-a", "inspect"),
        3: ("adapter-b", "inspect"),
    }
    adapter_id, operation = mapping[tier]
    return TrustedExecutionExperienceEvidence(
        trusted_execution_experience_id=UUID(int=number),
        promotion_fingerprint=digest(
            promotion_seed
            if promotion_seed is not None
            else f"promotion-{number}"
        ),
        target_kind="tool",
        capability_id="capability.read",
        adapter_id=adapter_id,
        operation=operation,
        effect="read",
        risk_class="R0",
    )


def make_set(
    tiers: tuple[int, ...] = (),
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    truncated: bool = False,
    promotion_prefix: str = "promotion",
) -> TrustedExecutionExperienceEvidenceSet:
    query = make_query(workspace_id=workspace_id)
    evidence = tuple(
        make_item(
            index,
            tier=tier,
            promotion_seed=f"{promotion_prefix}-{index}",
        )
        for index, tier in enumerate(tiers, start=1)
    )
    fingerprint = (
        compute_trusted_execution_experience_evidence_set_fingerprint(
            query=query,
            evidence=evidence,
        )
    )
    return TrustedExecutionExperienceEvidenceSet(
        workspace_id=workspace_id,
        query=query,
        evidence=evidence,
        selected_count=len(evidence),
        truncated=truncated,
        evidence_set_fingerprint=fingerprint,
    )


def evaluate(value: object | None):
    return TrustedExecutionExperienceAdvisoryEvaluator.evaluate(
        evidence_set=value
    )


def test_d189_valid_empty_set_is_no_evidence_not_invalid():
    source = make_set()
    result = evaluate(source)
    assert result.advisory_status == "no_evidence"
    assert result.workspace_id is WorkspaceId.PERSONAL
    assert result.source_evidence_set_fingerprint == (
        source.evidence_set_fingerprint
    )
    assert result.source_selected_count == 0
    assert result.source_truncated is False
    assert result.best_relevance_tier is None
    assert result.mixed_relevance is False


@pytest.mark.parametrize(
    ("tier", "status"),
    (
        (0, "exact_match"),
        (1, "operation_match"),
        (2, "adapter_match"),
        (3, "capability_only"),
    ),
)
def test_d189_single_tier_status_matrix(tier: int, status: str):
    result = evaluate(make_set((tier, tier, tier)))
    assert result.advisory_status == status
    assert result.best_relevance_tier == tier
    assert result.mixed_relevance is False


@pytest.mark.parametrize(
    "tiers",
    (
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 2),
        (1, 3),
        (2, 3),
        (0, 1, 2, 3),
    ),
)
def test_d189_mixed_relevance_uses_best_tier(tiers: tuple[int, ...]):
    result = evaluate(make_set(tiers))
    assert result.advisory_status == "mixed_relevance"
    assert result.best_relevance_tier == min(tiers)
    assert result.mixed_relevance is True


def test_d189_recomputes_tier_from_fields_not_tuple_position():
    source = make_set((3, 0, 2, 1))
    result = evaluate(source)
    assert result.advisory_status == "mixed_relevance"
    assert result.best_relevance_tier == 0


def test_d189_accepts_full_sixteen_item_source():
    result = evaluate(make_set((0,) * 16))
    assert result.source_selected_count == 16
    assert result.source_truncated is False
    assert result.advisory_status == "exact_match"


def test_d189_preserves_truncation_without_changing_classification():
    normal = evaluate(make_set((0,) * 16, truncated=False))
    truncated = evaluate(make_set((0,) * 16, truncated=True))
    assert normal.advisory_status == truncated.advisory_status == "exact_match"
    assert normal.best_relevance_tier == truncated.best_relevance_tier == 0
    assert truncated.source_truncated is True


@pytest.mark.parametrize(
    "invalid",
    (None, object(), True, 1, "invalid", {"evidence": ()}),
)
def test_d189_non_d188_inputs_collapse_to_canonical_invalid(invalid):
    result = evaluate(invalid)
    assert result.advisory_status == "invalid_evidence"
    assert result.workspace_id is None
    assert result.source_evidence_set_fingerprint is None
    assert result.source_selected_count is None
    assert result.source_truncated is None
    assert result.best_relevance_tier is None
    assert result.mixed_relevance is False


def test_d189_tampered_d188_authority_fails_closed():
    source = make_set((0,))
    object.__setattr__(source.evidence[0], "execution_authority", True)
    assert evaluate(source).advisory_status == "invalid_evidence"


def test_d189_tampered_primary_match_fails_closed():
    source = make_set((0,))
    object.__setattr__(
        source.evidence[0],
        "capability_id",
        "different.capability",
    )
    assert evaluate(source).advisory_status == "invalid_evidence"


def test_d189_tampered_d188_set_fingerprint_fails_closed():
    source = make_set((0,))
    object.__setattr__(source, "evidence_set_fingerprint", "0" * 64)
    assert evaluate(source).advisory_status == "invalid_evidence"


def test_d189_contract_metadata_and_source_linkage_are_exact():
    source = make_set((1,))
    result = evaluate(source)
    assert result.contract_version == D189_CONTRACT_VERSION
    assert result.reference_baseline == D189_REFERENCE_BASELINE
    assert result.advisory_policy == D189_ADVISORY_POLICY
    assert result.workspace_id is source.workspace_id
    assert result.source_evidence_set_fingerprint == (
        source.evidence_set_fingerprint
    )
    assert result.source_selected_count == source.selected_count
    assert result.source_truncated is source.truncated
    assert len(result.advisory_fingerprint) == 64
