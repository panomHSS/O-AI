from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AIAdapterDiscovery,
    AIModelDescriptor,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_model_intelligence import (
    D135_MODEL_CAPABILITY_ARTIFACT_TYPE,
    D135_MODEL_CAPABILITY_CONTRACT_VERSION,
    D135_OBSERVED_LATENCY_MS_MAX,
    D135_VERIFIED_CONTEXT_TOKENS_MAX,
    CognitiveModelCapabilityKnowledgeArtifact,
    ModelCapabilityEvaluationEvidence,
)
from app.contracts.local_ai_profile import LocalAIProfile
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_model_intelligence import CognitiveModelIntelligenceCoordinator

from tests.test_d135_cognitive_model_intelligence import (
    CONTEXT_A,
    NOW,
    SOURCE_A,
    SOURCE_B,
    make_discovery,
    make_evidence,
    make_profile,
    make_task,
    model_envelope,
    refs_for,
    form,
)


CONTRACT_VIOLATION = "cognitive_model_intelligence_contract_violation"
APP_ROOT = Path(__file__).resolve().parents[1] / "app"
CONTRACT_PATH = APP_ROOT / "contracts" / "cognitive_model_intelligence.py"
SERVICE_PATH = APP_ROOT / "services" / "cognitive_model_intelligence.py"


def assert_contract_error(callable_):
    with pytest.raises(ValueError) as caught:
        callable_()
    assert str(caught.value) == CONTRACT_VIOLATION


def coordinator_call(
    *,
    task=None,
    discovery=None,
    target_model_id="model-a",
    profile=None,
    evidence=(),
    refs=None,
    envelope=None,
):
    task = task or make_task()
    discovery = discovery or make_discovery()
    if envelope is None:
        if refs is None:
            refs = refs_for(discovery, profile, evidence)
        envelope = model_envelope(task, refs)
    return CognitiveModelIntelligenceCoordinator().form_knowledge(
        envelope,
        task,
        discovery,
        target_model_id=target_model_id,
        local_profile=profile,
        evaluation_evidence=evidence,
    )


def imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def production_sources() -> tuple[str, str]:
    return (
        CONTRACT_PATH.read_text(encoding="utf-8"),
        SERVICE_PATH.read_text(encoding="utf-8"),
    )


# S01
def test_s01_wrong_envelope_producer_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        producer_organ=CognitiveOrgan.REASONING,
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S02
def test_s02_wrong_artifact_type_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        artifact_type="cognitive.other",
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S03
def test_s03_wrong_contract_version_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        contract_version="o-ai.other.v1",
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S04
def test_s04_non_ready_envelope_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        status=CognitiveOrganStatus.INSUFFICIENT,
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S05
def test_s05_model_binding_reference_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        model_binding_reference="a" * 64,
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S06
def test_s06_turn_mismatch_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(model_envelope(task, refs_for(discovery, None)), turn_id="other")
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S07
def test_s07_workspace_mismatch_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        workspace_id=WorkspaceId.COMPANY,
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S08
def test_s08_context_digest_mismatch_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = replace(
        model_envelope(task, refs_for(discovery, None)),
        context_snapshot_digest="b" * 64,
    )
    assert_contract_error(lambda: coordinator_call(task=task, discovery=discovery, envelope=envelope))


# S09
def test_s09_wrong_task_input_type_rejected():
    discovery = make_discovery()
    envelope = model_envelope(make_task(), refs_for(discovery, None))
    assert_contract_error(
        lambda: CognitiveModelIntelligenceCoordinator().form_knowledge(
            envelope, object(), discovery, target_model_id="model-a"
        )
    )


# S10
def test_s10_malformed_target_model_id_rejected():
    assert_contract_error(lambda: coordinator_call(target_model_id=" bad "))


# S11
def test_s11_malformed_discovery_adapter_id_rejected():
    discovery = make_discovery(adapter_id="bad\x01adapter")
    assert_contract_error(lambda: coordinator_call(discovery=discovery))


# S12
def test_s12_malformed_output_fingerprint_rejected():
    artifact = form()
    with pytest.raises(ValueError):
        replace(artifact, knowledge_fingerprint="not-a-digest")


