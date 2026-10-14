from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from typing import get_args

import pytest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnManifest,
    CognitiveTurnState,
)
from app.contracts.cognitive_experience import (
    D134_EXPERIENCE_ARTIFACT_TYPE,
    D134_EXPERIENCE_CONTRACT_VERSION,
    D134_EXPERIENCE_FINGERPRINT_VERSION,
    D134_PROMOTION_DISPOSITION,
    D134_RETENTION_DISPOSITION,
    CognitiveExperienceCandidateArtifact,
    ExperienceLessonCode,
    ExperienceOutcomeClass,
    ExperiencePromotionDisposition,
    ExperienceRetentionDisposition,
)
from app.contracts.cognitive_input_semantics import (
    D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
    D127_TASK_DESCRIPTION_CONTRACT_VERSION,
    CognitiveTaskDescription,
)
from app.contracts.cognitive_metacognition import (
    D132_METACOGNITION_ARTIFACT_TYPE,
    D132_METACOGNITION_CONTRACT_VERSION,
    CognitiveMetacognitionArtifact,
)
from app.contracts.cognitive_verification import (
    D133_PUBLICATION_GATE_ARTIFACT_TYPE,
    D133_PUBLICATION_GATE_CONTRACT_VERSION,
    D133_VERIFICATION_ARTIFACT_TYPE,
    D133_VERIFICATION_CONTRACT_VERSION,
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_experience import CognitiveExperienceCoordinator


NOW = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)
CTX = "a" * 64
DRAFT = "b" * 64


def digest(number: int) -> str:
    return f"{number:064x}"


def experience_envelope(
    manifest: CognitiveTurnManifest,
    *,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    context_digest: str | None | object = ...,
    refs: tuple[str, ...] | None = None,
    created_at: datetime = NOW,
    producer: CognitiveOrgan = CognitiveOrgan.EXPERIENCE_SYSTEM,
    artifact_type: str = D134_EXPERIENCE_ARTIFACT_TYPE,
    contract_version: str = D134_EXPERIENCE_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    model_binding_reference: str | None = None,
) -> CognitiveArtifactEnvelope:
    actual_context = (
        manifest.context_snapshot_digest if context_digest is ... else context_digest
    )
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or manifest.turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=producer,
        workspace_id=workspace_id or manifest.workspace_id,
        context_snapshot_digest=actual_context,
        created_at=created_at,
        status=status,
        input_reference_digests=(
            manifest.artifact_digests if refs is None else refs
        ),
        model_binding_reference=model_binding_reference,
    )


def make_manifest(
    terminal: CognitiveTurnState = CognitiveTurnState.COMPLETED,
    *,
    turn_id: str = "turn-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: str = "conversation-1",
    project_id: str | None = None,
    context_digest: str | None = CTX,
    task_kind: AITaskKind | None = AITaskKind.GENERAL_CHAT,
    revision: int = 0,
    failure_code: CognitiveFailureCode | None = None,
    artifact_digests: tuple[str, ...] = (digest(1), digest(2)),
    adapter_id: str | None = "adapter-a",
    model_id: str | None = "model-a",
    profile_id: str | None = "profile-a",
) -> CognitiveTurnManifest:
    if terminal is CognitiveTurnState.FAILED and failure_code is None:
        failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
    return CognitiveTurnManifest(
        turn_id=turn_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        project_id=project_id,
        terminal_state=terminal,
        context_snapshot_digest=context_digest,
        authoritative_ai_task_kind=task_kind,
        authorized_adapter_id=adapter_id,
        authorized_model_id=model_id,
        authorized_profile_id=profile_id,
        revision_count=revision,
        failure_code=failure_code,
        artifact_digests=artifact_digests,
    )


