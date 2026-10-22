"""D183 deterministic governed-execution experience candidate projection."""

from __future__ import annotations

from app.contracts.governed_execution_experience_candidate import (
    GovernedExecutionExperienceCandidate,
    compute_governed_execution_experience_candidate_fingerprint,
)
from app.contracts.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedback,
)


class GovernedExecutionExperienceProjector:
    """Project one validated D182 artifact into one ephemeral D183 candidate."""

    _PROJECTION = {
        "execution_succeeded": ("success", "authorized_execution_succeeded"),
        "owner_denied": ("owner_declined", "owner_declined_execution"),
        "execution_failed": ("execution_failure", "authorized_execution_failed"),
        "execution_blocked": ("execution_blocked", "execution_policy_blocked"),
        "execution_rejected": ("execution_rejected", "execution_request_rejected"),
        "execution_unavailable": (
            "execution_unavailable",
            "execution_capability_unavailable",
        ),
    }

    @classmethod
    def project(
        cls,
        feedback: object,
    ) -> GovernedExecutionExperienceCandidate | None:
        if type(feedback) is not GovernedExecutionOutcomeFeedback:
            return None

        try:
            feedback.__post_init__()
            outcome_class, lesson_code = cls._PROJECTION[feedback.classification]

            fingerprint = (
                compute_governed_execution_experience_candidate_fingerprint(
                    workspace_id=feedback.workspace_id,
                    conversation_id=feedback.conversation_id,
                    source_turn_id=feedback.source_turn_id,
                    source_artifact_digest=feedback.source_artifact_digest,
                    intent_digest=feedback.intent_digest,
                    approval_id=feedback.approval_id,
                    execution_request_id=feedback.execution_request_id,
                    plan_digest=feedback.plan_digest,
                    source_feedback_fingerprint=feedback.feedback_fingerprint,
                    target_kind=feedback.target_kind,
                    capability_id=feedback.capability_id,
                    adapter_id=feedback.adapter_id,
                    operation=feedback.operation,
                    effect=feedback.effect,
                    risk_class=feedback.risk_class,
                    owner_decision=feedback.owner_decision,
                    execution_status=feedback.execution_status,
                    result_status=feedback.result_status,
                    execution_reason_code=feedback.execution_reason_code,
                    source_classification=feedback.classification,
                    experience_outcome_class=outcome_class,
                    experience_lesson_code=lesson_code,
                )
            )

            return GovernedExecutionExperienceCandidate(
                workspace_id=feedback.workspace_id,
                conversation_id=feedback.conversation_id,
                source_turn_id=feedback.source_turn_id,
                source_artifact_digest=feedback.source_artifact_digest,
                intent_digest=feedback.intent_digest,
                approval_id=feedback.approval_id,
                execution_request_id=feedback.execution_request_id,
                plan_digest=feedback.plan_digest,
                source_feedback_fingerprint=feedback.feedback_fingerprint,
                target_kind=feedback.target_kind,
                capability_id=feedback.capability_id,
                adapter_id=feedback.adapter_id,
                operation=feedback.operation,
                effect=feedback.effect,
                risk_class=feedback.risk_class,
                owner_decision=feedback.owner_decision,
                execution_status=feedback.execution_status,
                result_status=feedback.result_status,
                execution_reason_code=feedback.execution_reason_code,
                source_classification=feedback.classification,
                experience_outcome_class=outcome_class,
                experience_lesson_code=lesson_code,
                candidate_fingerprint=fingerprint,
            )
        except Exception:
            return None


__all__ = ["GovernedExecutionExperienceProjector"]
