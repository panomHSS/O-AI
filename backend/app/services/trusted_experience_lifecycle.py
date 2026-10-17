from __future__ import annotations

from uuid import UUID

from app.contracts.cognitive_trusted_experience import (
    CognitiveTrustedExperienceEligibilityAssessment,
    evaluate_cognitive_trusted_experience_eligibility,
)
from app.repositories.trusted_experiences import TrustedExperienceRepository
from app.schemas.trusted_experiences import (
    TrustedExperienceEventResponse,
    TrustedExperienceHistoryResponse,
    TrustedExperienceListResponse,
    TrustedExperienceResponse,
)
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
)


class TrustedExperienceNotFoundError(Exception):
    pass


class TrustedExperienceConflictError(Exception):
    pass


class TrustedExperienceValidationError(Exception):
    pass


class TrustedExperienceLifecycleService:
    """D147 durable proposal + explicit Owner trust lifecycle only."""

    def __init__(self, repository: TrustedExperienceRepository) -> None:
        self._repository = repository

    def evaluate(
        self,
        candidate: object,
    ) -> CognitiveTrustedExperienceEligibilityAssessment:
        feedback = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
        return evaluate_cognitive_trusted_experience_eligibility(
            candidate=candidate,
            feedback=feedback,
        )

    def capture_candidate(
        self,
        candidate: object,
    ) -> TrustedExperienceResponse | None:
        assessment = self.evaluate(candidate)
        if assessment.eligibility != "eligible_for_owner_review":
            return None
        proposal = assessment.proposal
        if proposal is None:
            raise TrustedExperienceValidationError(
                "Eligible trusted experience evidence has no proposal."
            )
        if proposal.workspace_id.value != self._repository.workspace_id:
            raise TrustedExperienceValidationError(
                "Trusted experience evidence belongs to a different workspace."
            )
        try:
            record = self._repository.create_pending(proposal)
            self._repository.commit()
            return self._response(record)
        except Exception:
            self._repository.rollback()
            raise

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> TrustedExperienceListResponse:
        records, total = self._repository.list(state, page, page_size)
        return TrustedExperienceListResponse(
            items=[self._response(item) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get(self, record_id: UUID) -> TrustedExperienceResponse:
        return self._response(self._require(record_id))

    def history(self, record_id: UUID) -> TrustedExperienceHistoryResponse:
        record = self._require(record_id)
        return TrustedExperienceHistoryResponse(
            trusted_experience_id=UUID(record.id),
            items=[
                TrustedExperienceEventResponse(
                    sequence=item.sequence,
                    event_type=item.event_type,
                    from_state=item.from_state,
                    to_state=item.to_state,
                    actor=item.actor,
                    decision_comment=item.decision_comment,
                    created_at=item.created_at,
                )
                for item in self._repository.history(record.id)
            ],
        )

    def approve(
        self,
        record_id: UUID,
        expected_revision: int,
        decision_comment: str,
    ) -> TrustedExperienceResponse:
        return self._transition(
            record_id=record_id,
            expected_revision=expected_revision,
            expected_state="PENDING_REVIEW",
            target_state="TRUSTED",
            event_type="APPROVED",
            decision_comment=decision_comment,
        )

    def reject(
        self,
        record_id: UUID,
        expected_revision: int,
        decision_comment: str,
    ) -> TrustedExperienceResponse:
        return self._transition(
            record_id=record_id,
            expected_revision=expected_revision,
            expected_state="PENDING_REVIEW",
            target_state="REJECTED",
            event_type="REJECTED",
            decision_comment=decision_comment,
        )

    def revoke(
        self,
        record_id: UUID,
        expected_revision: int,
        decision_comment: str,
    ) -> TrustedExperienceResponse:
        return self._transition(
            record_id=record_id,
            expected_revision=expected_revision,
            expected_state="TRUSTED",
            target_state="REVOKED",
            event_type="REVOKED",
            decision_comment=decision_comment,
        )

    def diagnostic_counts(self) -> dict[str, int]:
        return self._repository.state_counts()

    def _require(self, record_id: UUID):
        record = self._repository.get(str(record_id))
        if record is None:
            raise TrustedExperienceNotFoundError(
                "The requested trusted experience was not found."
            )
        return record

    def _transition(
        self,
        *,
        record_id: UUID,
        expected_revision: int,
        expected_state: str,
        target_state: str,
        event_type: str,
        decision_comment: str,
    ) -> TrustedExperienceResponse:
        comment = decision_comment.strip()
        if not comment or len(comment) > 2000:
            raise TrustedExperienceValidationError(
                "A bounded Owner decision comment is required."
            )
        record = self._require(record_id)
        if (
            record.state != expected_state
            or record.current_revision != expected_revision
        ):
            raise TrustedExperienceConflictError(
                "The trusted experience lifecycle revision or state changed."
            )
        try:
            updated = self._repository.transition(
                record_id=record.id,
                expected_revision=expected_revision,
                expected_state=expected_state,
                target_state=target_state,
                event_type=event_type,
                decision_comment=comment,
            )
            if updated is None:
                raise TrustedExperienceConflictError(
                    "The trusted experience lifecycle revision or state changed."
                )
            self._repository.commit()
            return self._response(updated)
        except Exception:
            self._repository.rollback()
            raise

    @staticmethod
    def _response(record) -> TrustedExperienceResponse:
        return TrustedExperienceResponse(
            id=UUID(record.id),
            workspace_id=record.workspace_id,
            contract_version=record.contract_version,
            source_candidate_fingerprint=record.source_candidate_fingerprint,
            source_feedback_fingerprint=record.source_feedback_fingerprint,
            proposal_fingerprint=record.proposal_fingerprint,
            quality_classification=record.quality_classification,
            quality_reason_code=record.quality_reason_code,
            lesson_code=record.lesson_code,
            interaction_intent=record.interaction_intent,
            cognitive_intent=record.cognitive_intent,
            authoritative_ai_task_kind=record.authoritative_ai_task_kind,
            observed_confidence_class=record.observed_confidence_class,
            authorized_adapter_id=record.authorized_adapter_id,
            authorized_model_id=record.authorized_model_id,
            authorized_profile_id=record.authorized_profile_id,
            source_revision_count=record.source_revision_count,
            state=record.state,
            current_revision=record.current_revision,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


__all__ = [
    "TrustedExperienceConflictError",
    "TrustedExperienceLifecycleService",
    "TrustedExperienceNotFoundError",
    "TrustedExperienceValidationError",
]