def make_task(
    manifest: CognitiveTurnManifest,
    *,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    context_digest: str | None = None,
    cognitive_intent: str = "general",
    interaction_intent: str = "chat",
    task_kind: AITaskKind | None = None,
) -> CognitiveTaskDescription:
    kind = task_kind or manifest.authoritative_ai_task_kind
    assert kind is not None
    return CognitiveTaskDescription(
        envelope=CognitiveArtifactEnvelope(
            turn_id=turn_id or manifest.turn_id,
            artifact_type=D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
            contract_version=D127_TASK_DESCRIPTION_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.TASK_UNDERSTANDING,
            workspace_id=workspace_id or manifest.workspace_id,
            context_snapshot_digest=context_digest,
            created_at=NOW,
            status=CognitiveOrganStatus.READY,
        ),
        interaction_intent=interaction_intent,
        cognitive_intent=cognitive_intent,
        authoritative_ai_task_kind=kind,
        normalized_request="private request that must not be copied",
        required_information=("user_question",),
    )


def make_meta(
    manifest: CognitiveTurnManifest,
    task: CognitiveTaskDescription,
    *,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    context_digest: str | None = None,
    confidence: str = "sufficient",
) -> CognitiveMetacognitionArtifact:
    digest_value = manifest.context_snapshot_digest if context_digest is None else context_digest
    assert digest_value is not None
    if confidence == "sufficient":
        knowledge = "known"
        status = CognitiveOrganStatus.READY
        action = "respond"
        evidence = "not_required"
        unknowns = ()
        assumptions = ()
    elif confidence == "limited":
        knowledge = "partial"
        status = CognitiveOrganStatus.READY
        action = "respond_with_uncertainty"
        evidence = "not_required"
        unknowns = ()
        assumptions = ("bounded assumption",)
    elif confidence == "unknown":
        knowledge = "unknown"
        status = CognitiveOrganStatus.INSUFFICIENT
        action = "insufficient_information"
        evidence = "not_required"
        unknowns = ("unknown",)
        assumptions = ()
    else:
        knowledge = "insufficient"
        status = CognitiveOrganStatus.INSUFFICIENT
        action = "insufficient_information"
        evidence = "insufficient"
        unknowns = ("missing evidence",)
        assumptions = ()
    return CognitiveMetacognitionArtifact(
        envelope=CognitiveArtifactEnvelope(
            turn_id=turn_id or manifest.turn_id,
            artifact_type=D132_METACOGNITION_ARTIFACT_TYPE,
            contract_version=D132_METACOGNITION_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.METACOGNITION,
            workspace_id=workspace_id or manifest.workspace_id,
            context_snapshot_digest=digest_value,
            created_at=NOW,
            status=status,
        ),
        intent=task.cognitive_intent,
        knowledge_status=knowledge,
        evidence_sufficiency=evidence,
        confidence_class=confidence,
        recommended_cognitive_action=action,
        unknowns=unknowns,
        assumptions=assumptions,
    )


def make_verification(
    manifest: CognitiveTurnManifest,
    *,
    result: str = "pass",
    issues: tuple[str, ...] | None = None,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    context_digest: str | None = None,
    revision: int | None = None,
    draft_digest: str = DRAFT,
) -> CognitiveVerificationArtifact:
    if result in {"pass", "revise"}:
        status = CognitiveOrganStatus.READY
        failure = None
    elif result == "insufficient_evidence":
        status = CognitiveOrganStatus.INSUFFICIENT
        failure = CognitiveFailureCode.INSUFFICIENT_EVIDENCE
    else:
        status = CognitiveOrganStatus.FAILED
        failure = CognitiveFailureCode.INVALID_COGNITION

    if issues is None:
        issues = {
            "pass": (),
            "revise": ("citation_required",),
            "insufficient_evidence": ("evidence_insufficient",),
            "invalid_cognition": ("metacognition_revision_required",),
        }[result]

    return CognitiveVerificationArtifact(
        envelope=CognitiveArtifactEnvelope(
            turn_id=turn_id or manifest.turn_id,
            artifact_type=D133_VERIFICATION_ARTIFACT_TYPE,
            contract_version=D133_VERIFICATION_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.VERIFICATION_CRITIC,
            workspace_id=workspace_id or manifest.workspace_id,
            context_snapshot_digest=(
                manifest.context_snapshot_digest
                if context_digest is None
                else context_digest
            ),
            created_at=NOW,
            status=status,
        ),
        result=result,
        response_mode="response",
        draft_revision_count=manifest.revision_count if revision is None else revision,
        draft_digest=draft_digest,
        issue_codes=issues,
        validated_citation_ids=(),
        advisory_result=None,
        advisory_binding_reference=None,
        failure_code=failure,
    )