# S13
def test_s13_discovery_models_over_256_rejected_without_truncation():
    models = tuple(
        AIModelDescriptor(f"m{i:03}", (AI_CAPABILITY_TEXT_GENERATION,))
        for i in range(257)
    )
    discovery = make_discovery(models=models)
    assert len(discovery.models) == 257
    assert_contract_error(lambda: coordinator_call(discovery=discovery, target_model_id="m000"))


# S14
def test_s14_adapter_capabilities_over_32_rejected_without_truncation():
    caps = tuple(f"cap{i:02}" for i in range(33))
    discovery = make_discovery(
        capability_ids=caps,
        models=(AIModelDescriptor("model-a", (caps[0],)),),
    )
    assert len(discovery.capability_ids) == 33
    assert_contract_error(lambda: coordinator_call(discovery=discovery))


# S15
def test_s15_model_capabilities_over_32_rejected_without_truncation():
    caps = tuple(f"cap{i:02}" for i in range(33))
    discovery = make_discovery(
        capability_ids=caps,
        models=(AIModelDescriptor("model-a", caps),),
    )
    assert_contract_error(lambda: coordinator_call(discovery=discovery))


# S16
def test_s16_model_capability_outside_adapter_set_rejected():
    discovery = make_discovery(
        capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        models=(AIModelDescriptor("model-a", ("other_capability",)),),
    )
    assert_contract_error(lambda: coordinator_call(discovery=discovery))


# S17
def test_s17_incoherence_not_silently_unioned():
    discovery = make_discovery(
        capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        models=(AIModelDescriptor("model-a", ("other_capability",)),),
    )
    original = discovery.capability_ids
    assert_contract_error(lambda: coordinator_call(discovery=discovery))
    assert discovery.capability_ids == original


# S18
def test_s18_incoherence_not_silently_dropped():
    discovery = make_discovery(
        capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        models=(AIModelDescriptor("model-a", ("other_capability",)),),
    )
    original = discovery.models[0].capability_ids
    assert_contract_error(lambda: coordinator_call(discovery=discovery))
    assert discovery.models[0].capability_ids == original


# S19
def test_s19_future_unknown_safe_d34_reason_accepted_preserved_exactly():
    discovery = make_discovery(reason_code="future_reason_v9")
    artifact = coordinator_call(discovery=discovery)
    assert artifact.discovery_reason_code == "future_reason_v9"


# S20
def test_s20_unsafe_control_oversized_d34_reason_rejected_fail_closed():
    for reason in ("bad\x01reason", "x" * (COGNITIVE_ID_MAX_BYTES + 1)):
        discovery = make_discovery(reason_code=reason)
        assert_contract_error(lambda discovery=discovery: coordinator_call(discovery=discovery))


# S21
def test_s21_duplicate_discovered_model_identity_rejected_at_boundary_upstream():
    with pytest.raises(ValueError):
        AIAdapterDiscovery(
            adapter_id=LOCAL_AI_ADAPTER_ID,
            status="available",
            configured_model_id="model-a",
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=(
                AIModelDescriptor("model-a", (AI_CAPABILITY_TEXT_GENERATION,)),
                AIModelDescriptor("model-a", (AI_CAPABILITY_TEXT_GENERATION,)),
            ),
            reason_code="models_discovered",
        )


# S22
def test_s22_configured_model_mismatch_alone_cannot_imply_target_presence():
    discovery = make_discovery(models=(), configured_model_id="model-a")
    artifact = coordinator_call(discovery=discovery)
    assert artifact.model_discovered is False


# S23
def test_s23_non_local_adapter_with_local_profile_rejected():
    discovery = make_discovery(
        adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        configured_model_id="model-a",
    )
    assert_contract_error(lambda: coordinator_call(discovery=discovery, profile=make_profile()))


# S24
def test_s24_wrong_local_profile_type_rejected():
    task = make_task()
    discovery = make_discovery()
    envelope = model_envelope(task, refs_for(discovery, None))
    assert_contract_error(
        lambda: CognitiveModelIntelligenceCoordinator().form_knowledge(
            envelope,
            task,
            discovery,
            target_model_id="model-a",
            local_profile=object(),  # type: ignore[arg-type]
        )
    )


# S25
def test_s25_profile_task_kind_mismatch_rejected():
    profile = make_profile(task_kind=AITaskKind.SOFTWARE_ENGINEERING)
    assert_contract_error(lambda: coordinator_call(profile=profile))


