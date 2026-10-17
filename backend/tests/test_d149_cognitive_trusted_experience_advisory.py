from __future__ import annotations

import hashlib
from uuid import UUID

import pytest

from app.contracts.cognitive_trusted_experience_advisory import (
    D149_ADVISORY_POLICY,
    D149_CONTRACT_VERSION,
    D149_REFERENCE_BASELINE,
)
from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidence,
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
    compute_cognitive_trusted_experience_evidence_set_fingerprint,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisoryEvaluator,
)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def make_query(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
) -> CognitiveTrustedExperienceRetrievalQuery:
    return CognitiveTrustedExperienceRetrievalQuery(
        workspace_id=workspace_id,
        interaction_intent="chat",
        cognitive_intent="general",
        authoritative_ai_task_kind=task_kind,
    )


def make_item(
    number: int,
    *,
    tier: int = 0,
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    adapter: str | None = "adapter-a",
    model: str | None = "model-a",
    profile: str | None = "profile-a",
    proposal_seed: str | None = None,
) -> CognitiveTrustedExperienceEvidence:
    mapping = {
        0: ("chat", "general"),
        1: ("action_request", "general"),
        2: ("chat", "comparison"),
        3: ("action_request", "comparison"),
    }
    interaction, cognitive = mapping[tier]
    return CognitiveTrustedExperienceEvidence(
        trusted_experience_id=UUID(int=number),
        proposal_fingerprint=digest(
            proposal_seed if proposal_seed is not None else f"proposal-{number}"
        ),
        interaction_intent=interaction,
        cognitive_intent=cognitive,
        authoritative_ai_task_kind=task_kind,
        observed_confidence_class="sufficient",
        authorized_adapter_id=adapter,
        authorized_model_id=model,
        authorized_profile_id=profile,
        source_revision_count=0,
    )


def make_set(
    tiers: tuple[int, ...] = (),
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    truncated: bool = False,
    proposal_prefix: str = "proposal",
) -> CognitiveTrustedExperienceEvidenceSet:
    query = make_query(workspace_id=workspace_id)
    evidence = tuple(
        make_item(
            index,
            tier=tier,
            proposal_seed=f"{proposal_prefix}-{index}",
        )
        for index, tier in enumerate(tiers, start=1)
    )
    fp = compute_cognitive_trusted_experience_evidence_set_fingerprint(
        query=query,
        evidence=evidence,
    )
    return CognitiveTrustedExperienceEvidenceSet(
        workspace_id=workspace_id,
        query=query,
        evidence=evidence,
        selected_count=len(evidence),
        truncated=truncated,
        evidence_set_fingerprint=fp,
    )


def evaluate(value: object | None):
    return CognitiveTrustedExperienceAdvisoryEvaluator.evaluate(
        evidence_set=value
    )


MIXED = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        result = evaluate(make_set())
        assert result.advisory_status == "no_evidence"
        assert result.best_relevance_tier is None
        assert result.mixed_relevance is False
    elif slot == 1:
        result = evaluate(make_set((0,) * (variant + 1)))
        assert (result.advisory_status, result.best_relevance_tier, result.mixed_relevance) == ("exact_match", 0, False)
    elif slot == 2:
        result = evaluate(make_set((1,) * (variant + 1)))
        assert (result.advisory_status, result.best_relevance_tier, result.mixed_relevance) == ("partial_match", 1, False)
    elif slot == 3:
        result = evaluate(make_set((2,) * (variant + 1)))
        assert (result.advisory_status, result.best_relevance_tier, result.mixed_relevance) == ("partial_match", 2, False)
    elif slot == 4:
        result = evaluate(make_set((3,) * (variant + 1)))
        assert (result.advisory_status, result.best_relevance_tier, result.mixed_relevance) == ("task_only", 3, False)
    elif 5 <= slot <= 10:
        tiers = MIXED[slot - 5]
        result = evaluate(make_set(tiers))
        assert result.advisory_status == "mixed_relevance"
        assert result.best_relevance_tier == min(tiers)
        assert result.mixed_relevance is True
    elif slot == 11:
        result = evaluate(make_set((0,) * 16))
        assert result.source_selected_count == 16
        assert result.advisory_status == "exact_match"
    elif slot == 12:
        result = evaluate(make_set((0,) * 16, truncated=True))
        assert result.source_selected_count == 16
        assert result.source_truncated is True
        assert result.advisory_status == "exact_match"
    elif slot == 13:
        bad = (None, object(), True, 1, "bad", {"evidence": ()})[variant]
        result = evaluate(bad)
        assert result.advisory_status == "invalid_evidence"
        assert result.workspace_id is None
        assert result.source_evidence_set_fingerprint is None
        assert result.source_selected_count is None
        assert result.source_truncated is None
        assert result.best_relevance_tier is None
        assert result.mixed_relevance is False
    elif slot == 14:
        source = make_set((0,))
        object.__setattr__(
            source.evidence[0],
            "authoritative_ai_task_kind",
            AITaskKind.SOFTWARE_ENGINEERING,
        )
        assert evaluate(source).advisory_status == "invalid_evidence"
    else:
        source = make_set((variant % 4,))
        result = evaluate(source)
        assert result.contract_version == D149_CONTRACT_VERSION
        assert result.reference_baseline == D149_REFERENCE_BASELINE
        assert result.advisory_policy == D149_ADVISORY_POLICY
        assert result.workspace_id is source.workspace_id
        assert result.source_evidence_set_fingerprint == source.evidence_set_fingerprint
        assert result.source_selected_count == source.selected_count
        assert result.source_truncated is source.truncated
        assert len(result.advisory_fingerprint) == 64


@pytest.mark.parametrize("case", range(1, 97), ids=[f"F{i:02d}" for i in range(1, 97)])
def test_d149_functional_matrix(case: int) -> None:
    run_case(case)