def make_gate(
    manifest: CognitiveTurnManifest,
    verification: CognitiveVerificationArtifact,
    *,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    context_digest: str | None = None,
    revision: int | None = None,
    draft_digest: str | None = None,
    verification_result: str | None = None,
) -> CognitivePublicationGateArtifact:
    result = verification.result if verification_result is None else verification_result
    rev = manifest.revision_count if revision is None else revision
    if result == "pass":
        disposition, exhausted, status = "eligible", False, CognitiveOrganStatus.READY
    elif result == "insufficient_evidence":
        disposition, exhausted, status = (
            "bounded_insufficiency_only",
            False,
            CognitiveOrganStatus.INSUFFICIENT,
        )
    elif result == "revise" and rev == 0:
        disposition, exhausted, status = (
            "revision_required",
            False,
            CognitiveOrganStatus.READY,
        )
    elif result == "revise":
        disposition, exhausted, status = "blocked", True, CognitiveOrganStatus.FAILED
    else:
        disposition, exhausted, status = "blocked", False, CognitiveOrganStatus.FAILED

    return CognitivePublicationGateArtifact(
        envelope=CognitiveArtifactEnvelope(
            turn_id=turn_id or manifest.turn_id,
            artifact_type=D133_PUBLICATION_GATE_ARTIFACT_TYPE,
            contract_version=D133_PUBLICATION_GATE_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.VERIFICATION_CRITIC,
            workspace_id=workspace_id or manifest.workspace_id,
            context_snapshot_digest=(
                manifest.context_snapshot_digest
                if context_digest is None
                else context_digest
            ),
            created_at=NOW,
            status=status,
        ),
        verification_result=result,
        disposition=disposition,
        draft_revision_count=rev,
        draft_digest=verification.draft_digest if draft_digest is None else draft_digest,
        critic_exhausted=exhausted,
    )


def form(
    manifest: CognitiveTurnManifest,
    *,
    task: CognitiveTaskDescription | None,
    meta: CognitiveMetacognitionArtifact | None,
    verification: CognitiveVerificationArtifact | None,
    gate: CognitivePublicationGateArtifact | None,
    envelope: CognitiveArtifactEnvelope | None = None,
) -> CognitiveExperienceCandidateArtifact:
    return CognitiveExperienceCoordinator().form_candidate(
        envelope or experience_envelope(manifest),
        manifest,
        task=task,
        metacognition=meta,
        verification=verification,
        publication_gate=gate,
    )


def completed_candidate(
    *,
    turn_id: str = "turn-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: str = "conversation-1",
    project_id: str | None = None,
    revision: int = 0,
    cognitive_intent: str = "general",
    adapter_id: str | None = "adapter-a",
    model_id: str | None = "model-a",
    profile_id: str | None = "profile-a",
    created_at: datetime = NOW,
) -> tuple[
    CognitiveExperienceCandidateArtifact,
    CognitiveTurnManifest,
    CognitiveTaskDescription,
    CognitiveMetacognitionArtifact,
    CognitiveVerificationArtifact,
    CognitivePublicationGateArtifact,
]:
    manifest = make_manifest(
        turn_id=turn_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        project_id=project_id,
        revision=revision,
        adapter_id=adapter_id,
        model_id=model_id,
        profile_id=profile_id,
    )
    task = make_task(manifest, cognitive_intent=cognitive_intent)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    candidate = form(
        manifest,
        task=task,
        meta=meta,
        verification=verification,
        gate=gate,
        envelope=experience_envelope(manifest, created_at=created_at),
    )
    return candidate, manifest, task, meta, verification, gate


