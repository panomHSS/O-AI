"""D184 deterministic governed-execution experience review eligibility."""

from __future__ import annotations

from app.contracts.governed_execution_experience_candidate import (
    GovernedExecutionExperienceCandidate,
)
from app.contracts.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewAssessment,
    GovernedExecutionExperienceReviewProposal,
    compute_governed_execution_experience_review_fingerprint,
)


class GovernedExecutionExperienceReviewEvaluator:
    """Evaluate one exact D183 candidate for future explicit Owner review."""

    _ADVERSE = frozenset(
        {
            "execution_failed",
            "execution_blocked",
            "execution_rejected",
            "execution_unavailable",
        }
    )

    @classmethod
    def evaluate(
        cls,
        candidate: object,
    ) -> GovernedExecutionExperienceReviewAssessment:
        if type(candidate) is not GovernedExecutionExperienceCandidate:
            return cls._invalid()

        try:
            candidate.__post_init__()
        except Exception:
            return cls._invalid()

        if candidate.source_classification == "owner_denied":
            return GovernedExecutionExperienceReviewAssessment(
                eligibility="ineligible",
                reason_code="owner_declined",
                proposal=None,
            )

        if candidate.source_classification in cls._ADVERSE:
            return GovernedExecutionExperienceReviewAssessment(
                eligibility="ineligible",
                reason_code="adverse_execution_outcome",
                proposal=None,
            )

        if candidate.risk_class != "R0":
            return GovernedExecutionExperienceReviewAssessment(
                eligibility="ineligible",
                reason_code="risk_not_reviewable",
                proposal=None,
            )

        if candidate.effect not in {"none", "read"}:
            return GovernedExecutionExperienceReviewAssessment(
                eligibility="ineligible",
                reason_code="effect_not_reviewable",
                proposal=None,
            )

        if (
            candidate.source_classification != "execution_succeeded"
            or candidate.experience_outcome_class != "success"
            or candidate.experience_lesson_code != "authorized_execution_succeeded"
            or candidate.owner_decision != "approved"
            or candidate.execution_status != "completed"
            or candidate.result_status != "succeeded"
        ):
            return cls._invalid()

        try:
            fingerprint = compute_governed_execution_experience_review_fingerprint(
                workspace_id=candidate.workspace_id,
                conversation_id=candidate.conversation_id,
                source_turn_id=candidate.source_turn_id,
                source_artifact_digest=candidate.source_artifact_digest,
                intent_digest=candidate.intent_digest,
                approval_id=candidate.approval_id,
                execution_request_id=candidate.execution_request_id,
                plan_digest=candidate.plan_digest,
                source_feedback_fingerprint=candidate.source_feedback_fingerprint,
                source_candidate_fingerprint=candidate.candidate_fingerprint,
                target_kind=candidate.target_kind,
                capability_id=candidate.capability_id,
                adapter_id=candidate.adapter_id,
                operation=candidate.operation,
                effect=candidate.effect,
                risk_class=candidate.risk_class,
                source_classification=candidate.source_classification,
                experience_outcome_class=candidate.experience_outcome_class,
                experience_lesson_code=candidate.experience_lesson_code,
                review_reason_code="authorized_execution_succeeded",
            )
            proposal = GovernedExecutionExperienceReviewProposal(
                workspace_id=candidate.workspace_id,
                conversation_id=candidate.conversation_id,
                source_turn_id=candidate.source_turn_id,
                source_artifact_digest=candidate.source_artifact_digest,
                intent_digest=candidate.intent_digest,
                approval_id=candidate.approval_id,
                execution_request_id=candidate.execution_request_id,
                plan_digest=candidate.plan_digest,
                source_feedback_fingerprint=candidate.source_feedback_fingerprint,
                source_candidate_fingerprint=candidate.candidate_fingerprint,
                target_kind=candidate.target_kind,
                capability_id=candidate.capability_id,
                adapter_id=candidate.adapter_id,
                operation=candidate.operation,
                effect=candidate.effect,
                risk_class=candidate.risk_class,
                source_classification=candidate.source_classification,
                experience_outcome_class=candidate.experience_outcome_class,
                experience_lesson_code=candidate.experience_lesson_code,
                review_reason_code="authorized_execution_succeeded",
                review_fingerprint=fingerprint,
            )
            return GovernedExecutionExperienceReviewAssessment(
                eligibility="eligible_for_owner_review",
                reason_code="authorized_execution_succeeded",
                proposal=proposal,
            )
        except Exception:
            return cls._invalid()

    @staticmethod
    def _invalid() -> GovernedExecutionExperienceReviewAssessment:
        return GovernedExecutionExperienceReviewAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )


__all__ = ["GovernedExecutionExperienceReviewEvaluator"]
