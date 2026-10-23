from __future__ import annotations

import re
from uuid import UUID

from app.contracts.governed_execution_experience_owner_review import (
    GovernedExecutionExperienceOwnerReviewProposal,
    compute_governed_execution_experience_owner_review_record_fingerprint,
)
from app.contracts.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewProposal,
)
from app.contracts.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeOutcome,
)
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.schemas.execution_experience_reviews import (
    ExecutionExperienceReviewEventResponse,
    ExecutionExperienceReviewHistoryResponse,
    ExecutionExperienceReviewListResponse,
    ExecutionExperienceReviewResponse,
)
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeStore,
)

_HEX = re.compile(r"^[0-9a-f]{64}$")


class ExecutionExperienceReviewNotFoundError(Exception):
    pass


class ExecutionExperienceReviewConflictError(Exception):
    pass


class ExecutionExperienceReviewValidationError(Exception):
    pass


class ExecutionExperienceReviewLifecycleService:
    """D186 durable explicit Owner review; never trust or learning authority."""

    def __init__(
        self,
        *,
        repository: ExecutionExperienceReviewRepository,
        runtime_store: GovernedExecutionExperienceRuntimeStore,
    ) -> None:
        if not isinstance(repository, ExecutionExperienceReviewRepository):
            raise TypeError(
                "repository must be an ExecutionExperienceReviewRepository."
            )
        if not isinstance(runtime_store, GovernedExecutionExperienceRuntimeStore):
            raise TypeError(
                "runtime_store must be a GovernedExecutionExperienceRuntimeStore."
            )
        self._repository = repository
        self._runtime_store = runtime_store

    def try_capture(self, approval_id: str) -> bool:
        """Best-effort post-authority capture. Never propagate into execution."""
        try:
            return self.capture(approval_id) is not None
        except Exception:
            self._repository.rollback()
            return False

    def capture(
        self,
        approval_id: str,
    ) -> ExecutionExperienceReviewResponse | None:
        outcome = self._runtime_store.get(approval_id)
        if outcome is None:
            return None
        if type(outcome) is not GovernedExecutionExperienceRuntimeOutcome:
            raise ExecutionExperienceReviewValidationError(
                "D185 runtime evidence is invalid."
            )
        try:
            outcome.__post_init__()
        except Exception as error:
            raise ExecutionExperienceReviewValidationError(
                "D185 runtime evidence failed validation."
            ) from error

        if outcome.runtime_status != "review_eligible":
            return None
        if outcome.review is None or outcome.review.proposal is None:
            raise ExecutionExperienceReviewValidationError(
                "Eligible D185 runtime evidence has no review proposal."
            )
        source = outcome.review.proposal
        if type(source) is not GovernedExecutionExperienceReviewProposal:
            raise ExecutionExperienceReviewValidationError(
                "D184 review proposal is invalid."
            )
        try:
            source.__post_init__()
        except Exception as error:
            raise ExecutionExperienceReviewValidationError(
                "D184 review proposal failed validation."
            ) from error

        if (
            source.approval_id != approval_id
            or source.workspace_id.value != self._repository.workspace_id
            or outcome.source_feedback_fingerprint != source.source_feedback_fingerprint
            or outcome.candidate is None
            or outcome.candidate.candidate_fingerprint
            != source.source_candidate_fingerprint
        ):
            raise ExecutionExperienceReviewValidationError(
                "D185 review lineage does not match the workspace or approval."
            )

        proposal = self._project(source)

        existing = self._repository.get_by_source_review_fingerprint(
            proposal.source_review_fingerprint
        )
        if existing is not None:
            if (
                existing.record_fingerprint == proposal.record_fingerprint
                and existing.approval_id == proposal.approval_id
            ):
                return self._response(existing)
            raise ExecutionExperienceReviewConflictError(
                "The D184 review identity already maps to different D186 evidence."
            )

        approval_existing = self._repository.get_by_approval_id(proposal.approval_id)
        if approval_existing is not None:
            if (
                approval_existing.source_review_fingerprint
                == proposal.source_review_fingerprint
                and approval_existing.record_fingerprint
                == proposal.record_fingerprint
            ):
                return self._response(approval_existing)
            raise ExecutionExperienceReviewConflictError(
                "The execution approval already maps to different D186 evidence."
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
    ) -> ExecutionExperienceReviewListResponse:
        records, total = self._repository.list(state, page, page_size)
        return ExecutionExperienceReviewListResponse(
            items=[self._response(item) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get(self, review_id: UUID) -> ExecutionExperienceReviewResponse:
        return self._response(self._require(review_id))

    def history(self, review_id: UUID) -> ExecutionExperienceReviewHistoryResponse:
        record = self._require(review_id)
        return ExecutionExperienceReviewHistoryResponse(
            execution_experience_review_id=UUID(record.id),
            items=[
                ExecutionExperienceReviewEventResponse(
                    sequence=item.sequence,
                    event_type=item.event_type,
                    from_state=item.from_state,
                    to_state=item.to_state,
                    actor=item.actor,
                    created_at=item.created_at,
                )
                for item in self._repository.history(record.id)
            ],
        )

    def accept(
        self,
        review_id: UUID,
        expected_revision: int,
        source_review_fingerprint: str,
    ) -> ExecutionExperienceReviewResponse:
        return self._transition(
            review_id=review_id,
            expected_revision=expected_revision,
            source_review_fingerprint=source_review_fingerprint,
            target_state="REVIEW_ACCEPTED",
            event_type="OWNER_ACCEPTED",
        )

    def reject(
        self,
        review_id: UUID,
        expected_revision: int,
        source_review_fingerprint: str,
    ) -> ExecutionExperienceReviewResponse:
        return self._transition(
            review_id=review_id,
            expected_revision=expected_revision,
            source_review_fingerprint=source_review_fingerprint,
            target_state="REVIEW_REJECTED",
            event_type="OWNER_REJECTED",
        )

    def _transition(
        self,
        *,
        review_id: UUID,
        expected_revision: int,
        source_review_fingerprint: str,
        target_state: str,
        event_type: str,
    ) -> ExecutionExperienceReviewResponse:
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision != 1
        ):
            raise ExecutionExperienceReviewConflictError(
                "The execution experience review revision or state changed."
            )
        if (
            type(source_review_fingerprint) is not str
            or _HEX.fullmatch(source_review_fingerprint) is None
        ):
            raise ExecutionExperienceReviewValidationError(
                "The source review fingerprint is invalid."
            )

        record = self._require(review_id)
        if record.source_review_fingerprint != source_review_fingerprint:
            raise ExecutionExperienceReviewValidationError(
                "The source review fingerprint does not match."
            )
        if record.state != "PENDING_REVIEW" or record.current_revision != 1:
            raise ExecutionExperienceReviewConflictError(
                "The execution experience review revision or state changed."
            )
        try:
            updated = self._repository.transition(
                record_id=record.id,
                expected_revision=expected_revision,
                source_review_fingerprint=source_review_fingerprint,
                target_state=target_state,
                event_type=event_type,
            )
            if updated is None:
                raise ExecutionExperienceReviewConflictError(
                    "The execution experience review revision or state changed."
                )
            self._repository.commit()
            return self._response(updated)
        except Exception:
            self._repository.rollback()
            raise

    def _require(self, review_id: UUID):
        record = self._repository.get(str(review_id))
        if record is None:
            raise ExecutionExperienceReviewNotFoundError(
                "The requested execution experience review was not found."
            )
        return record

    @staticmethod
    def _project(
        source: GovernedExecutionExperienceReviewProposal,
    ) -> GovernedExecutionExperienceOwnerReviewProposal:
        fingerprint = compute_governed_execution_experience_owner_review_record_fingerprint(
            workspace_id=source.workspace_id,
            conversation_id=source.conversation_id,
            source_turn_id=source.source_turn_id,
            source_artifact_digest=source.source_artifact_digest,
            intent_digest=source.intent_digest,
            approval_id=source.approval_id,
            execution_request_id=source.execution_request_id,
            plan_digest=source.plan_digest,
            source_feedback_fingerprint=source.source_feedback_fingerprint,
            source_candidate_fingerprint=source.source_candidate_fingerprint,
            source_review_fingerprint=source.review_fingerprint,
            target_kind=source.target_kind,
            capability_id=source.capability_id,
            adapter_id=source.adapter_id,
            operation=source.operation,
            effect=source.effect,
            risk_class=source.risk_class,
            source_classification=source.source_classification,
            experience_outcome_class=source.experience_outcome_class,
            experience_lesson_code=source.experience_lesson_code,
            review_reason_code=source.review_reason_code,
        )
        return GovernedExecutionExperienceOwnerReviewProposal(
            workspace_id=source.workspace_id,
            conversation_id=source.conversation_id,
            source_turn_id=source.source_turn_id,
            source_artifact_digest=source.source_artifact_digest,
            intent_digest=source.intent_digest,
            approval_id=source.approval_id,
            execution_request_id=source.execution_request_id,
            plan_digest=source.plan_digest,
            source_feedback_fingerprint=source.source_feedback_fingerprint,
            source_candidate_fingerprint=source.source_candidate_fingerprint,
            source_review_fingerprint=source.review_fingerprint,
            target_kind=source.target_kind,
            capability_id=source.capability_id,
            adapter_id=source.adapter_id,
            operation=source.operation,
            effect=source.effect,
            risk_class=source.risk_class,
            source_classification=source.source_classification,
            experience_outcome_class=source.experience_outcome_class,
            experience_lesson_code=source.experience_lesson_code,
            review_reason_code=source.review_reason_code,
            record_fingerprint=fingerprint,
        )

    @staticmethod
    def _response(record) -> ExecutionExperienceReviewResponse:
        return ExecutionExperienceReviewResponse(
            id=UUID(record.id),
            workspace_id=record.workspace_id,
            contract_version=record.contract_version,
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
            record_fingerprint=record.record_fingerprint,
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
            state=record.state,
            current_revision=record.current_revision,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


__all__ = [
    "ExecutionExperienceReviewConflictError",
    "ExecutionExperienceReviewLifecycleService",
    "ExecutionExperienceReviewNotFoundError",
    "ExecutionExperienceReviewValidationError",
]