# F01
def test_f01_exact_constants():
    assert D134_EXPERIENCE_ARTIFACT_TYPE == "cognitive.experience_candidate"
    assert D134_EXPERIENCE_CONTRACT_VERSION == "o-ai.cognitive-experience-candidate.v1"
    assert D134_EXPERIENCE_FINGERPRINT_VERSION == "o-ai.cognitive-experience-fingerprint.v1"
    assert D134_RETENTION_DISPOSITION == "ephemeral"
    assert D134_PROMOTION_DISPOSITION == "candidate_only"


# F02
def test_f02_exact_outcome_vocabulary():
    assert get_args(ExperienceOutcomeClass) == ("success", "insufficient", "failure")


# F03
def test_f03_exact_lesson_vocabulary():
    assert get_args(ExperienceLessonCode) == (
        "verified_success",
        "bounded_insufficiency",
        "critic_exhausted",
        "invalid_cognition",
        "terminal_failure",
    )


# F04
def test_f04_exact_retention_promotion_vocabulary():
    assert get_args(ExperienceRetentionDisposition) == ("ephemeral",)
    assert get_args(ExperiencePromotionDisposition) == ("candidate_only",)


# F05
def test_f05_valid_completed_revision_zero():
    candidate, *_ = completed_candidate()
    assert candidate.terminal_state is CognitiveTurnState.COMPLETED
    assert candidate.revision_count == 0


# F06
def test_f06_valid_completed_revision_one():
    candidate, *_ = completed_candidate(revision=1)
    assert candidate.revision_count == 1
    assert candidate.publication_disposition == "eligible"


# F07
def test_f07_completed_task_metadata_projection():
    candidate, _, task, *_ = completed_candidate(cognitive_intent="summary")
    assert candidate.interaction_intent == task.interaction_intent
    assert candidate.cognitive_intent == "summary"
    assert candidate.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT


# F08
def test_f08_manifest_adapter_model_profile_projection():
    candidate, manifest, *_ = completed_candidate()
    assert (
        candidate.authorized_adapter_id,
        candidate.authorized_model_id,
        candidate.authorized_profile_id,
    ) == (
        manifest.authorized_adapter_id,
        manifest.authorized_model_id,
        manifest.authorized_profile_id,
    )


# F09
def test_f09_metacognitive_confidence_projection():
    candidate, *_ = completed_candidate()
    assert candidate.observed_confidence_class == "sufficient"


# F10
def test_f10_pass_verification_issue_projection():
    candidate, *_ = completed_candidate()
    assert candidate.verification_result == "pass"
    assert candidate.verification_issue_codes == ()


# F11
def test_f11_valid_insufficient_with_d133_artifacts():
    manifest = make_manifest(
        CognitiveTurnState.INSUFFICIENT,
        failure_code=CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
    )
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    verification = make_verification(manifest, result="insufficient_evidence")
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.outcome_class == "insufficient"
    assert candidate.publication_disposition == "bounded_insufficiency_only"


# F12
def test_f12_valid_insufficient_from_d132_without_d133_artifacts():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT, failure_code=None)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="unknown")
    candidate = form(manifest, task=task, meta=meta, verification=None, gate=None)
    assert candidate.verification_result is None
    assert candidate.lesson_code == "bounded_insufficiency"


# F13
def test_f13_valid_early_failed_without_context_or_task():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        context_digest=None,
        task_kind=None,
        failure_code=CognitiveFailureCode.TURN_DEADLINE_EXCEEDED,
    )
    candidate = form(manifest, task=None, meta=None, verification=None, gate=None)
    assert candidate.envelope.context_snapshot_digest is None
    assert candidate.cognitive_intent is None


# F14
def test_f14_valid_failed_with_task_without_metacognition():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        failure_code=CognitiveFailureCode.CONTRACT_VIOLATION,
    )
    task = make_task(manifest)
    candidate = form(manifest, task=task, meta=None, verification=None, gate=None)
    assert candidate.cognitive_intent == task.cognitive_intent
    assert candidate.observed_confidence_class is None


# F15
def test_f15_valid_failed_with_metacognition_without_verification():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="limited")
    candidate = form(manifest, task=task, meta=meta, verification=None, gate=None)
    assert candidate.observed_confidence_class == "limited"
    assert candidate.verification_result is None


