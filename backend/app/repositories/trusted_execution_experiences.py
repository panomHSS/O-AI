from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.contracts.governed_execution_experience_trust import (
    GovernedExecutionExperienceTrustPromotionProposal,
)
from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.trusted_execution_experience import (
    TrustedExecutionExperienceEventRecord,
    TrustedExecutionExperienceRecord,
)


class TrustedExecutionExperienceRepository:
    """Workspace-scoped D187 trusted execution-experience repository."""

    def __init__(self, session: Session, workspace_scope: WorkspaceScope) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def create_trusted(
        self,
        *,
        source_review_id: str,
        proposal: GovernedExecutionExperienceTrustPromotionProposal,
    ) -> TrustedExecutionExperienceRecord:
        if proposal.workspace_id.value != self._workspace_id:
            raise ValueError("workspace_mismatch")
        record = TrustedExecutionExperienceRecord(
            workspace_id=self._workspace_id,
            source_review_id=source_review_id,
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
            state="TRUSTED",
            current_revision=1,
        )
        self._session.add(record)
        self._session.flush()
        self._session.add(
            TrustedExecutionExperienceEventRecord(
                trusted_execution_experience_id=record.id,
                sequence=1,
                event_type="OWNER_PROMOTED",
                from_state=None,
                to_state="TRUSTED",
                actor="OWNER",
            )
        )
        self._session.flush()
        return record

    def get(self, record_id: str) -> TrustedExecutionExperienceRecord | None:
        return self._session.scalar(
            select(TrustedExecutionExperienceRecord).where(
                TrustedExecutionExperienceRecord.id == record_id,
                TrustedExecutionExperienceRecord.workspace_id == self._workspace_id,
            )
        )

    def get_by_source_review_id(
        self,
        source_review_id: str,
    ) -> TrustedExecutionExperienceRecord | None:
        return self._session.scalar(
            select(TrustedExecutionExperienceRecord).where(
                TrustedExecutionExperienceRecord.source_review_id == source_review_id,
                TrustedExecutionExperienceRecord.workspace_id == self._workspace_id,
            )
        )

    def get_by_promotion_fingerprint(
        self,
        promotion_fingerprint: str,
    ) -> TrustedExecutionExperienceRecord | None:
        return self._session.scalar(
            select(TrustedExecutionExperienceRecord).where(
                TrustedExecutionExperienceRecord.promotion_fingerprint
                == promotion_fingerprint,
                TrustedExecutionExperienceRecord.workspace_id == self._workspace_id,
            )
        )

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[TrustedExecutionExperienceRecord], int]:
        filters = [
            TrustedExecutionExperienceRecord.workspace_id == self._workspace_id
        ]
        if state is not None:
            filters.append(TrustedExecutionExperienceRecord.state == state)
        statement = (
            select(TrustedExecutionExperienceRecord)
            .where(*filters)
            .order_by(
                TrustedExecutionExperienceRecord.updated_at.desc(),
                TrustedExecutionExperienceRecord.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = self._session.scalar(
            select(func.count(TrustedExecutionExperienceRecord.id)).where(*filters)
        ) or 0
        return self._session.scalars(statement).all(), int(total)

    def history(
        self,
        record_id: str,
    ) -> Sequence[TrustedExecutionExperienceEventRecord]:
        return self._session.scalars(
            select(TrustedExecutionExperienceEventRecord)
            .join(
                TrustedExecutionExperienceRecord,
                TrustedExecutionExperienceRecord.id
                == TrustedExecutionExperienceEventRecord.trusted_execution_experience_id,
            )
            .where(
                TrustedExecutionExperienceEventRecord.trusted_execution_experience_id
                == record_id,
                TrustedExecutionExperienceRecord.workspace_id == self._workspace_id,
            )
            .order_by(TrustedExecutionExperienceEventRecord.sequence)
        ).all()

    def revoke(
        self,
        *,
        record_id: str,
        expected_revision: int,
        promotion_fingerprint: str,
    ) -> TrustedExecutionExperienceRecord | None:
        result = self._session.execute(
            update(TrustedExecutionExperienceRecord)
            .where(
                TrustedExecutionExperienceRecord.id == record_id,
                TrustedExecutionExperienceRecord.workspace_id == self._workspace_id,
                TrustedExecutionExperienceRecord.state == "TRUSTED",
                TrustedExecutionExperienceRecord.current_revision == expected_revision,
                TrustedExecutionExperienceRecord.promotion_fingerprint
                == promotion_fingerprint,
            )
            .values(
                state="REVOKED",
                current_revision=2,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            return None
        self._session.add(
            TrustedExecutionExperienceEventRecord(
                trusted_execution_experience_id=record_id,
                sequence=2,
                event_type="OWNER_REVOKED",
                from_state="TRUSTED",
                to_state="REVOKED",
                actor="OWNER",
            )
        )
        self._session.flush()
        return self.get(record_id)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
