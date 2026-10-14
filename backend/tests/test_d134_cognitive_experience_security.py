from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
)
from app.contracts.cognitive_experience import CognitiveExperienceCandidateArtifact
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_experience import (
    CognitiveExperienceContractError,
    CognitiveExperienceCoordinator,
)
from tests.test_d134_cognitive_experience import (
    CTX,
    completed_candidate,
    digest,
    experience_envelope,
    form,
    make_gate,
    make_manifest,
    make_meta,
    make_task,
    make_verification,
)


def assert_contract_error(callable_):
    with pytest.raises(CognitiveExperienceContractError):
        callable_()


def production_sources() -> tuple[str, str]:
    root = Path(__file__).resolve().parents[1] / "app"
    return (
        (root / "contracts" / "cognitive_experience.py").read_text(encoding="utf-8"),
        (root / "services" / "cognitive_experience.py").read_text(encoding="utf-8"),
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


# S01
def test_s01_wrong_experience_envelope_producer_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    envelope = experience_envelope(manifest, producer=CognitiveOrgan.METACOGNITION)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate, envelope=envelope))


# S02
def test_s02_wrong_experience_artifact_type_rejected():
    manifest = make_manifest()
    envelope = experience_envelope(manifest, artifact_type="cognitive.wrong")
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(envelope, manifest))


# S03
def test_s03_wrong_experience_contract_version_rejected():
    manifest = make_manifest()
    envelope = experience_envelope(manifest, contract_version="wrong")
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(envelope, manifest))


# S04
def test_s04_non_ready_experience_envelope_rejected():
    manifest = make_manifest()
    envelope = experience_envelope(manifest, status=CognitiveOrganStatus.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate, envelope=envelope))


# S05
def test_s05_experience_model_binding_rejected():
    manifest = make_manifest()
    envelope = experience_envelope(manifest, model_binding_reference="f" * 64)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate, envelope=envelope))


# S06
def test_s06_wrong_manifest_type_rejected():
    manifest = make_manifest()
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), object()))


# S07
def test_s07_non_terminal_manifest_rejected():
    manifest = replace(make_manifest(), terminal_state=None)
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), manifest))


# S08
def test_s08_envelope_turn_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    envelope = experience_envelope(manifest, turn_id="other")
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S09
def test_s09_envelope_workspace_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    envelope = experience_envelope(manifest, workspace_id=WorkspaceId.COMPANY)
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S10
def test_s10_envelope_context_digest_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None)
    envelope = experience_envelope(manifest, context_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S11
def test_s11_manifest_artifact_refs_over_sixty_four_fail_closed():
    refs = tuple(digest(i) for i in range(1, 66))
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None, artifact_digests=refs)
    envelope = experience_envelope(manifest, refs=())
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S12
def test_s12_reference_overflow_has_exact_reason():
    refs = tuple(digest(i) for i in range(1, 66))
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None, artifact_digests=refs)
    envelope = experience_envelope(manifest, refs=())
    with pytest.raises(CognitiveExperienceContractError) as caught:
        form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope)
    assert caught.value.reason == "experience_reference_limit_exceeded"


# S13
def test_s13_envelope_refs_missing_manifest_ref_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    envelope = experience_envelope(manifest, refs=(manifest.artifact_digests[0],))
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S14
def test_s14_envelope_refs_adding_ref_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    envelope = experience_envelope(manifest, refs=manifest.artifact_digests + (digest(3),))
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S15
def test_s15_envelope_refs_reordering_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    envelope = experience_envelope(manifest, refs=tuple(reversed(manifest.artifact_digests)))
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S16
def test_s16_no_silent_first_sixty_four_projection():
    refs = tuple(digest(i) for i in range(1, 66))
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None, artifact_digests=refs)
    envelope = experience_envelope(manifest, refs=refs[:64])
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S17
def test_s17_no_silent_last_sixty_four_projection():
    refs = tuple(digest(i) for i in range(1, 66))
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None, artifact_digests=refs)
    envelope = experience_envelope(manifest, refs=refs[-64:])
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))


# S18
def test_s18_source_manifest_not_mutated_on_reference_failure():
    refs = tuple(digest(i) for i in range(1, 66))
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None, artifact_digests=refs)
    before = manifest.artifact_digests
    envelope = experience_envelope(manifest, refs=())
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None, envelope=envelope))
    assert manifest.artifact_digests == before


# S19
def test_s19_malformed_fingerprint_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, candidate_fingerprint="bad")


# S20
def test_s20_mismatched_recomputed_fingerprint_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, candidate_fingerprint="c" * 64)


