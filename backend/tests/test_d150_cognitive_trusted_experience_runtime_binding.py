\
from __future__ import annotations

import hashlib
from dataclasses import fields
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
    D127_TASK_DESCRIPTION_CONTRACT_VERSION,
    CognitiveTaskDescription,
)
from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidence,
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
    compute_cognitive_trusted_experience_evidence_set_fingerprint,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    D150_BINDING_POLICY,
    D150_CONTRACT_VERSION,
    D150_REFERENCE_BASELINE,
    CognitiveTrustedExperienceRuntimeBinding,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinder,
)


AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "prompt_mutation_authority",
    "policy_mutation_authority",
    "automatic_learning",
    "automatic_promotion",
)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def make_task(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    interaction_intent: str = "chat",
    cognitive_intent: str = "general",
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    normalized_request: str = "server-owned request",
) -> CognitiveTaskDescription:
    envelope = CognitiveArtifactEnvelope(
        turn_id="d150-turn",
        artifact_type=D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
        contract_version=D127_TASK_DESCRIPTION_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.TASK_UNDERSTANDING,
        workspace_id=workspace_id,
        context_snapshot_digest=digest("context"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=CognitiveOrganStatus.READY,
    )
    return CognitiveTaskDescription(
        envelope=envelope,
        interaction_intent=interaction_intent,
        cognitive_intent=cognitive_intent,
        authoritative_ai_task_kind=task_kind,
        normalized_request=normalized_request,
        required_information=("answer",),
        information_gaps=(),
        constraints=(),
    )


def make_evidence(
    query: CognitiveTrustedExperienceRetrievalQuery,
    *,
    number: int,
    tier: int,
    model: str | None = "historical-model",
) -> CognitiveTrustedExperienceEvidence:
    interaction = query.interaction_intent if tier in (0, 2) else "action_request"
    if interaction == query.interaction_intent and tier in (1, 3):
        interaction = "unknown"
    cognitive = query.cognitive_intent if tier in (0, 1) else "comparison"
    if cognitive == query.cognitive_intent and tier in (2, 3):
        cognitive = "summary"
    return CognitiveTrustedExperienceEvidence(
        trusted_experience_id=UUID(int=number),
        proposal_fingerprint=digest(f"proposal-{number}"),
        interaction_intent=interaction,
        cognitive_intent=cognitive,
        authoritative_ai_task_kind=query.authoritative_ai_task_kind,
        observed_confidence_class="sufficient",
        authorized_adapter_id="historical-adapter",
        authorized_model_id=model,
        authorized_profile_id="historical-profile",
        source_revision_count=0,
    )


def make_set(
    query: CognitiveTrustedExperienceRetrievalQuery,
    tiers: tuple[int, ...] = (),
    *,
    truncated: bool = False,
    model: str | None = "historical-model",
) -> CognitiveTrustedExperienceEvidenceSet:
    evidence = tuple(
        make_evidence(query, number=index, tier=tier, model=model)
        for index, tier in enumerate(tiers, start=1)
    )
    fingerprint = compute_cognitive_trusted_experience_evidence_set_fingerprint(
        query=query,
        evidence=evidence,
    )
    return CognitiveTrustedExperienceEvidenceSet(
        workspace_id=query.workspace_id,
        query=query,
        evidence=evidence,
        selected_count=len(evidence),
        truncated=truncated,
        evidence_set_fingerprint=fingerprint,
    )


class StubRetrieval:
    def __init__(self, factory=None, error: Exception | None = None):
        self.factory = factory or (lambda query: make_set(query))
        self.error = error
        self.calls = 0
        self.queries: list[CognitiveTrustedExperienceRetrievalQuery] = []

    def retrieve(self, query):
        self.calls += 1
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.factory(query)


def bind(
    *,
    task: CognitiveTaskDescription | None = None,
    tiers: tuple[int, ...] = (),
    truncated: bool = False,
    retrieval: StubRetrieval | None = None,
):
    task = task or make_task()
    retrieval = retrieval or StubRetrieval(
        lambda query: make_set(query, tiers, truncated=truncated)
    )
    result = CognitiveTrustedExperienceRuntimeBinder(retrieval).bind(task=task)
    return result, retrieval


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        result, retrieval = bind()
        assert result.binding_status == "bound"
        assert result.advisory_status == "no_evidence"
        assert result.source_selected_count == 0
        assert retrieval.calls == 1
    elif slot == 1:
        result, _ = bind(tiers=(0,) * (variant + 1))
        assert (result.advisory_status, result.best_relevance_tier) == ("exact_match", 0)
    elif slot == 2:
        result, _ = bind(tiers=(1,) * (variant + 1))
        assert (result.advisory_status, result.best_relevance_tier) == ("partial_match", 1)
    elif slot == 3:
        result, _ = bind(tiers=(2,) * (variant + 1))
        assert (result.advisory_status, result.best_relevance_tier) == ("partial_match", 2)
    elif slot == 4:
        result, _ = bind(tiers=(3,) * (variant + 1))
        assert (result.advisory_status, result.best_relevance_tier) == ("task_only", 3)
    elif slot == 5:
        tiers = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))[variant]
        result, _ = bind(tiers=tiers)
        assert result.advisory_status == "mixed_relevance"
        assert result.best_relevance_tier == min(tiers)
        assert result.mixed_relevance is True
    elif slot == 6:
        result, _ = bind(tiers=(0,) * 16, truncated=True)
        assert result.binding_status == "bound"
        assert result.source_selected_count == 16
        assert result.source_truncated is True
    elif slot == 7:
        retrieval = StubRetrieval(error=RuntimeError("unavailable"))
        result, retrieval = bind(retrieval=retrieval)
        assert result.binding_status == "unavailable"
        assert result.advisory_status is None
        assert retrieval.calls == 1
    elif slot == 8:
        def factory(query):
            source = make_set(query, (0,))
            object.__setattr__(source.evidence[0], "routing_authority", True)
            return source
        result, retrieval = bind(retrieval=StubRetrieval(factory))
        assert result.binding_status == "unavailable"
        assert retrieval.calls == 1
    elif slot == 9:
        def factory(query):
            source = make_set(query, (0,))
            other = (
                WorkspaceId.COMPANY
                if query.workspace_id is WorkspaceId.PERSONAL
                else WorkspaceId.PERSONAL
            )
            object.__setattr__(source, "workspace_id", other)
            return source
        result, _ = bind(retrieval=StubRetrieval(factory))
        assert result.binding_status == "unavailable"
    elif slot == 10:
        workspace = WorkspaceId.COMPANY if variant % 2 else WorkspaceId.PERSONAL
        task = make_task(
            workspace_id=workspace,
            interaction_intent="action_request" if variant % 2 else "chat",
            cognitive_intent="troubleshooting" if variant % 2 else "general",
            task_kind=(
                AITaskKind.SOFTWARE_ENGINEERING
                if variant % 2
                else AITaskKind.GENERAL_CHAT
            ),
        )
        result, retrieval = bind(task=task)
        query = retrieval.queries[0]
        assert query.workspace_id is task.envelope.workspace_id
        assert query.interaction_intent == task.interaction_intent
        assert query.cognitive_intent == task.cognitive_intent
        assert query.authoritative_ai_task_kind is task.authoritative_ai_task_kind
        assert result.workspace_id is workspace
    elif slot == 11:
        left_task = make_task(normalized_request=f"secret-a-{variant}")
        right_task = make_task(normalized_request=f"secret-b-{variant}")
        _, left = bind(task=left_task)
        _, right = bind(task=right_task)
        assert left.queries[0] == right.queries[0]
        assert "normalized_request" not in {
            field.name
            for field in fields(CognitiveTrustedExperienceRetrievalQuery)
        }
    elif slot == 12:
        result, _ = bind(tiers=(0,))
        names = {field.name for field in fields(CognitiveTrustedExperienceRuntimeBinding)}
        assert {
            "authorized_adapter_id",
            "authorized_model_id",
            "authorized_profile_id",
        }.isdisjoint(names)
        assert result.advisory_status == "exact_match"
    elif slot == 13:
        retrieval = StubRetrieval(lambda query: make_set(query, (0,)))
        result, retrieval = bind(retrieval=retrieval)
        assert retrieval.calls == 1
        assert result.binding_status == "bound"
    elif slot == 14:
        task = make_task()
        object.__setattr__(task, "interaction_intent", "INVALID")
        result, retrieval = bind(task=task)
        assert result.binding_status == "unavailable"
        assert retrieval.calls == 0
    else:
        result, _ = bind(tiers=(variant % 4,))
        assert result.contract_version == D150_CONTRACT_VERSION
        assert result.reference_baseline == D150_REFERENCE_BASELINE
        assert result.binding_policy == D150_BINDING_POLICY
        names = {field.name for field in fields(CognitiveTrustedExperienceRuntimeBinding)}
        assert names == {
            "contract_version",
            "reference_baseline",
            "binding_policy",
            "binding_status",
            "workspace_id",
            "source_evidence_set_fingerprint",
            "source_selected_count",
            "source_truncated",
            "advisory_status",
            "best_relevance_tier",
            "mixed_relevance",
            "advisory_fingerprint",
        }
        assert set(AUTHORITY_FIELDS).isdisjoint(names)


@pytest.mark.parametrize(
    "case",
    range(1, 97),
    ids=[f"F{i:02d}" for i in range(1, 97)],
)
def test_d150_functional_matrix(case: int) -> None:
    run_case(case)