# S26
def test_s26_profile_model_mismatch_rejected():
    profile = make_profile(model_id="model-b")
    assert_contract_error(lambda: coordinator_call(profile=profile))


# S27
def test_s27_invalid_d125_profile_identity_rejected_upstream():
    with pytest.raises(ValueError):
        LocalAIProfile(
            profile_id="bad.profile",
            task_kind=AITaskKind.GENERAL_CHAT,
            model_id="model-a",
            timeout_seconds=30,
            context_length=4096,
            reasoning_enabled=None,
        )


# S28
def test_s28_profile_cannot_authorize_undiscovered_model_use():
    discovery = make_discovery(models=())
    artifact = coordinator_call(discovery=discovery, profile=make_profile())
    assert artifact.model_discovered is False
    assert artifact.text_generation_support == "unknown"


# S29
def test_s29_profile_context_cannot_become_verified_context_evidence():
    artifact = coordinator_call(profile=make_profile(context_length=32768))
    assert artifact.configured_context_length == 32768
    assert artifact.max_verified_context_tokens is None


# S30
def test_s30_reasoning_enabled_true_cannot_become_reasoning_supported():
    artifact = coordinator_call(profile=make_profile(reasoning_enabled=True))
    assert artifact.reasoning_support == "unknown"


# S31
def test_s31_reasoning_enabled_false_cannot_become_reasoning_unsupported():
    artifact = coordinator_call(profile=make_profile(reasoning_enabled=False))
    assert artifact.reasoning_support == "unknown"


# S32
def test_s32_profile_id_cannot_become_routing_authority():
    names = {item.name for item in fields(CognitiveModelCapabilityKnowledgeArtifact)}
    assert {"route", "routing", "selected_adapter_id", "authorized_adapter_id"}.isdisjoint(names)


# S33
def test_s33_target_model_id_cannot_become_execution_selection():
    names = {item.name for item in fields(CognitiveModelCapabilityKnowledgeArtifact)}
    assert {"execution_plan", "authorization", "selected_model_id", "invoke"}.isdisjoint(names)


# S34
def test_s34_profile_timeout_is_not_latency_evidence():
    artifact = coordinator_call(profile=make_profile(timeout_seconds=600))
    assert artifact.latency_observations_ms == ()


# S35
def test_s35_evidence_count_over_32_rejected_without_truncation():
    evidence = tuple(
        make_evidence(f"e{i:02}", source_digest=f"{i + 1:064x}", task_fit="supported")
        for i in range(33)
    )
    assert len(evidence) == 33
    assert_contract_error(lambda: coordinator_call(evidence=evidence))


# S36
def test_s36_duplicate_evidence_ids_rejected():
    evidence = (
        make_evidence("dup", task_fit="supported"),
        make_evidence("dup", source_digest=SOURCE_B, reasoning_support="limited"),
    )
    assert_contract_error(lambda: coordinator_call(evidence=evidence))


# S37
def test_s37_wrong_evidence_source_kind_rejected():
    with pytest.raises(ValueError):
        ModelCapabilityEvaluationEvidence(
            evidence_id="e1",
            source_kind="browser",  # type: ignore[arg-type]
            source_digest=SOURCE_A,
            adapter_id=LOCAL_AI_ADAPTER_ID,
            model_id="model-a",
            task_kind=AITaskKind.GENERAL_CHAT,
            task_fit="supported",
        )


# S38
def test_s38_malformed_source_digest_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", source_digest="ABC", task_fit="supported")


# S39
def test_s39_evidence_adapter_mismatch_rejected():
    evidence = (
        make_evidence("e1", adapter_id="future.adapter", task_fit="supported"),
    )
    assert_contract_error(lambda: coordinator_call(evidence=evidence))


# S40
def test_s40_evidence_model_mismatch_rejected():
    evidence = (make_evidence("e1", model_id="model-b", task_fit="supported"),)
    assert_contract_error(lambda: coordinator_call(evidence=evidence))


# S41
def test_s41_evidence_task_kind_mismatch_rejected():
    evidence = (
        make_evidence("e1", task_kind=AITaskKind.SOFTWARE_ENGINEERING, task_fit="supported"),
    )
    assert_contract_error(lambda: coordinator_call(evidence=evidence))


