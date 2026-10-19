"""D156 deterministic terminal quality projection."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.cognitive_experience import CognitiveExperienceCandidateArtifact
from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.contracts.cognitive_quality_observability import CognitiveQualityObservation, cognitive_quality_turn_digest, compute_cognitive_quality_projection_fingerprint
from app.contracts.cognitive_trusted_experience_context_projection import CognitiveTrustedExperienceContextProjection
from app.contracts.cognitive_trusted_experience_reasoning import CognitiveTrustedExperienceReasoningInfluence
from app.contracts.cognitive_trusted_experience_runtime_binding import CognitiveTrustedExperienceRuntimeBinding
from app.contracts.cognitive_trusted_experience_verification import CognitiveTrustedExperienceVerificationInfluence
from app.contracts.cognitive_verification import CognitivePublicationGateArtifact, CognitiveVerificationArtifact
from app.services.cognitive_outcome_quality_feedback import CognitiveOutcomeQualityFeedbackEvaluator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CognitiveQualityProjectionService:
    def __init__(self, *, clock: Callable[[], datetime] = _utc_now) -> None:
        if not callable(clock): raise TypeError("clock must be callable")
        self._clock = clock

    @staticmethod
    def _cohort(*, experience_evaluated: bool, binding, projection, reasoning, verification):
        if type(experience_evaluated) is not bool: raise ValueError("cognitive_quality_experience_evaluated_invalid")
        if not experience_evaluated:
            if any(x is not None for x in (binding, projection, reasoning, verification)): raise ValueError("cognitive_quality_experience_stage_invalid")
            return "not_evaluated"
        if verification is not None:
            verification.__post_init__()
            if verification.verification_status == "active": return "verification_active"
        if reasoning is not None:
            reasoning.__post_init__()
            if reasoning.reasoning_status == "active": return "reasoning_active"
        if projection is not None:
            projection.__post_init__()
            return {"projected":"projected","restricted":"restricted","unavailable":"unavailable","empty":"no_evidence"}[projection.projection_status]
        if binding is None: return "absent"
        binding.__post_init__()
        if binding.binding_status == "unavailable": return "unavailable"
        if binding.advisory_status == "no_evidence": return "no_evidence"
        return "unavailable"

    def project(self, *, turn_id: str, outcome: CognitiveExecutiveOutcome, candidate: CognitiveExperienceCandidateArtifact | None = None,
                task: CognitiveTaskDescription | None = None, metacognition: CognitiveMetacognitionArtifact | None = None,
                verification: CognitiveVerificationArtifact | None = None, publication_gate: CognitivePublicationGateArtifact | None = None,
                experience_evaluated: bool = False, trusted_experience_binding: CognitiveTrustedExperienceRuntimeBinding | None = None,
                trusted_experience_context_projection: CognitiveTrustedExperienceContextProjection | None = None,
                trusted_experience_reasoning_influence: CognitiveTrustedExperienceReasoningInfluence | None = None,
                trusted_experience_verification_influence: CognitiveTrustedExperienceVerificationInfluence | None = None) -> CognitiveQualityObservation:
        if not isinstance(outcome, CognitiveExecutiveOutcome): raise TypeError("outcome invalid")
        outcome.__post_init__()
        ws = outcome.envelope.workspace_id
        for item in (candidate, task, metacognition, verification, publication_gate, trusted_experience_binding, trusted_experience_context_projection, trusted_experience_reasoning_influence, trusted_experience_verification_influence):
            if item is None: continue
            item.__post_init__()
            item_ws = getattr(getattr(item, "envelope", None), "workspace_id", getattr(item, "workspace_id", None))
            if item_ws is not None and item_ws is not ws: raise ValueError("cognitive_quality_workspace_mismatch")

        if candidate is not None:
            if candidate.envelope.turn_id != turn_id: raise ValueError("cognitive_quality_candidate_turn_mismatch")
            feedback = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
            feedback.__post_init__()
            classification, reason = feedback.classification, feedback.reason_code
            candidate_fp, feedback_fp = feedback.source_candidate_fingerprint, feedback.feedback_fingerprint
            interaction, cognitive = candidate.interaction_intent, candidate.cognitive_intent
            task_kind, confidence = candidate.authoritative_ai_task_kind, candidate.observed_confidence_class
        else:
            candidate_fp = feedback_fp = None
            if outcome.terminal_state is CognitiveTurnState.COMPLETED:
                classification, reason = "verified_success", "verified_success"
            elif outcome.terminal_state is CognitiveTurnState.INSUFFICIENT:
                classification, reason = "bounded_insufficiency", "bounded_insufficiency"
            elif outcome.failure_code is CognitiveFailureCode.CRITIC_UNAVAILABLE:
                classification, reason = "adverse_outcome", "critic_exhausted"
            elif outcome.failure_code is CognitiveFailureCode.INVALID_COGNITION:
                classification, reason = "adverse_outcome", "invalid_cognition"
            else:
                classification, reason = "adverse_outcome", "terminal_failure"
            interaction = task.interaction_intent if isinstance(task, CognitiveTaskDescription) else None
            cognitive = task.cognitive_intent if isinstance(task, CognitiveTaskDescription) else None
            task_kind = task.authoritative_ai_task_kind if isinstance(task, CognitiveTaskDescription) else (outcome.bindings[0].task_kind if outcome.bindings else None)
            confidence = metacognition.confidence_class if isinstance(metacognition, CognitiveMetacognitionArtifact) else None

        verification_result = verification.result if isinstance(verification, CognitiveVerificationArtifact) else (publication_gate.verification_result if isinstance(publication_gate, CognitivePublicationGateArtifact) else None)
        critic_exhausted = publication_gate.critic_exhausted if isinstance(publication_gate, CognitivePublicationGateArtifact) else (True if outcome.failure_code is CognitiveFailureCode.CRITIC_UNAVAILABLE else None)
        binding0 = outcome.bindings[0] if outcome.bindings else None
        cohort = self._cohort(experience_evaluated=experience_evaluated, binding=trusted_experience_binding, projection=trusted_experience_context_projection, reasoning=trusted_experience_reasoning_influence, verification=trusted_experience_verification_influence)
        occurred_at = self._clock()
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None: raise ValueError("cognitive_quality_clock_invalid")
        kwargs = dict(
            turn_digest=cognitive_quality_turn_digest(workspace_id=ws, turn_id=turn_id), workspace_id=ws,
            terminal_state=outcome.terminal_state, interaction_intent=interaction, cognitive_intent=cognitive,
            authoritative_ai_task_kind=task_kind, quality_classification=classification, quality_reason_code=reason,
            verification_result=verification_result, publication_disposition=outcome.publication_disposition,
            critic_exhausted=critic_exhausted, revision_count=outcome.revision_count, confidence_class=confidence,
            experience_cohort=cohort, adapter_id=binding0.adapter_id if binding0 else None,
            model_id=binding0.model_id if binding0 else None, profile_id=binding0.profile_id if binding0 else None,
            source_candidate_fingerprint=candidate_fp, source_feedback_fingerprint=feedback_fp,
        )
        return CognitiveQualityObservation(**kwargs, projection_fingerprint=compute_cognitive_quality_projection_fingerprint(**kwargs), occurred_at=occurred_at)