# F16
def test_f16_valid_failed_invalid_cognition_verification():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        failure_code=CognitiveFailureCode.INVALID_COGNITION,
    )
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition")
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    assert candidate.lesson_code == "invalid_cognition"


# F17
def test_f17_valid_failed_critic_exhaustion():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        revision=1,
        failure_code=CognitiveFailureCode.CRITIC_UNAVAILABLE,
    )
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="limited")
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.critic_exhausted is True
    assert candidate.lesson_code == "critic_exhausted"


# F18
def test_f18_valid_failed_after_prior_pass_eligible():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        failure_code=CognitiveFailureCode.CONTRACT_VIOLATION,
    )
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="pass")
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.verification_result == "pass"
    assert candidate.outcome_class == "failure"
    assert candidate.lesson_code == "terminal_failure"


# F19
def test_f19_completed_outcome_mapping():
    candidate, *_ = completed_candidate()
    assert candidate.outcome_class == "success"


# F20
def test_f20_insufficient_outcome_mapping():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    candidate = form(manifest, task=task, meta=meta, verification=None, gate=None)
    assert candidate.outcome_class == "insufficient"


# F21
def test_f21_failed_outcome_mapping():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    candidate = form(manifest, task=None, meta=None, verification=None, gate=None)
    assert candidate.outcome_class == "failure"


# F22
def test_f22_critic_exhausted_lesson_precedence():
    manifest = make_manifest(CognitiveTurnState.FAILED, revision=1)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="limited")
    verification = make_verification(manifest, result="revise")
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.lesson_code == "critic_exhausted"


# F23
def test_f23_invalid_cognition_lesson_precedence():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition")
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    assert candidate.lesson_code == "invalid_cognition"


# F24
def test_f24_terminal_failure_lesson_mapping():
    manifest = make_manifest(CognitiveTurnState.FAILED, task_kind=None, context_digest=None)
    candidate = form(manifest, task=None, meta=None, verification=None, gate=None)
    assert candidate.lesson_code == "terminal_failure"


# F25
def test_f25_bounded_insufficiency_lesson_mapping():
    manifest = make_manifest(CognitiveTurnState.INSUFFICIENT)
    task = make_task(manifest)
    meta = make_meta(manifest, task, confidence="insufficient")
    candidate = form(manifest, task=task, meta=meta, verification=None, gate=None)
    assert candidate.lesson_code == "bounded_insufficiency"


# F26
def test_f26_verified_success_lesson_mapping():
    candidate, *_ = completed_candidate()
    assert candidate.lesson_code == "verified_success"


# F27
def test_f27_fingerprint_determinism():
    first, *_ = completed_candidate()
    second, *_ = completed_candidate()
    assert first.candidate_fingerprint == second.candidate_fingerprint


# F28
def test_f28_fingerprint_independent_of_created_at_and_turn_identity():
    first, *_ = completed_candidate(turn_id="turn-a", created_at=NOW)
    second, *_ = completed_candidate(
        turn_id="turn-b",
        created_at=NOW + timedelta(hours=1),
    )
    assert first.candidate_fingerprint == second.candidate_fingerprint


# F29
def test_f29_fingerprint_independent_of_conversation_project_identity():
    first, *_ = completed_candidate(
        conversation_id="conversation-a",
        project_id="project-a",
    )
    second, *_ = completed_candidate(
        conversation_id="conversation-b",
        project_id="project-b",
    )
    assert first.candidate_fingerprint == second.candidate_fingerprint


# F30
def test_f30_fingerprint_changes_across_workspace():
    first, *_ = completed_candidate(workspace_id=WorkspaceId.PERSONAL)
    second, *_ = completed_candidate(workspace_id=WorkspaceId.COMPANY)
    assert first.candidate_fingerprint != second.candidate_fingerprint


# F31
def test_f31_fingerprint_changes_with_task_semantics():
    first, *_ = completed_candidate(cognitive_intent="general")
    second, *_ = completed_candidate(cognitive_intent="summary")
    assert first.candidate_fingerprint != second.candidate_fingerprint