# S42
def test_s42_evidence_with_no_observations_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1")


# S43
def test_s43_invalid_task_fit_literal_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", task_fit="unknown")


# S44
def test_s44_invalid_reasoning_literal_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", reasoning_support="conflicted")


# S45
def test_s45_invalid_structured_output_literal_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", structured_output_support="other")


# S46
def test_s46_evidence_level_unknown_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", task_fit="unknown")


# S47
def test_s47_evidence_level_conflicted_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", reasoning_support="conflicted")


# S48
def test_s48_verified_context_zero_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", verified_context_tokens=0)


# S49
def test_s49_verified_context_overflow_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", verified_context_tokens=D135_VERIFIED_CONTEXT_TOKENS_MAX + 1)


# S50
def test_s50_non_integer_verified_context_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", verified_context_tokens=1.5)


# S51
def test_s51_latency_zero_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", observed_latency_ms=0)


# S52
def test_s52_latency_overflow_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", observed_latency_ms=D135_OBSERVED_LATENCY_MS_MAX + 1)


# S53
def test_s53_non_integer_latency_rejected():
    with pytest.raises(ValueError):
        make_evidence("e1", observed_latency_ms=True)


# S54
def test_s54_malformed_evidence_id_rejected():
    for evidence_id in (" bad ", "bad\x01id", "x" * (COGNITIVE_ID_MAX_BYTES + 1)):
        with pytest.raises(ValueError):
            make_evidence(evidence_id, task_fit="supported")


# S55
def test_s55_no_evidence_remains_unknown_not_unsupported():
    artifact = coordinator_call()
    assert artifact.task_fit == "unknown"


