from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from typing import get_args

import pytest

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AIAdapterDiscovery,
    AIModelDescriptor,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
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
from app.contracts.cognitive_model_intelligence import (
    D135_DISCOVERY_CAPABILITY_MAX_COUNT,
    D135_DISCOVERY_INPUT_DIGEST_VERSION,
    D135_DISCOVERY_MODEL_MAX_COUNT,
    D135_EVALUATION_EVIDENCE_MAX_COUNT,
    D135_EVALUATION_SOURCE_KIND,
    D135_MODEL_CAPABILITY_ARTIFACT_TYPE,
    D135_MODEL_CAPABILITY_CONTRACT_VERSION,
    D135_MODEL_CAPABILITY_FINGERPRINT_VERSION,
    D135_OBSERVED_LATENCY_MS_MAX,
    D135_PROFILE_INPUT_DIGEST_VERSION,
    D135_VERIFIED_CONTEXT_TOKENS_MAX,
    CognitiveModelCapabilityKnowledgeArtifact,
    ModelCapabilityConflictCode,
    ModelCapabilityEvaluationEvidence,
    ModelCapabilityEvaluationSupport,
    ModelCapabilityLimitationCode,
    ModelCapabilitySupport,
    ModelLocality,
)
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
    LocalAIProfile,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_model_intelligence import (
    CognitiveModelIntelligenceCoordinator,
    _discovery_input_digest,
    _profile_input_digest,
)


NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
CONTEXT_A = "a" * 64
CONTEXT_B = "b" * 64
SOURCE_A = "1" * 64
SOURCE_B = "2" * 64
SOURCE_C = "3" * 64


def task_envelope(
    *,
    turn_id: str = "turn-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    context_digest: str | None = CONTEXT_A,
    created_at: datetime = NOW,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id,
        artifact_type=D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
        contract_version=D127_TASK_DESCRIPTION_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.TASK_UNDERSTANDING,
        workspace_id=workspace_id,
        context_snapshot_digest=context_digest,
        created_at=created_at,
        status=CognitiveOrganStatus.READY,
        input_reference_digests=(),
        model_binding_reference=None,
    )


def make_task(
    *,
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    turn_id: str = "turn-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    context_digest: str | None = CONTEXT_A,
    created_at: datetime = NOW,
) -> CognitiveTaskDescription:
    return CognitiveTaskDescription(
        envelope=task_envelope(
            turn_id=turn_id,
            workspace_id=workspace_id,
            context_digest=context_digest,
            created_at=created_at,
        ),
        interaction_intent="chat",
        cognitive_intent="general",
        authoritative_ai_task_kind=task_kind,
        normalized_request="Explain the result",
        required_information=("result",),
        information_gaps=(),
        constraints=(),
    )


def make_discovery(
    *,
    adapter_id: str = LOCAL_AI_ADAPTER_ID,
    status: str = "available",
    configured_model_id: str | None = "model-a",
    capability_ids: tuple[str, ...] = (AI_CAPABILITY_TEXT_GENERATION,),
    models: tuple[AIModelDescriptor, ...] | None = None,
    reason_code: str = "models_discovered",
) -> AIAdapterDiscovery:
    if models is None:
        models = (
            AIModelDescriptor(
                model_id="model-a",
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            ),
        )
    return AIAdapterDiscovery(
        adapter_id=adapter_id,
        status=status,
        configured_model_id=configured_model_id,
        capability_ids=capability_ids,
        models=models,
        reason_code=reason_code,
    )


def make_profile(
    *,
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    model_id: str = "model-a",
    timeout_seconds: float = 90.0,
    context_length: int = 4096,
    reasoning_enabled: bool | None = None,
) -> LocalAIProfile:
    return LocalAIProfile(
        profile_id=(
            GENERAL_CHAT_PROFILE_ID
            if task_kind is AITaskKind.GENERAL_CHAT
            else SOFTWARE_ENGINEERING_PROFILE_ID
        ),
        task_kind=task_kind,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        context_length=context_length,
        reasoning_enabled=reasoning_enabled,
    )