# F32
def test_f32_fingerprint_changes_with_outcome():
    success, *_ = completed_candidate()
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        task_kind=None,
        context_digest=None,
        adapter_id="adapter-a",
        model_id="model-a",
        profile_id="profile-a",
    )
    failed = form(manifest, task=None, meta=None, verification=None, gate=None)
    assert success.candidate_fingerprint != failed.candidate_fingerprint


# F33
def test_f33_fingerprint_changes_with_verification_issues():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    first_v = make_verification(
        manifest,
        result="invalid_cognition",
        issues=("metacognition_revision_required",),
    )
    second_v = make_verification(
        manifest,
        result="invalid_cognition",
        issues=("advisory_invalid_cognition",),
    )
    first = form(manifest, task=task, meta=meta, verification=first_v, gate=None)
    second = form(manifest, task=task, meta=meta, verification=second_v, gate=None)
    assert first.candidate_fingerprint != second.candidate_fingerprint


# F34
def test_f34_fingerprint_changes_with_model_profile_observation():
    first, *_ = completed_candidate(model_id="model-a", profile_id="profile-a")
    second, *_ = completed_candidate(model_id="model-b", profile_id="profile-b")
    assert first.candidate_fingerprint != second.candidate_fingerprint


# F35
def test_f35_fingerprint_preserves_verification_issue_order():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(
        manifest,
        result="revise",
        issues=("citation_required", "citation_unknown"),
    )
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    assert candidate.verification_issue_codes == ("citation_required", "citation_unknown")


# F36
def test_f36_empty_provenance_reference_sequence():
    manifest = make_manifest(artifact_digests=())
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.envelope.input_reference_digests == ()


# F37
def test_f37_exact_sixty_four_provenance_reference_copying():
    refs = tuple(digest(index) for index in range(1, 65))
    manifest = make_manifest(artifact_digests=refs)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert candidate.envelope.input_reference_digests == refs


# F38
def test_f38_failed_no_task_projection_produces_none_task_fields():
    manifest = make_manifest(
        CognitiveTurnState.FAILED,
        context_digest=None,
        task_kind=None,
    )
    candidate = form(manifest, task=None, meta=None, verification=None, gate=None)
    assert (
        candidate.interaction_intent,
        candidate.cognitive_intent,
        candidate.authoritative_ai_task_kind,
    ) == (None, None, None)


# F39
def test_f39_absent_verification_produces_none_empty_projection():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    candidate = form(manifest, task=task, meta=meta, verification=None, gate=None)
    assert candidate.verification_result is None
    assert candidate.verification_issue_codes == ()


# F40
def test_f40_absent_publication_gate_produces_none_projection():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="invalid_cognition")
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    assert candidate.publication_disposition is None
    assert candidate.critic_exhausted is None


# F41
def test_f41_candidate_is_frozen_slots_dataclass():
    candidate, *_ = completed_candidate()
    assert not hasattr(candidate, "__dict__")
    with pytest.raises(FrozenInstanceError):
        candidate.lesson_code = "terminal_failure"


# F42
def test_f42_bounded_sequence_values_are_immutable_tuples():
    manifest = make_manifest(CognitiveTurnState.FAILED)
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest, result="revise")
    candidate = form(manifest, task=task, meta=meta, verification=verification, gate=None)
    assert type(candidate.verification_issue_codes) is tuple


# F43
def test_f43_exact_repeated_invocation_is_idempotent():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    envelope = experience_envelope(manifest)
    first = form(
        manifest,
        task=task,
        meta=meta,
        verification=verification,
        gate=gate,
        envelope=envelope,
    )
    second = form(
        manifest,
        task=task,
        meta=meta,
        verification=verification,
        gate=gate,
        envelope=envelope,
    )
    assert first == second


# F44
def test_f44_source_artifacts_and_manifest_remain_unchanged():
    manifest = make_manifest()
    task = make_task(manifest)
    meta = make_meta(manifest, task)
    verification = make_verification(manifest)
    gate = make_gate(manifest, verification)
    before = (manifest, task, meta, verification, gate)
    form(manifest, task=task, meta=meta, verification=verification, gate=gate)
    assert before == (manifest, task, meta, verification, gate)