# S56
def test_s56_model_name_cannot_infer_task_fit():
    discovery = make_discovery(
        configured_model_id="super-reasoning-best-model",
        models=(AIModelDescriptor("super-reasoning-best-model", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = coordinator_call(discovery=discovery, target_model_id="super-reasoning-best-model")
    assert artifact.task_fit == "unknown"


# S57
def test_s57_model_name_cannot_infer_reasoning_support():
    discovery = make_discovery(
        configured_model_id="reasoning-enabled-model",
        models=(AIModelDescriptor("reasoning-enabled-model", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = coordinator_call(discovery=discovery, target_model_id="reasoning-enabled-model")
    assert artifact.reasoning_support == "unknown"


# S58
def test_s58_model_name_cannot_infer_structured_output_support():
    discovery = make_discovery(
        configured_model_id="json-structured-model",
        models=(AIModelDescriptor("json-structured-model", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = coordinator_call(discovery=discovery, target_model_id="json-structured-model")
    assert artifact.structured_output_support == "unknown"


# S59
def test_s59_provider_reputation_cannot_infer_task_fit():
    discovery = make_discovery(
        adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        configured_model_id="gpt-x",
        models=(AIModelDescriptor("gpt-x", (AI_CAPABILITY_TEXT_GENERATION,)),),
    )
    artifact = coordinator_call(discovery=discovery, target_model_id="gpt-x")
    assert artifact.task_fit == "unknown"


# S60
def test_s60_discovery_availability_alone_cannot_infer_task_fit():
    assert coordinator_call().task_fit == "unknown"


# S61
def test_s61_configured_context_cannot_infer_intrinsic_capacity():
    artifact = coordinator_call(profile=make_profile(context_length=32768))
    assert artifact.max_verified_context_tokens is None


# S62
def test_s62_reasoning_policy_cannot_infer_reasoning_capability():
    artifact = coordinator_call(profile=make_profile(reasoning_enabled=True))
    assert artifact.reasoning_support == "unknown"


# S63
def test_s63_task_fit_conflict_never_majority_voted():
    evidence = (
        make_evidence("a", source_digest=SOURCE_A, task_fit="supported"),
        make_evidence("b", source_digest=SOURCE_B, task_fit="supported"),
        make_evidence("c", source_digest="3" * 64, task_fit="unsupported"),
    )
    assert coordinator_call(evidence=evidence).task_fit == "conflicted"


# S64
def test_s64_reasoning_conflict_never_latest_wins():
    evidence = (
        make_evidence("a", source_digest=SOURCE_A, reasoning_support="unsupported"),
        make_evidence("z", source_digest=SOURCE_B, reasoning_support="supported"),
    )
    assert coordinator_call(evidence=evidence).reasoning_support == "conflicted"


# S65
def test_s65_structured_output_conflict_never_source_prioritized():
    evidence = (
        make_evidence("a", source_digest=SOURCE_A, structured_output_support="limited"),
        make_evidence("b", source_digest=SOURCE_B, structured_output_support="supported"),
    )
    assert coordinator_call(evidence=evidence).structured_output_support == "conflicted"


# S66
def test_s66_conflicted_cannot_be_downgraded_to_limited():
    evidence = (
        make_evidence("a", task_fit="supported"),
        make_evidence("b", source_digest=SOURCE_B, task_fit="limited"),
    )
    artifact = coordinator_call(evidence=evidence)
    with pytest.raises(ValueError):
        replace(artifact, task_fit="limited")


# S67
def test_s67_unknown_cannot_be_upgraded_to_supported():
    artifact = coordinator_call()
    with pytest.raises(ValueError):
        replace(artifact, task_fit="supported")


# S68
def test_s68_d134_experience_candidate_is_not_automatic_evaluation_evidence():
    task = make_task()
    discovery = make_discovery()
    envelope = model_envelope(task, refs_for(discovery, None))
    assert_contract_error(
        lambda: CognitiveModelIntelligenceCoordinator().form_knowledge(
            envelope,
            task,
            discovery,
            target_model_id="model-a",
            evaluation_evidence=(object(),),  # type: ignore[arg-type]
        )
    )


# S69
def test_s69_refs_missing_discovery_digest_rejected():
    assert_contract_error(lambda: coordinator_call(refs=()))


# S70
def test_s70_refs_missing_profile_digest_rejected_when_profile_present():
    discovery = make_discovery()
    profile = make_profile()
    refs = (_discovery_digest := refs_for(discovery, None)[0],)
    assert_contract_error(
        lambda: coordinator_call(discovery=discovery, profile=profile, refs=refs)
    )


# S71
def test_s71_profile_digest_ref_rejected_when_profile_absent():
    discovery = make_discovery()
    refs = (refs_for(discovery, None)[0], "f" * 64)
    assert_contract_error(lambda: coordinator_call(discovery=discovery, refs=refs))


# S72
def test_s72_refs_missing_evaluation_source_digest_rejected():
    discovery = make_discovery()
    evidence = (make_evidence("e1", task_fit="supported"),)
    refs = (refs_for(discovery, None)[0],)
    assert_contract_error(lambda: coordinator_call(discovery=discovery, evidence=evidence, refs=refs))


# S73
def test_s73_refs_adding_unknown_digest_rejected():
    discovery = make_discovery()
    refs = (*refs_for(discovery, None), "f" * 64)
    assert_contract_error(lambda: coordinator_call(discovery=discovery, refs=refs))


# S74
def test_s74_refs_reordering_rejected():
    discovery = make_discovery()
    evidence = (make_evidence("e1", task_fit="supported"),)
    correct = refs_for(discovery, None, evidence)
    refs = (correct[1], correct[0])
    assert_contract_error(lambda: coordinator_call(discovery=discovery, evidence=evidence, refs=refs))


# S75
def test_s75_refs_require_unique_sorted_evaluation_digests():
    discovery = make_discovery()
    evidence = (
        make_evidence("a", source_digest=SOURCE_A, task_fit="supported"),
        make_evidence("b", source_digest=SOURCE_B, reasoning_support="limited"),
    )
    discovery_digest = refs_for(discovery, None)[0]
    refs = (discovery_digest, SOURCE_B, SOURCE_A)
    assert_contract_error(lambda: coordinator_call(discovery=discovery, evidence=evidence, refs=refs))


# S76
def test_s76_discovery_digest_tampering_rejected():
    artifact = form()
    bad = replace(
        artifact.envelope,
        input_reference_digests=("f" * 64,),
    )
    with pytest.raises(ValueError):
        replace(artifact, envelope=bad)


# S77
def test_s77_profile_digest_tampering_rejected():
    artifact = form(profile=make_profile())
    bad_refs = (
        artifact.envelope.input_reference_digests[0],
        "f" * 64,
    )
    bad = replace(artifact.envelope, input_reference_digests=bad_refs)
    with pytest.raises(ValueError):
        replace(artifact, envelope=bad)


# S78
def test_s78_evaluation_digest_projection_tampering_rejected():
    artifact = form(evidence=(make_evidence("e1", task_fit="supported"),))
    bad = replace(
        artifact.envelope,
        input_reference_digests=(artifact.envelope.input_reference_digests[0], "f" * 64),
    )
    with pytest.raises(ValueError):
        replace(artifact, envelope=bad)


# S79
def test_s79_limitation_code_tampering_rejected():
    artifact = form(evidence=(make_evidence("e1", task_fit="limited"),))
    with pytest.raises(ValueError):
        replace(artifact, limitation_codes=("task_fit_unsupported",))


# S80
def test_s80_limitation_code_reordering_rejected():
    artifact = form(
        evidence=(
            make_evidence(
                "e1",
                task_fit="limited",
                reasoning_support="unsupported",
            ),
        )
    )
    with pytest.raises(ValueError):
        replace(artifact, limitation_codes=tuple(reversed(artifact.limitation_codes)))


# S81
def test_s81_conflict_code_tampering_rejected():
    artifact = form(
        evidence=(
            make_evidence("a", task_fit="supported"),
            make_evidence("b", source_digest=SOURCE_B, task_fit="unsupported"),
        )
    )
    with pytest.raises(ValueError):
        replace(artifact, evidence_conflict_codes=("reasoning_support_conflict",))


# S82
def test_s82_conflict_code_reordering_rejected():
    artifact = form(
        evidence=(
            make_evidence(
                "a",
                task_fit="supported",
                reasoning_support="limited",
            ),
            make_evidence(
                "b",
                source_digest=SOURCE_B,
                task_fit="unsupported",
                reasoning_support="supported",
            ),
        )
    )
    with pytest.raises(ValueError):
        replace(
            artifact,
            evidence_conflict_codes=tuple(reversed(artifact.evidence_conflict_codes)),
        )


# S83
def test_s83_fingerprint_mismatch_rejected():
    artifact = form()
    with pytest.raises(ValueError):
        replace(artifact, knowledge_fingerprint="f" * 64)


# S84
def test_s84_raw_request_response_context_memory_knowledge_fields_absent():
    names = {item.name for item in fields(CognitiveModelCapabilityKnowledgeArtifact)}
    assert {
        "normalized_request",
        "raw_request",
        "raw_response",
        "context_text",
        "memory_value",
        "knowledge_content",
        "conversation_text",
        "draft_text",
    }.isdisjoint(names)


# S85
def test_s85_hidden_reasoning_prompt_credential_free_text_benchmark_fields_absent():
    names = {item.name for item in fields(CognitiveModelCapabilityKnowledgeArtifact)}
    assert {
        "chain_of_thought",
        "hidden_reasoning",
        "system_prompt",
        "provider_prompt",
        "credential",
        "api_key",
        "oauth_token",
        "benchmark_prose",
        "review_text",
    }.isdisjoint(names)


# S86
def test_s86_no_ranking_preferred_model_routing_selection_authority_surface():
    contract_source, service_source = production_sources()
    combined = contract_source + "\n" + service_source
    forbidden = (
        "select_model",
        "choose_model",
        "best_model",
        "preferred_model",
        "rank_models",
        "score_models",
        "selected_model_id",
        "routing_decision",
    )
    assert all(token not in combined for token in forbidden)


# S87
def test_s87_no_persistence_db_repository_scheduler_background_evaluator_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    assert not any(module.startswith("sqlalchemy") for module in imports)
    assert not any(module.startswith("alembic") for module in imports)
    assert not any(module.startswith("app.repositories.") for module in imports)
    assert "asyncio" not in imports
    assert "threading" not in imports
    assert "sched" not in imports


# S88
def test_s88_no_provider_network_model_invocation_or_d136_runtime_authority_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    forbidden_prefixes = ("openai", "httpx", "requests", "aiohttp", "urllib.request")
    assert not any(module.startswith(forbidden_prefixes) for module in imports)
    combined = "\n".join(production_sources())
    assert ".generate(" not in combined
    assert ".invoke(" not in combined
    assert "AIRuntime" not in combined
    assert "ExecutionPlanner" not in combined
    assert "ExecutionGuard" not in combined
    assert "CognitiveExecutive" not in combined