def make_evidence(
    evidence_id: str,
    *,
    source_digest: str = SOURCE_A,
    adapter_id: str = LOCAL_AI_ADAPTER_ID,
    model_id: str = "model-a",
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    task_fit: str | None = None,
    reasoning_support: str | None = None,
    structured_output_support: str | None = None,
    verified_context_tokens: int | None = None,
    observed_latency_ms: int | None = None,
) -> ModelCapabilityEvaluationEvidence:
    return ModelCapabilityEvaluationEvidence(
        evidence_id=evidence_id,
        source_kind=D135_EVALUATION_SOURCE_KIND,
        source_digest=source_digest,
        adapter_id=adapter_id,
        model_id=model_id,
        task_kind=task_kind,
        task_fit=task_fit,
        reasoning_support=reasoning_support,
        structured_output_support=structured_output_support,
        verified_context_tokens=verified_context_tokens,
        observed_latency_ms=observed_latency_ms,
    )


def refs_for(
    discovery: AIAdapterDiscovery,
    profile: LocalAIProfile | None,
    evidence: tuple[ModelCapabilityEvaluationEvidence, ...] = (),
) -> tuple[str, ...]:
    canonical = tuple(sorted(evidence, key=lambda item: item.evidence_id))
    source_digests = tuple(sorted({item.source_digest for item in canonical}))
    return (
        _discovery_input_digest(discovery),
        *((_profile_input_digest(profile),) if profile is not None else ()),
        *source_digests,
    )


def model_envelope(
    task: CognitiveTaskDescription,
    refs: tuple[str, ...],
    *,
    created_at: datetime = NOW,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=task.envelope.turn_id,
        artifact_type=D135_MODEL_CAPABILITY_ARTIFACT_TYPE,
        contract_version=D135_MODEL_CAPABILITY_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.MODEL_INTELLIGENCE,
        workspace_id=task.envelope.workspace_id,
        context_snapshot_digest=task.envelope.context_snapshot_digest,
        created_at=created_at,
        status=CognitiveOrganStatus.READY,
        input_reference_digests=refs,
        model_binding_reference=None,
    )


def form(
    *,
    task: CognitiveTaskDescription | None = None,
    discovery: AIAdapterDiscovery | None = None,
    target_model_id: str = "model-a",
    profile: LocalAIProfile | None = None,
    evidence: tuple[ModelCapabilityEvaluationEvidence, ...] = (),
    created_at: datetime = NOW,
) -> CognitiveModelCapabilityKnowledgeArtifact:
    task = task or make_task()
    discovery = discovery or make_discovery()
    envelope = model_envelope(
        task,
        refs_for(discovery, profile, evidence),
        created_at=created_at,
    )
    return CognitiveModelIntelligenceCoordinator().form_knowledge(
        envelope,
        task,
        discovery,
        target_model_id=target_model_id,
        local_profile=profile,
        evaluation_evidence=evidence,
    )


# F01
def test_f01_exact_constants():
    assert D135_MODEL_CAPABILITY_ARTIFACT_TYPE == "cognitive.model_capability_knowledge"
    assert D135_MODEL_CAPABILITY_CONTRACT_VERSION == "o-ai.cognitive-model-capability-knowledge.v1"
    assert D135_MODEL_CAPABILITY_FINGERPRINT_VERSION == "o-ai.cognitive-model-capability-fingerprint.v1"
    assert D135_DISCOVERY_INPUT_DIGEST_VERSION == "o-ai.d135.discovery-input.v1"
    assert D135_PROFILE_INPUT_DIGEST_VERSION == "o-ai.d135.profile-input.v1"


# F02
def test_f02_exact_support_vocabularies():
    assert set(get_args(ModelCapabilitySupport)) == {
        "supported", "limited", "unsupported", "unknown", "conflicted"
    }
    assert set(get_args(ModelCapabilityEvaluationSupport)) == {
        "supported", "limited", "unsupported"
    }


