"""Deterministic D134 ExperienceCandidate formation over terminal metadata."""

from __future__ import annotations

from app.contracts.cognitive_brain import (
    COGNITIVE_REFERENCE_DIGEST_MAX_COUNT,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveTurnManifest,
    CognitiveTurnState,
)
from app.contracts.cognitive_experience import (
    D134_EXPERIENCE_ARTIFACT_TYPE,
    D134_EXPERIENCE_CONTRACT_VERSION,
    D134_PROMOTION_DISPOSITION,
    D134_RETENTION_DISPOSITION,
    CognitiveExperienceCandidateArtifact,
    compute_cognitive_experience_fingerprint,
)
from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.contracts.cognitive_verification import (
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
)


class CognitiveExperienceContractError(Exception):
    """Fail-closed D134 contract failure; never rewrites primary turn state."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self, reason: str = "experience_contract_violation") -> None:
        if type(reason) is not str or not reason:
            reason = "experience_contract_violation"
        self.reason = reason
        super().__init__(reason)


class CognitiveExperienceCoordinator:
    """Form one ephemeral ExperienceCandidate from already-terminal metadata."""

    def form_candidate(
        self,
        envelope: CognitiveArtifactEnvelope,
        manifest: CognitiveTurnManifest,
        *,
        task: CognitiveTaskDescription | None = None,
        metacognition: CognitiveMetacognitionArtifact | None = None,
        verification: CognitiveVerificationArtifact | None = None,
        publication_gate: CognitivePublicationGateArtifact | None = None,
    ) -> CognitiveExperienceCandidateArtifact:
        try:
            return self._form(
                envelope,
                manifest,
                task=task,
                metacognition=metacognition,
                verification=verification,
                publication_gate=publication_gate,
            )
        except CognitiveExperienceContractError:
            raise
        except (TypeError, ValueError) as error:
            raise CognitiveExperienceContractError(
                "experience_contract_violation"
            ) from error

    def _form(
        self,
        envelope: CognitiveArtifactEnvelope,
        manifest: CognitiveTurnManifest,
        *,
        task: CognitiveTaskDescription | None,
        metacognition: CognitiveMetacognitionArtifact | None,
        verification: CognitiveVerificationArtifact | None,
        publication_gate: CognitivePublicationGateArtifact | None,
    ) -> CognitiveExperienceCandidateArtifact:
        if not isinstance(envelope, CognitiveArtifactEnvelope):
            raise CognitiveExperienceContractError("experience_envelope_invalid")
        if (
            envelope.artifact_type != D134_EXPERIENCE_ARTIFACT_TYPE
            or envelope.contract_version != D134_EXPERIENCE_CONTRACT_VERSION
        ):
            raise CognitiveExperienceContractError("experience_envelope_invalid")

        if not isinstance(manifest, CognitiveTurnManifest):
            raise CognitiveExperienceContractError("experience_manifest_invalid")
        if manifest.terminal_state not in {
            CognitiveTurnState.COMPLETED,
            CognitiveTurnState.INSUFFICIENT,
            CognitiveTurnState.FAILED,
        }:
            raise CognitiveExperienceContractError("experience_terminal_required")

        if len(manifest.artifact_digests) > COGNITIVE_REFERENCE_DIGEST_MAX_COUNT:
            raise CognitiveExperienceContractError(
                "experience_reference_limit_exceeded"
            )

        if (
            envelope.turn_id != manifest.turn_id
            or envelope.workspace_id is not manifest.workspace_id
            or envelope.context_snapshot_digest != manifest.context_snapshot_digest
            or envelope.input_reference_digests != manifest.artifact_digests
        ):
            raise CognitiveExperienceContractError("experience_binding_mismatch")

        terminal = manifest.terminal_state

        if task is None:
            if (
                terminal is not CognitiveTurnState.FAILED
                or manifest.authoritative_ai_task_kind is not None
            ):
                raise CognitiveExperienceContractError(
                    "experience_task_projection_invalid"
                )
            interaction_intent = None
            cognitive_intent = None
            task_kind = None
        else:
            if not isinstance(task, CognitiveTaskDescription):
                raise CognitiveExperienceContractError("experience_task_invalid")
            if (
                task.envelope.turn_id != manifest.turn_id
                or task.envelope.workspace_id is not manifest.workspace_id
                or (
                    task.envelope.context_snapshot_digest is not None
                    and task.envelope.context_snapshot_digest
                    != manifest.context_snapshot_digest
                )
                or task.authoritative_ai_task_kind
                is not manifest.authoritative_ai_task_kind
            ):
                raise CognitiveExperienceContractError(
                    "experience_task_binding_mismatch"
                )
            interaction_intent = task.interaction_intent
            cognitive_intent = task.cognitive_intent
            task_kind = manifest.authoritative_ai_task_kind

        if metacognition is None:
            if terminal in {
                CognitiveTurnState.COMPLETED,
                CognitiveTurnState.INSUFFICIENT,
            }:
                raise CognitiveExperienceContractError(
                    "experience_metacognition_required"
                )
            observed_confidence = None
        else:
            if not isinstance(metacognition, CognitiveMetacognitionArtifact):
                raise CognitiveExperienceContractError(
                    "experience_metacognition_invalid"
                )
            if task is None:
                raise CognitiveExperienceContractError(
                    "experience_metacognition_requires_task"
                )
            if (
                metacognition.envelope.turn_id != manifest.turn_id
                or metacognition.envelope.workspace_id is not manifest.workspace_id
                or metacognition.envelope.context_snapshot_digest
                != manifest.context_snapshot_digest
                or metacognition.intent != task.cognitive_intent
            ):
                raise CognitiveExperienceContractError(
                    "experience_metacognition_binding_mismatch"
                )
            observed_confidence = metacognition.confidence_class

        if verification is None:
            if terminal is CognitiveTurnState.COMPLETED:
                raise CognitiveExperienceContractError(
                    "experience_verification_required"
                )
            verification_result = None
            verification_issues = ()
        else:
            if not isinstance(verification, CognitiveVerificationArtifact):
                raise CognitiveExperienceContractError(
                    "experience_verification_invalid"
                )
            if task is None or metacognition is None:
                raise CognitiveExperienceContractError(
                    "experience_verification_requires_metacognition"
                )
            if (
                verification.envelope.turn_id != manifest.turn_id
                or verification.envelope.workspace_id is not manifest.workspace_id
                or verification.envelope.context_snapshot_digest
                != manifest.context_snapshot_digest
                or verification.draft_revision_count != manifest.revision_count
            ):
                raise CognitiveExperienceContractError(
                    "experience_verification_binding_mismatch"
                )
            verification_result = verification.result
            verification_issues = verification.issue_codes

        if publication_gate is None:
            if terminal is CognitiveTurnState.COMPLETED:
                raise CognitiveExperienceContractError(
                    "experience_publication_gate_required"
                )
            publication_disposition = None
            critic_exhausted = None
        else:
            if not isinstance(
                publication_gate,
                CognitivePublicationGateArtifact,
            ):
                raise CognitiveExperienceContractError(
                    "experience_publication_gate_invalid"
                )
            if verification is None:
                raise CognitiveExperienceContractError(
                    "experience_publication_gate_requires_verification"
                )
            if (
                publication_gate.envelope.turn_id != manifest.turn_id
                or publication_gate.envelope.workspace_id is not manifest.workspace_id
                or publication_gate.envelope.context_snapshot_digest
                != manifest.context_snapshot_digest
                or publication_gate.verification_result != verification.result
                or publication_gate.draft_revision_count != manifest.revision_count
                or publication_gate.draft_revision_count
                != verification.draft_revision_count
                or publication_gate.draft_digest != verification.draft_digest
            ):
                raise CognitiveExperienceContractError(
                    "experience_publication_gate_binding_mismatch"
                )
            publication_disposition = publication_gate.disposition
            critic_exhausted = publication_gate.critic_exhausted

        if terminal is CognitiveTurnState.COMPLETED:
            if (
                manifest.context_snapshot_digest is None
                or verification_result != "pass"
                or publication_disposition != "eligible"
                or critic_exhausted is not False
                or manifest.failure_code is not None
            ):
                raise CognitiveExperienceContractError(
                    "experience_completed_incoherent"
                )

        elif terminal is CognitiveTurnState.INSUFFICIENT:
            if (
                manifest.context_snapshot_digest is None
                or metacognition is None
                or metacognition.confidence_class
                not in {"insufficient", "unknown"}
                or metacognition.recommended_cognitive_action
                != "insufficient_information"
            ):
                raise CognitiveExperienceContractError(
                    "experience_insufficient_incoherent"
                )
            if (
                verification is not None
                and verification.result != "insufficient_evidence"
            ):
                raise CognitiveExperienceContractError(
                    "experience_insufficient_verification_incoherent"
                )
            if publication_gate is not None and (
                publication_gate.disposition != "bounded_insufficiency_only"
                or publication_gate.critic_exhausted is not False
            ):
                raise CognitiveExperienceContractError(
                    "experience_insufficient_publication_incoherent"
                )
            if manifest.failure_code not in {
                None,
                CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
            }:
                raise CognitiveExperienceContractError(
                    "experience_insufficient_failure_incoherent"
                )

        if critic_exhausted is True:
            lesson_code = "critic_exhausted"
        elif verification_result == "invalid_cognition":
            lesson_code = "invalid_cognition"
        elif terminal is CognitiveTurnState.FAILED:
            lesson_code = "terminal_failure"
        elif terminal is CognitiveTurnState.INSUFFICIENT:
            lesson_code = "bounded_insufficiency"
        else:
            lesson_code = "verified_success"

        outcome_class = {
            CognitiveTurnState.COMPLETED: "success",
            CognitiveTurnState.INSUFFICIENT: "insufficient",
            CognitiveTurnState.FAILED: "failure",
        }[terminal]

        fingerprint = compute_cognitive_experience_fingerprint(
            workspace_id=manifest.workspace_id,
            terminal_state=terminal,
            interaction_intent=interaction_intent,
            cognitive_intent=cognitive_intent,
            authoritative_ai_task_kind=task_kind,
            outcome_class=outcome_class,
            verification_result=verification_result,
            verification_issue_codes=verification_issues,
            publication_disposition=publication_disposition,
            critic_exhausted=critic_exhausted,
            revision_count=manifest.revision_count,
            failure_code=manifest.failure_code,
            observed_confidence_class=observed_confidence,
            authorized_adapter_id=manifest.authorized_adapter_id,
            authorized_model_id=manifest.authorized_model_id,
            authorized_profile_id=manifest.authorized_profile_id,
            lesson_code=lesson_code,
        )

        return CognitiveExperienceCandidateArtifact(
            envelope=envelope,
            terminal_state=terminal,
            interaction_intent=interaction_intent,
            cognitive_intent=cognitive_intent,
            authoritative_ai_task_kind=task_kind,
            outcome_class=outcome_class,
            verification_result=verification_result,
            verification_issue_codes=verification_issues,
            publication_disposition=publication_disposition,
            critic_exhausted=critic_exhausted,
            revision_count=manifest.revision_count,
            failure_code=manifest.failure_code,
            observed_confidence_class=observed_confidence,
            authorized_adapter_id=manifest.authorized_adapter_id,
            authorized_model_id=manifest.authorized_model_id,
            authorized_profile_id=manifest.authorized_profile_id,
            lesson_code=lesson_code,
            retention_disposition=D134_RETENTION_DISPOSITION,
            promotion_disposition=D134_PROMOTION_DISPOSITION,
            candidate_fingerprint=fingerprint,
        )


__all__ = [
    "CognitiveExperienceContractError",
    "CognitiveExperienceCoordinator",
]