# S21
def test_s21_invalid_outcome_literal_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, outcome_class="other")


# S22
def test_s22_invalid_lesson_literal_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, lesson_code="learned")


# S23
def test_s23_invalid_retention_literal_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, retention_disposition="durable")


# S24
def test_s24_invalid_promotion_literal_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, promotion_disposition="promoted")


# S25
def test_s25_non_terminal_candidate_state_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, terminal_state=CognitiveTurnState.THINKING)


# S26
def test_s26_revision_overflow_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, revision_count=2)


# S27
def test_s27_non_boolean_critic_exhaustion_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, critic_exhausted="false")


# S28
def test_s28_invalid_verification_issue_sequence_rejected():
    candidate, *_ = completed_candidate()
    with pytest.raises(ValueError):
        replace(candidate, verification_issue_codes=("not_an_issue",))


# S29
def test_s29_duplicate_verification_issues_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="revise")
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    with pytest.raises(ValueError):
        replace(candidate, verification_issue_codes=("citation_required", "citation_required"))


# S30
def test_s30_invalid_task_type_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), manifest, task=object()))


# S31
def test_s31_task_turn_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest, turn_id="other")
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S32
def test_s32_task_workspace_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest, workspace_id=WorkspaceId.COMPANY)
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S33
def test_s33_non_none_task_context_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest, context_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S34
def test_s34_task_kind_mismatch_with_manifest_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest, task_kind=AITaskKind.SOFTWARE_ENGINEERING)
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S35
def test_s35_task_absent_on_completed_rejected():
    manifest = make_manifest()
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None))


# S36
def test_s36_task_absent_on_insufficient_rejected():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None))


# S37
def test_s37_task_absent_with_manifest_task_kind_present_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, context_digest=None)
    assert_contract_error(lambda: form(manifest, task=None, meta=None, verification=None, gate=None))


# S38
def test_s38_metacognition_wrong_type_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), manifest, task=task, metacognition=object()))


# S39
def test_s39_metacognition_without_task_rejected():
    source_manifest = make_manifest(CognitiveTurnState.FAILED)
    source_task = make_task(source_manifest)
    meta = make_meta(source_manifest, source_task)
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, turn_id=source_manifest.turn_id)
    assert_contract_error(lambda: form(manifest, task=None, meta=meta, verification=None, gate=None))


# S40
def test_s40_metacognition_turn_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task, turn_id="other")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S41
def test_s41_metacognition_workspace_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task, workspace_id=WorkspaceId.COMPANY)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S42
def test_s42_metacognition_context_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task, context_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S43
def test_s43_metacognition_intent_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest, cognitive_intent="general")
    other_task = make_task(manifest, cognitive_intent="summary")
    meta = make_meta(manifest, other_task)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S44
def test_s44_completed_missing_metacognition_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S45
def test_s45_insufficient_missing_metacognition_rejected():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    task = make_task(manifest)
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=None, gate=None))


# S46
def test_s46_verification_wrong_type_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), manifest, task=task, metacognition=meta, verification=object()))


# S47
def test_s47_verification_without_metacognition_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    verification = make_verification(manifest, result="invalid_cognition")
    assert_contract_error(lambda: form(manifest, task=task, meta=None, verification=verification, gate=None))


# S48
def test_s48_verification_turn_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition", turn_id="other")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S49
def test_s49_verification_workspace_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition", workspace_id=WorkspaceId.COMPANY)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S50
def test_s50_verification_context_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition", context_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S51
def test_s51_verification_revision_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, revision=0)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition", revision=1)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S52
def test_s52_completed_missing_verification_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S53
def test_s53_completed_non_pass_verification_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S54
def test_s54_insufficient_supplied_non_insufficient_verification_rejected():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    verification = make_verification(manifest, result="pass")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S55
def test_s55_publication_gate_wrong_type_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    assert_contract_error(lambda: CognitiveExperienceCoordinator().form_candidate(experience_envelope(manifest), manifest, task=task, metacognition=meta, verification=verification, publication_gate=object()))


# S56
def test_s56_publication_gate_without_verification_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=gate))


# S57
def test_s57_publication_gate_turn_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification, turn_id="other")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S58
def test_s58_publication_gate_workspace_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification, workspace_id=WorkspaceId.COMPANY)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S59
def test_s59_publication_gate_context_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification, context_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S60
def test_s60_publication_verification_result_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification, verification_result="invalid_cognition")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S61
def test_s61_publication_verification_draft_digest_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification, draft_digest="c" * 64)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S62
def test_s62_publication_revision_mismatch_rejected():
    manifest = make_manifest(CognitiveTurnState.FAILED, revision=0)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass", revision=0)
    gate = make_gate(manifest, verification, revision=1)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S63