# F03
def test_f03_exact_locality_limitation_conflict_vocabularies():
    assert set(get_args(ModelLocality)) == {"local", "cloud", "unknown"}
    assert get_args(ModelCapabilityLimitationCode) == (
        "task_fit_limited",
        "task_fit_unsupported",
        "reasoning_limited",
        "reasoning_unsupported",
        "structured_output_limited",
        "structured_output_unsupported",
    )
    assert get_args(ModelCapabilityConflictCode) == (
        "task_fit_conflict",
        "reasoning_support_conflict",
        "structured_output_support_conflict",
    )


# F04
def test_f04_exact_evaluation_source_kind_and_numeric_count_bounds():
    assert D135_EVALUATION_SOURCE_KIND == "server_evaluation"
    assert D135_EVALUATION_EVIDENCE_MAX_COUNT == 32
    assert D135_DISCOVERY_MODEL_MAX_COUNT == 256
    assert D135_DISCOVERY_CAPABILITY_MAX_COUNT == 32
    assert D135_VERIFIED_CONTEXT_TOKENS_MAX == 10_000_000
    assert D135_OBSERVED_LATENCY_MS_MAX == 3_600_000


# F05
def test_f05_valid_task_fit_evidence():
    item = make_evidence("e1", task_fit="supported")
    assert item.task_fit == "supported"


# F06
def test_f06_valid_reasoning_evidence():
    item = make_evidence("e1", reasoning_support="limited")
    assert item.reasoning_support == "limited"


# F07
def test_f07_valid_structured_output_evidence():
    item = make_evidence("e1", structured_output_support="unsupported")
    assert item.structured_output_support == "unsupported"


# F08
def test_f08_valid_context_and_latency_evidence():
    item = make_evidence(
        "e1",
        verified_context_tokens=8192,
        observed_latency_ms=321,
    )
    assert item.verified_context_tokens == 8192
    assert item.observed_latency_ms == 321


# F09
def test_f09_discovered_target_text_generation_supported():
    artifact = form()
    assert artifact.model_discovered is True
    assert artifact.text_generation_support == "supported"


# F10
def test_f10_discovered_target_without_text_generation_unsupported():
    discovery = make_discovery(
        capability_ids=("embeddings",),
        models=(AIModelDescriptor("model-a", ("embeddings",)),),
    )
    artifact = form(discovery=discovery)
    assert artifact.model_discovered is True
    assert artifact.text_generation_support == "unsupported"


# F11
def test_f11_absent_target_not_discovered_and_text_generation_unknown():
    artifact = form(target_model_id="model-b")
    assert artifact.model_discovered is False
    assert artifact.text_generation_support == "unknown"


# F12
def test_f12_unavailable_adapter_preserves_discovered_target():
    discovery = make_discovery(status="unavailable", reason_code="runtime_unavailable")
    artifact = form(discovery=discovery)
    assert artifact.adapter_discovery_status == "unavailable"
    assert artifact.model_discovered is True


# F13
def test_f13_configured_model_id_alone_does_not_prove_discovery():
    discovery = make_discovery(models=(), configured_model_id="model-a")
    artifact = form(discovery=discovery)
    assert artifact.model_discovered is False
    assert artifact.text_generation_support == "unknown"


# F14
def test_f14_exact_discovery_status_reason_projection():
    discovery = make_discovery(status="unavailable", reason_code="future_safe_reason")
    artifact = form(discovery=discovery)
    assert artifact.adapter_discovery_status == "unavailable"
    assert artifact.discovery_reason_code == "future_safe_reason"


# F15
def test_f15_local_ai_locality():
    assert form().locality == "local"


