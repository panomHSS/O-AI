from __future__ import annotations

import re
from uuid import UUID

from app.contracts.governed_execution_experience_owner_review import (
    D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION,
    compute_governed_execution_experience_owner_review_record_fingerprint,
)
from app.contracts.governed_execution_experience_trust import (
    GovernedExecutionExperienceTrustEligibilityAssessment,
    GovernedExecutionExperienceTrustPromotionProposal,
    compute_governed_execution_experience_trust_promotion_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.repositories.trusted_execution_experiences import (
    TrustedExecutionExperienceRepository,
)
from app.schemas.trusted_execution_experiences import (
    ExecutionExperienceTrustEligibilityResponse,
    ExecutionExperienceTrustPromotionProposalResponse,
    TrustedExecutionExperienceEventResponse,
    TrustedExecutionExperienceHistoryResponse,
    TrustedExecutionExperienceListResponse,
    TrustedExecutionExperienceResponse,
)

_HEX = re.compile(r"^[0-9a-f]{64}$")


class ExecutionExperienceTrustNotFoundError(Exception):
    pass


class ExecutionExperienceTrustConflictError(Exception):
    pass


class ExecutionExperienceTrustValidationError(Exception):
    pass


class ExecutionExperienceTrustLifecycleService:
    """D187 deterministic eligibility plus explicit Owner trust promotion/revocation."""

    def __init__(
        self,
        *,
        review_repository: ExecutionExperienceReviewRepository,
        trusted_repository: TrustedExecutionExperienceRepository,
    ) -> None:
        if not isinstance(review_repository, ExecutionExperienceReviewRepository):
            raise TypeError(
                "review_repository must be an ExecutionExperienceReviewRepository."
            )
        if not isinstance(trusted_repository, TrustedExecutionExperienceRepository):
            raise TypeError(
                "trusted_repository must be a TrustedExecutionExperienceRepository."
            )
        if review_repository.workspace_id != trusted_repository.workspace_id:
            raise ValueError("workspace_mismatch")
        self._review_repository = review_repository
        self._trusted_repository = trusted_repository

    def evaluate(
        self,
        review_id: UUID,
    ) -> ExecutionExperienceTrustEligibilityResponse:
        record = self._review_repository.get(str(review_id))
        if record is None:
            raise ExecutionExperienceTrustNotFoundError(
                "The execution experience review was not found."
            )
        assessment = self._assess(record)
        return self._eligibility_response(review_id, assessment)

    def promote(
        self,
        *,
        review_id: UUID,
        expected_revision: int,
        source_record_fingerprint: str,
        promotion_fingerprint: str,
    ) -> TrustedExecutionExperienceResponse:
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision != 2
        ):
            raise ExecutionExperienceTrustConflictError(
                "The execution experience review revision or state changed."
            )
        self._require_digest(
            source_record_fingerprint,
            "The source review record fingerprint is invalid.",
        )
        self._require_digest(
            promotion_fingerprint,
            "The promotion fingerprint is invalid.",
        )

        record = self._review_repository.get(str(review_id))
        if record is None:
            raise ExecutionExperienceTrustNotFoundError(
                "The execution experience review was not found."
            )
        if record.current_revision != expected_revision:
            raise ExecutionExperienceTrustConflictError(
                "The execution experience review revision or state changed."
            )

        assessment = self._assess(record)
        if (
            assessment.eligibility != "eligible_for_owner_promotion"
            or assessment.proposal is None
        ):
            raise ExecutionExperienceTrustValidationError(
                "The execution experience review is not eligible for trust promotion."
            )
        proposal = assessment.proposal

        if source_record_fingerprint != proposal.source_d186_record_fingerprint:
            raise ExecutionExperienceTrustValidationError(
                "The source review record fingerprint does not match."
            )
        if promotion_fingerprint != proposal.promotion_fingerprint:
            raise ExecutionExperienceTrustValidationError(
                "The promotion fingerprint does not match."
            )

        existing = self._trusted_repository.get_by_source_review_id(str(review_id))
        if existing is not None:
            if (
                existing.source_d186_record_fingerprint
                == proposal.source_d186_record_fingerprint
                and existing.promotion_fingerprint == proposal.promotion_fingerprint
            ):
                return self._response(existing)
            raise ExecutionExperienceTrustConflictError(
                "The source review already maps to different trusted evidence."
            )

        fingerprint_existing = (
            self._trusted_repository.get_by_promotion_fingerprint(
                proposal.promotion_fingerprint
            )
        )
        if fingerprint_existing is not None:
            if (
                fingerprint_existing.source_review_id == str(review_id)
                and fingerprint_existing.source_d186_record_fingerprint
                == proposal.source_d186_record_fingerprint
            ):
                return self._response(fingerprint_existing)
            raise ExecutionExperienceTrustConflictError(
                "The promotion fingerprint already maps to different trusted evidence."
            )

        try:
            trusted = self._trusted_repository.create_trusted(
                source_review_id=str(review_id),
                proposal=proposal,
            )
            self._trusted_repository.commit()
            return self._response(trusted)
        except Exception:
            self._trusted_repository.rollback()
            raise

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> TrustedExecutionExperienceListResponse:
        records, total = self._trusted_repository.list(state, page, page_size)
        return TrustedExecutionExperienceListResponse(
            items=[self._response(item) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get(self, trusted_id: UUID) -> TrustedExecutionExperienceResponse:
        return self._response(self._require_trusted(trusted_id))

    def history(
        self,
        trusted_id: UUID,
    ) -> TrustedExecutionExperienceHistoryResponse:
        record = self._require_trusted(trusted_id)
        return TrustedExecutionExperienceHistoryResponse(
            trusted_execution_experience_id=UUID(record.id),
            items=[
                TrustedExecutionExperienceEventResponse(
                    sequence=item.sequence,
                    event_type=item.event_type,
                    from_state=item.from_state,
                    to_state=item.to_state,
                    actor=item.actor,
                    created_at=item.created_at,
                )
                for item in self._trusted_repository.history(record.id)
            ],
        )

    def revoke(
        self,
        *,
        trusted_id: UUID,
        expected_revision: int,
        promotion_fingerprint: str,
    ) -> TrustedExecutionExperienceResponse:
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision != 1
        ):
            raise ExecutionExperienceTrustConflictError(
                "The trusted execution experience revision or state changed."
            )
        self._require_digest(
            promotion_fingerprint,
            "The promotion fingerprint is invalid.",
        )
        record = self._require_trusted(trusted_id)
        if record.promotion_fingerprint != promotion_fingerprint:
            raise ExecutionExperienceTrustValidationError(
                "The promotion fingerprint does not match."
            )
        if record.state != "TRUSTED" or record.current_revision != 1:
            raise ExecutionExperienceTrustConflictError(
                "The trusted execution experience revision or state changed."
            )
        try:
            updated = self._trusted_repository.revoke(
                record_id=record.id,
                expected_revision=expected_revision,
                promotion_fingerprint=promotion_fingerprint,
            )
            if updated is None:
                raise ExecutionExperienceTrustConflictError(
                    "The trusted execution experience revision or state changed."
                )
            self._trusted_repository.commit()
            return self._response(updated)
        except Exception:
            self._trusted_repository.rollback()
            raise

    def _assess(
        self,
        record,
    ) -> GovernedExecutionExperienceTrustEligibilityAssessment:
        try:
            workspace_id = WorkspaceId(record.workspace_id)
            conversation_id = UUID(record.conversation_id)
            if (
                record.contract_version
                != D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION
            ):
                raise ValueError("contract_invalid")
            expected_d186 = (
                compute_governed_execution_experience_owner_review_record_fingerprint(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    source_turn_id=record.source_turn_id,
                    source_artifact_digest=record.source_artifact_digest,
                    intent_digest=record.intent_digest,
                    approval_id=record.approval_id,
                    execution_request_id=record.execution_request_id,
                    plan_digest=record.plan_digest,
                    source_feedback_fingerprint=record.source_feedback_fingerprint,
                    source_candidate_fingerprint=record.source_candidate_fingerprint,
                    source_review_fingerprint=record.source_review_fingerprint,
                    target_kind=record.target_kind,
                    capability_id=record.capability_id,
                    adapter_id=record.adapter_id,
                    operation=record.operation,
                    effect=record.effect,
                    risk_class=record.risk_class,
                    source_classification=record.source_classification,
                    experience_outcome_class=record.experience_outcome_class,
                    experience_lesson_code=record.experience_lesson_code,
                    review_reason_code=record.review_reason_code,
                )
            )
            if expected_d186 != record.record_fingerprint:
                raise ValueError("record_fingerprint_invalid")
        except Exception:
            return GovernedExecutionExperienceTrustEligibilityAssessment(
                eligibility="invalid_evidence",
                reason_code="invalid_evidence",
                proposal=None,
            )

        history = tuple(self._review_repository.history(record.id))
        expected_history: tuple[tuple[object, ...], ...]
        if record.state == "PENDING_REVIEW" and record.current_revision == 1:
            expected_history = (
                (1, "PROPOSED", None, "PENDING_REVIEW", "SYSTEM"),
            )
            if self._history_tuple(history) != expected_history:
                return self._invalid()
            return GovernedExecutionExperienceTrustEligibilityAssessment(
                eligibility="ineligible",
                reason_code="review_not_accepted",
                proposal=None,
            )
        if record.state == "REVIEW_REJECTED" and record.current_revision == 2:
            expected_history = (
                (1, "PROPOSED", None, "PENDING_REVIEW", "SYSTEM"),
                (
                    2,
                    "OWNER_REJECTED",
                    "PENDING_REVIEW",
                    "REVIEW_REJECTED",
                    "OWNER",
                ),
            )
            if self._history_tuple(history) != expected_history:
                return self._invalid()
            return GovernedExecutionExperienceTrustEligibilityAssessment(
                eligibility="ineligible",
                reason_code="review_not_accepted",
                proposal=None,
            )
        if record.state != "REVIEW_ACCEPTED" or record.current_revision != 2:
            return self._invalid()

        expected_history = (
            (1, "PROPOSED", None, "PENDING_REVIEW", "SYSTEM"),
            (
                2,
                "OWNER_ACCEPTED",
                "PENDING_REVIEW",
                "REVIEW_ACCEPTED",
                "OWNER",
            ),
        )
        if self._history_tuple(history) != expected_history:
            return self._invalid()

        try:
            promotion_fingerprint = (
                compute_governed_execution_experience_trust_promotion_fingerprint(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    source_turn_id=record.source_turn_id,
                    source_artifact_digest=record.source_artifact_digest,
                    intent_digest=record.intent_digest,
                    approval_id=record.approval_id,
                    execution_request_id=record.execution_request_id,
                    plan_digest=record.plan_digest,
                    source_feedback_fingerprint=record.source_feedback_fingerprint,
                    source_candidate_fingerprint=record.source_candidate_fingerprint,
                    source_review_fingerprint=record.source_review_fingerprint,
                    source_d186_record_fingerprint=record.record_fingerprint,
                    target_kind=record.target_kind,
                    capability_id=record.capability_id,
                    adapter_id=record.adapter_id,
                    operation=record.operation,
                    effect=record.effect,
                    risk_class=record.risk_class,
                    source_classification=record.source_classification,
                    experience_outcome_class=record.experience_outcome_class,
                    experience_lesson_code=record.experience_lesson_code,
                    review_reason_code=record.review_reason_code,
                )
            )
            proposal = GovernedExecutionExperienceTrustPromotionProposal(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                source_turn_id=record.source_turn_id,
                source_artifact_digest=record.source_artifact_digest,
                intent_digest=record.intent_digest,
                approval_id=record.approval_id,
                execution_request_id=record.execution_request_id,
                plan_digest=record.plan_digest,
                source_feedback_fingerprint=record.source_feedback_fingerprint,
                source_candidate_fingerprint=record.source_candidate_fingerprint,
                source_review_fingerprint=record.source_review_fingerprint,
                source_d186_record_fingerprint=record.record_fingerprint,
                target_kind=record.target_kind,
                capability_id=record.capability_id,
                adapter_id=record.adapter_id,
                operation=record.operation,
                effect=record.effect,
                risk_class=record.risk_class,
                source_classification=record.source_classification,
                experience_outcome_class=record.experience_outcome_class,
                experience_lesson_code=record.experience_lesson_code,
                review_reason_code=record.review_reason_code,
                promotion_fingerprint=promotion_fingerprint,
            )
        except Exception:
            return self._invalid()

        return GovernedExecutionExperienceTrustEligibilityAssessment(
            eligibility="eligible_for_owner_promotion",
            reason_code="review_accepted",
            proposal=proposal,
        )

    @staticmethod
    def _history_tuple(history) -> tuple[tuple[object, ...], ...]:
        return tuple(
            (
                item.sequence,
                item.event_type,
                item.from_state,
                item.to_state,
                item.actor,
            )
            for item in history
        )

    @staticmethod
    def _invalid() -> GovernedExecutionExperienceTrustEligibilityAssessment:
        return GovernedExecutionExperienceTrustEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )

    @staticmethod
    def _require_digest(value: str, message: str) -> None:
        if type(value) is not str or _HEX.fullmatch(value) is None:
            raise ExecutionExperienceTrustValidationError(message)

    def _require_trusted(self, trusted_id: UUID):
        record = self._trusted_repository.get(str(trusted_id))
        if record is None:
            raise ExecutionExperienceTrustNotFoundError(
                "The trusted execution experience was not found."
            )
        return record

    @staticmethod
    def _proposal_response(
        proposal: GovernedExecutionExperienceTrustPromotionProposal,
    ) -> ExecutionExperienceTrustPromotionProposalResponse:
        return ExecutionExperienceTrustPromotionProposalResponse(
            workspace_id=proposal.workspace_id.value,
            conversation_id=proposal.conversation_id,
            source_turn_id=proposal.source_turn_id,
            source_artifact_digest=proposal.source_artifact_digest,
            intent_digest=proposal.intent_digest,
            approval_id=proposal.approval_id,
            execution_request_id=proposal.execution_request_id,
            plan_digest=proposal.plan_digest,
            source_feedback_fingerprint=proposal.source_feedback_fingerprint,
            source_candidate_fingerprint=proposal.source_candidate_fingerprint,
            source_review_fingerprint=proposal.source_review_fingerprint,
            source_d186_record_fingerprint=proposal.source_d186_record_fingerprint,
            target_kind=proposal.target_kind,
            capability_id=proposal.capability_id,
            adapter_id=proposal.adapter_id,
            operation=proposal.operation,
            effect=proposal.effect,
            risk_class=proposal.risk_class,
            source_classification=proposal.source_classification,
            experience_outcome_class=proposal.experience_outcome_class,
            experience_lesson_code=proposal.experience_lesson_code,
            review_reason_code=proposal.review_reason_code,
            promotion_fingerprint=proposal.promotion_fingerprint,
            contract_version=proposal.contract_version,
        )

    @classmethod
    def _eligibility_response(
        cls,
        review_id: UUID,
        assessment: GovernedExecutionExperienceTrustEligibilityAssessment,
    ) -> ExecutionExperienceTrustEligibilityResponse:
        return ExecutionExperienceTrustEligibilityResponse(
            review_id=review_id,
            eligibility=assessment.eligibility,
            reason_code=assessment.reason_code,
            proposal=(
                None
                if assessment.proposal is None
                else cls._proposal_response(assessment.proposal)
            ),
        )

    @staticmethod
    def _response(record) -> TrustedExecutionExperienceResponse:
        return TrustedExecutionExperienceResponse(
            id=UUID(record.id),
            workspace_id=record.workspace_id,
            source_review_id=UUID(record.source_review_id),
            conversation_id=UUID(record.conversation_id),
            source_turn_id=record.source_turn_id,
            source_artifact_digest=record.source_artifact_digest,
            intent_digest=record.intent_digest,
            approval_id=record.approval_id,
            execution_request_id=record.execution_request_id,
            plan_digest=record.plan_digest,
            source_feedback_fingerprint=record.source_feedback_fingerprint,
            source_candidate_fingerprint=record.source_candidate_fingerprint,
            source_review_fingerprint=record.source_review_fingerprint,
            source_d186_record_fingerprint=record.source_d186_record_fingerprint,
            target_kind=record.target_kind,
            capability_id=record.capability_id,
            adapter_id=record.adapter_id,
            operation=record.operation,
            effect=record.effect,
            risk_class=record.risk_class,
            source_classification=record.source_classification,
            experience_outcome_class=record.experience_outcome_class,
            experience_lesson_code=record.experience_lesson_code,
            review_reason_code=record.review_reason_code,
            promotion_fingerprint=record.promotion_fingerprint,
            contract_version=record.contract_version,
            state=record.state,
            current_revision=record.current_revision,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


__all__ = [
    "ExecutionExperienceTrustConflictError",
    "ExecutionExperienceTrustLifecycleService",
    "ExecutionExperienceTrustNotFoundError",
    "ExecutionExperienceTrustValidationError",
]
