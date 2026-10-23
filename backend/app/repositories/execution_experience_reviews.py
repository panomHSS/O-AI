from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.contracts.governed_execution_experience_owner_review import (
    GovernedExecutionExperienceOwnerReviewProposal,
)
from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.execution_experience_review import (
    ExecutionExperienceReviewEventRecord,
    ExecutionExperienceReviewRecord,
)


class ExecutionExperienceReviewRepository:
    """Workspace-scoped durable D186 Owner-review repository."""

    def __init__(self, session: Session, workspace_scope: WorkspaceScope) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def create_pending(
        self,
        proposal: GovernedExecutionExperienceOwnerReviewProposal,
    ) -> ExecutionExperienceReviewRecord:
        if proposal.workspace_id.value != self._workspace_id:
            raise ValueError("workspace_mismatch")
        record = ExecutionExperienceReviewRecord(
            workspace_id=self._workspace_id,
            conversation_id=str(proposal.conversation_id),
            source_turn_id=proposal.source_turn_id,
            source_artifact_digest=proposal.source_artifact_digest,
            intent_digest=proposal.intent_digest,
            approval_id=proposal.approval_id,
            execution_request_id=proposal.execution_request_id,
            plan_digest=proposal.plan_digest,
            source_feedback_fingerprint=proposal.source_feedback_fingerprint,
            source_candidate_fingerprint=proposal.source_candidate_fingerprint,
            source_review_fingerprint=proposal.source_review_fingerprint,
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
            record_fingerprint=proposal.record_fingerprint,
            contract_version=proposal.contract_version,
            state="PENDING_REVIEW",
            current_revision=1,
        )
        self._session.add(record)
        self._session.flush()
        self._session.add(
            ExecutionExperienceReviewEventRecord(
                execution_experience_review_id=record.id,
                sequence=1,
                event_type="PROPOSED",
                from_state=None,
                to_state="PENDING_REVIEW",
                actor="SYSTEM",
            )
        )
        self._session.flush()
        return record

    def get(self, record_id: str) -> ExecutionExperienceReviewRecord | None:
        return self._session.scalar(
            select(ExecutionExperienceReviewRecord).where(
                ExecutionExperienceReviewRecord.id == record_id,
                ExecutionExperienceReviewRecord.workspace_id == self._workspace_id,
            )
        )

    def get_by_source_review_fingerprint(
        self,
        source_review_fingerprint: str,
    ) -> ExecutionExperienceReviewRecord | None:
        return self._session.scalar(
            select(ExecutionExperienceReviewRecord).where(
                ExecutionExperienceReviewRecord.source_review_fingerprint == source_review_fingerprint,
                ExecutionExperienceReviewRecord.workspace_id == self._workspace_id,
            )
        )

    def get_by_approval_id(self, approval_id: str) -> ExecutionExperienceReviewRecord | None:
        return self._session.scalar(
            select(ExecutionExperienceReviewRecord).where(
                ExecutionExperienceReviewRecord.approval_id == approval_id,
                ExecutionExperienceReviewRecord.workspace_id == self._workspace_id,
            )
        )

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[ExecutionExperienceReviewRecord], int]:
        filters = [ExecutionExperienceReviewRecord.workspace_id == self._workspace_id]
        if state is not None:
            filters.append(ExecutionExperienceReviewRecord.state == state)
        statement = (
            select(ExecutionExperienceReviewRecord)
            .where(*filters)
            .order_by(
                ExecutionExperienceReviewRecord.updated_at.desc(),
                ExecutionExperienceReviewRecord.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = self._session.scalar(
            select(func.count(ExecutionExperienceReviewRecord.id)).where(*filters)
        ) or 0
        return self._session.scalars(statement).all(), int(total)

    def history(self, record_id: str) -> Sequence[ExecutionExperienceReviewEventRecord]:
        return self._session.scalars(
            select(ExecutionExperienceReviewEventRecord)
            .join(
                ExecutionExperienceReviewRecord,
                ExecutionExperienceReviewRecord.id
                == ExecutionExperienceReviewEventRecord.execution_experience_review_id,
            )
            .where(
                ExecutionExperienceReviewEventRecord.execution_experience_review_id == record_id,
                ExecutionExperienceReviewRecord.workspace_id == self._workspace_id,
            )
            .order_by(ExecutionExperienceReviewEventRecord.sequence)
        ).all()

    def transition(
        self,
        *,
        record_id: str,
        expected_revision: int,
        source_review_fingerprint: str,
        target_state: str,
        event_type: str,
    ) -> ExecutionExperienceReviewRecord | None:
        result = self._session.execute(
            update(ExecutionExperienceReviewRecord)
            .where(
                ExecutionExperienceReviewRecord.id == record_id,
                ExecutionExperienceReviewRecord.workspace_id == self._workspace_id,
                ExecutionExperienceReviewRecord.state == "PENDING_REVIEW",
                ExecutionExperienceReviewRecord.current_revision == expected_revision,
                ExecutionExperienceReviewRecord.source_review_fingerprint == source_review_fingerprint,
            )
            .values(state=target_state, current_revision=2, updated_at=utc_now())
        )
        if result.rowcount != 1:
            return None
        self._session.add(
            ExecutionExperienceReviewEventRecord(
                execution_experience_review_id=record_id,
                sequence=2,
                event_type=event_type,
                from_state="PENDING_REVIEW",
                to_state=target_state,
                actor="OWNER",
            )
        )
        self._session.flush()
        return self.get(record_id)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