# F16
def test_f16_chatgpt_cloud_locality():
    discovery = make_discovery(
        adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        configured_model_id="gpt-x",
        models=(AIModelDescriptor("gpt-x", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = form(discovery=discovery, target_model_id="gpt-x")
    assert artifact.locality == "cloud"


# F17
def test_f17_unknown_adapter_locality():
    discovery = make_discovery(
        adapter_id="future.adapter",
        configured_model_id="future-model",
        models=(AIModelDescriptor("future-model", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = form(discovery=discovery, target_model_id="future-model")
    assert artifact.locality == "unknown"


# F18
def test_f18_general_chat_profile_projection():
    profile = make_profile(context_length=8192, reasoning_enabled=True)
    artifact = form(profile=profile)
    assert artifact.profile_id == GENERAL_CHAT_PROFILE_ID
    assert artifact.configured_context_length == 8192
    assert artifact.configured_reasoning_policy is True


# F19
def test_f19_software_engineering_profile_projection():
    task = make_task(task_kind=AITaskKind.SOFTWARE_ENGINEERING)
    profile = make_profile(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        context_length=16384,
        reasoning_enabled=False,
    )
    evidence = (
        make_evidence(
            "e1",
            task_kind=AITaskKind.SOFTWARE_ENGINEERING,
            task_fit="supported",
        ),
    )
    artifact = form(task=task, profile=profile, evidence=evidence)
    assert artifact.profile_id == SOFTWARE_ENGINEERING_PROFILE_ID
    assert artifact.task_kind is AITaskKind.SOFTWARE_ENGINEERING


# F20
def test_f20_local_ai_model_may_be_described_without_profile():
    artifact = form(profile=None)
    assert artifact.adapter_id == LOCAL_AI_ADAPTER_ID
    assert artifact.profile_id is None


# F21
def test_f21_configured_context_separate_from_verified_context():
    profile = make_profile(context_length=8192)
    evidence = (make_evidence("e1", verified_context_tokens=4096),)
    artifact = form(profile=profile, evidence=evidence)
    assert artifact.configured_context_length == 8192
    assert artifact.max_verified_context_tokens == 4096


# F22
def test_f22_configured_reasoning_policy_separate_from_reasoning_support():
    profile = make_profile(reasoning_enabled=True)
    artifact = form(profile=profile)
    assert artifact.configured_reasoning_policy is True
    assert artifact.reasoning_support == "unknown"


# F23
def test_f23_no_evidence_unknown_evaluated_supports():
    artifact = form()
    assert (
        artifact.task_fit,
        artifact.reasoning_support,
        artifact.structured_output_support,
    ) == ("unknown", "unknown", "unknown")


# F24
def test_f24_unanimous_supported_aggregation():
    evidence = (
        make_evidence("e1", task_fit="supported"),
        make_evidence("e2", source_digest=SOURCE_B, task_fit="supported"),
    )
    assert form(evidence=evidence).task_fit == "supported"


# F25
def test_f25_unanimous_limited_aggregation():
    evidence = (
        make_evidence("e1", reasoning_support="limited"),
        make_evidence("e2", source_digest=SOURCE_B, reasoning_support="limited"),
    )
    assert form(evidence=evidence).reasoning_support == "limited"


# F26
def test_f26_unanimous_unsupported_aggregation():
    evidence = (
        make_evidence("e1", structured_output_support="unsupported"),
        make_evidence("e2", source_digest=SOURCE_B, structured_output_support="unsupported"),
    )
    assert form(evidence=evidence).structured_output_support == "unsupported"


# F27
def test_f27_task_fit_conflict_aggregation():
    evidence = (
        make_evidence("e1", task_fit="supported"),
        make_evidence("e2", source_digest=SOURCE_B, task_fit="unsupported"),
    )
    assert form(evidence=evidence).task_fit == "conflicted"


# F28
def test_f28_reasoning_conflict_aggregation():
    evidence = (
        make_evidence("e1", reasoning_support="limited"),
        make_evidence("e2", source_digest=SOURCE_B, reasoning_support="supported"),
    )
    assert form(evidence=evidence).reasoning_support == "conflicted"


# F29
def test_f29_structured_output_conflict_aggregation():
    evidence = (
        make_evidence("e1", structured_output_support="limited"),
        make_evidence("e2", source_digest=SOURCE_B, structured_output_support="unsupported"),
    )
    assert form(evidence=evidence).structured_output_support == "conflicted"


# F30
def test_f30_max_verified_context_from_explicit_observations():
    evidence = (
        make_evidence("e1", verified_context_tokens=2048),
        make_evidence("e2", source_digest=SOURCE_B, verified_context_tokens=16384),
        make_evidence("e3", source_digest=SOURCE_C, verified_context_tokens=8192),
    )
    assert form(evidence=evidence).max_verified_context_tokens == 16384


# F31
def test_f31_absent_verified_context_is_none():
    evidence = (make_evidence("e1", task_fit="supported"),)
    assert form(evidence=evidence).max_verified_context_tokens is None


# F32
def test_f32_latency_observations_canonical_order():
    evidence = (
        make_evidence("z", source_digest=SOURCE_B, observed_latency_ms=900),
        make_evidence("a", source_digest=SOURCE_A, observed_latency_ms=100),
    )
    artifact = form(evidence=evidence)
    assert tuple(item.evidence_id for item in artifact.evaluation_evidence) == ("a", "z")
    assert artifact.latency_observations_ms == (100, 900)


# F33
def test_f33_absent_latency_is_empty_tuple():
    assert form().latency_observations_ms == ()


# F34
def test_f34_limitation_codes_exact_derived_order():
    evidence = (
        make_evidence(
            "e1",
            task_fit="limited",
            reasoning_support="unsupported",
            structured_output_support="limited",
        ),
    )
    assert form(evidence=evidence).limitation_codes == (
        "task_fit_limited",
        "reasoning_unsupported",
        "structured_output_limited",
    )


# F35
def test_f35_conflict_codes_exact_derived_order():
    evidence = (
        make_evidence(
            "e1",
            task_fit="supported",
            reasoning_support="limited",
            structured_output_support="unsupported",
        ),
        make_evidence(
            "e2",
            source_digest=SOURCE_B,
            task_fit="unsupported",
            reasoning_support="supported",
            structured_output_support="limited",
        ),
    )
    assert form(evidence=evidence).evidence_conflict_codes == (
        "task_fit_conflict",
        "reasoning_support_conflict",
        "structured_output_support_conflict",
    )


# F36
def test_f36_evidence_canonicalized_by_evidence_id():
    evidence = (
        make_evidence("z", task_fit="supported"),
        make_evidence("a", source_digest=SOURCE_B, task_fit="supported"),
    )
    assert tuple(item.evidence_id for item in form(evidence=evidence).evaluation_evidence) == (
        "a",
        "z",
    )


# F37
def test_f37_source_digests_unique_and_sorted():
    evidence = (
        make_evidence("c", source_digest=SOURCE_B, task_fit="supported"),
        make_evidence("a", source_digest=SOURCE_A, task_fit="supported"),
        make_evidence("b", source_digest=SOURCE_A, reasoning_support="limited"),
    )
    artifact = form(evidence=evidence)
    assert artifact.envelope.input_reference_digests[1:] == (SOURCE_A, SOURCE_B)


# F38
def test_f38_discovery_digest_deterministic():
    discovery = make_discovery()
    assert _discovery_input_digest(discovery) == _discovery_input_digest(discovery)


# F39
def test_f39_profile_digest_deterministic():
    profile = make_profile()
    assert _profile_input_digest(profile) == _profile_input_digest(profile)


# F40
def test_f40_fingerprint_deterministic():
    evidence = (make_evidence("e1", task_fit="supported"),)
    first = form(evidence=evidence)
    second = form(evidence=evidence)
    assert first.knowledge_fingerprint == second.knowledge_fingerprint


# F41
def test_f41_fingerprint_independent_of_turn_workspace_context_time_identity():
    discovery = make_discovery()
    evidence = (make_evidence("e1", task_fit="supported"),)
    first = form(
        task=make_task(
            turn_id="turn-a",
            workspace_id=WorkspaceId.PERSONAL,
            context_digest=CONTEXT_A,
            created_at=NOW,
        ),
        discovery=discovery,
        evidence=evidence,
        created_at=NOW,
    )
    later = datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    second = form(
        task=make_task(
            turn_id="turn-b",
            workspace_id=WorkspaceId.COMPANY,
            context_digest=CONTEXT_B,
            created_at=later,
        ),
        discovery=discovery,
        evidence=evidence,
        created_at=later,
    )
    assert first.knowledge_fingerprint == second.knowledge_fingerprint


# F42
def test_f42_fingerprint_changes_with_discovery_facts_digest():
    first = form(discovery=make_discovery(reason_code="reason_a"))
    second = form(discovery=make_discovery(reason_code="reason_b"))
    assert first.knowledge_fingerprint != second.knowledge_fingerprint


# F43
def test_f43_fingerprint_changes_with_profile_facts_digest():
    first = form(profile=make_profile(context_length=4096))
    second = form(profile=make_profile(context_length=8192))
    assert first.knowledge_fingerprint != second.knowledge_fingerprint


# F44
def test_f44_fingerprint_changes_with_evaluation_facts_source_digests():
    first = form(evidence=(make_evidence("e1", source_digest=SOURCE_A, task_fit="supported"),))
    second = form(evidence=(make_evidence("e1", source_digest=SOURCE_B, task_fit="supported"),))
    assert first.knowledge_fingerprint != second.knowledge_fingerprint


# F45
def test_f45_artifact_evidence_frozen_slots_exact_public_output_field_surface():
    evidence = make_evidence("e1", task_fit="supported")
    artifact = form(evidence=(evidence,))
    assert not hasattr(evidence, "__dict__")
    assert not hasattr(artifact, "__dict__")
    with pytest.raises(FrozenInstanceError):
        evidence.evidence_id = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        artifact.model_id = "other"  # type: ignore[misc]
    assert tuple(item.name for item in fields(CognitiveModelCapabilityKnowledgeArtifact)) == (
        "envelope",
        "task_kind",
        "adapter_id",
        "model_id",
        "profile_id",
        "adapter_discovery_status",
        "discovery_reason_code",
        "model_discovered",
        "text_generation_support",
        "locality",
        "configured_context_length",
        "configured_reasoning_policy",
        "task_fit",
        "reasoning_support",
        "structured_output_support",
        "max_verified_context_tokens",
        "latency_observations_ms",
        "limitation_codes",
        "evidence_conflict_codes",
        "evaluation_evidence",
        "knowledge_fingerprint",
    )


# F46
def test_f46_exact_repeated_invocation_idempotent():
    task = make_task()
    discovery = make_discovery()
    evidence = (make_evidence("e1", task_fit="supported"),)
    envelope = model_envelope(task, refs_for(discovery, None, evidence))
    coordinator = CognitiveModelIntelligenceCoordinator()
    first = coordinator.form_knowledge(
        envelope,
        task,
        discovery,
        target_model_id="model-a",
        evaluation_evidence=evidence,
    )
    second = coordinator.form_knowledge(
        envelope,
        task,
        discovery,
        target_model_id="model-a",
        evaluation_evidence=evidence,
    )
    assert first == second


# F47
def test_f47_source_objects_remain_unchanged():
    task = make_task()
    discovery = make_discovery()
    profile = make_profile()
    evidence = (make_evidence("e1", task_fit="supported"),)
    snapshots = (repr(task), repr(discovery), repr(profile), repr(evidence))
    form(task=task, discovery=discovery, profile=profile, evidence=evidence)
    assert snapshots == (repr(task), repr(discovery), repr(profile), repr(evidence))


# F48
def test_f48_caller_evidence_ordering_does_not_change_canonical_fingerprint():
    a = make_evidence("a", source_digest=SOURCE_A, task_fit="supported")
    z = make_evidence("z", source_digest=SOURCE_B, reasoning_support="limited")
    first = form(evidence=(z, a))
    second = form(evidence=(a, z))
    assert first.knowledge_fingerprint == second.knowledge_fingerprint
    assert first.evaluation_evidence == second.evaluation_evidence