def test_s63_completed_missing_publication_gate_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=None))


# S64
def test_s64_completed_non_eligible_disposition_rejected():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S65
def test_s65_completed_critic_exhaustion_rejected():
    manifest = make_manifest(revision=1)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="limited")
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    assert gate.critic_exhausted is True
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S66
def test_s66_insufficient_non_bounded_disposition_rejected():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S67
def test_s67_insufficient_critic_exhaustion_rejected():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT, revision=1)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    assert gate.critic_exhausted is True
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=verification, gate=gate))


# S68
def test_s68_insufficient_unrelated_manifest_failure_code_rejected():
    manifest = make_manifest(
        CognitiveTurnState.INSUFFICIENT,
        failure_code=CognitiveFailureCode.CONTRACT_VIOLATION,
    )
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    assert_contract_error(lambda: form(manifest, task=task, meta=meta, verification=None, gate=None))


# S69
def test_s69_candidate_adapter_id_equals_manifest():
    candidate, manifest, *_ = completed_candidate()
    assert candidate.authorized_adapter_id == manifest.authorized_adapter_id


# S70
def test_s70_candidate_model_id_equals_manifest():
    candidate, manifest, *_ = completed_candidate()
    assert candidate.authorized_model_id == manifest.authorized_model_id


# S71
def test_s71_candidate_profile_id_equals_manifest():
    candidate, manifest, *_ = completed_candidate()
    assert candidate.authorized_profile_id == manifest.authorized_profile_id


# S72
def test_s72_raw_normalized_request_absent_from_candidate_fields():
    candidate, _, task, *_ = completed_candidate()
    names = {item.name for item in fields(CognitiveExperienceCandidateArtifact)}
    assert "normalized_request" not in names
    assert task.normalized_request not in repr(candidate)


# S73
def test_s73_raw_draft_response_text_absent_from_candidate_fields():
    names = {item.name for item in fields(CognitiveExperienceCandidateArtifact)}
    assert {"text", "draft_text", "response_text", "raw_response"}.isdisjoint(names)


# S74
def test_s74_raw_context_memory_knowledge_fields_absent():
    names = {item.name for item in fields(CognitiveExperienceCandidateArtifact)}
    assert {
        "context_text",
        "memory_value",
        "knowledge_content",
        "conversation_text",
    }.isdisjoint(names)


# S75
def test_s75_hidden_reasoning_prompt_credential_fields_absent():
    names = {item.name for item in fields(CognitiveExperienceCandidateArtifact)}
    assert {
        "chain_of_thought",
        "hidden_reasoning",
        "system_prompt",
        "provider_prompt",
        "credential",
        "api_key",
        "oauth_token",
        "lesson_text",
    }.isdisjoint(names)


# S76
def test_s76_no_memory_mutation_promotion_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    assert "app.services.memories" not in imports
    assert "app.repositories.memories" not in imports
    service_source = production_sources()[1]
    assert "write_memory" not in service_source
    assert "promote(" not in service_source


# S77
def test_s77_no_persistence_db_repository_migration_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    assert not any(module.startswith("sqlalchemy") for module in imports)
    assert not any(module.startswith("app.repositories.") for module in imports)
    assert not any(module.startswith("alembic") for module in imports)


# S78
def test_s78_no_provider_network_model_invocation_or_routing_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    forbidden = ("openai", "httpx", "requests", "aiohttp", "urllib.request")
    assert not any(module.startswith(forbidden) for module in imports)
    service_source = production_sources()[1]
    assert ".generate(" not in service_source
    assert ".invoke(" not in service_source
    assert "AIRuntime" not in service_source


# S79
def test_s79_no_scheduler_background_loop_d136_runtime_surface():
    imports = set().union(*(imported_modules(source) for source in production_sources()))
    assert "asyncio" not in imports
    assert "threading" not in imports
    assert "sched" not in imports
    service_source = production_sources()[1]
    assert "while True" not in service_source
    assert "create_task" not in service_source


# S80
def test_s80_no_model_scoring_preferred_model_d135_authority_surface():
    contract_source, service_source = production_sources()
    combined = contract_source + "\n" + service_source
    assert "preferred_model" not in combined
    assert "best_model" not in combined
    assert "score_model" not in combined
    assert "model_rank" not in combined
