from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.contracts.cognitive_trusted_experience import CognitiveTrustedExperienceProposal
from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.trusted_experience import (
    TrustedExperienceEventRecord,
    TrustedExperienceRecord,
)


class TrustedExperienceRepository:
    """Workspace-scoped D147 durable lifecycle persistence boundary."""

    def __init__(self, session: Session, workspace_scope: WorkspaceScope) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def create_pending(
        self,
        proposal: CognitiveTrustedExperienceProposal,
    ) -> TrustedExperienceRecord:
        if proposal.workspace_id.value != self._workspace_id:
            raise ValueError("workspace_mismatch")
        record = TrustedExperienceRecord(
            workspace_id=self._workspace_id,
            contract_version=proposal.contract_version,
            source_candidate_fingerprint=proposal.source_candidate_fingerprint,
            source_feedback_fingerprint=proposal.source_feedback_fingerprint,
            proposal_fingerprint=proposal.proposal_fingerprint,
            quality_classification=proposal.quality_classification,
            quality_reason_code=proposal.quality_reason_code,
            lesson_code=proposal.lesson_code,
            interaction_intent=proposal.interaction_intent,
            cognitive_intent=proposal.cognitive_intent,
            authoritative_ai_task_kind=proposal.authoritative_ai_task_kind.value,
            observed_confidence_class=proposal.observed_confidence_class,
            authorized_adapter_id=proposal.authorized_adapter_id,
            authorized_model_id=proposal.authorized_model_id,
            authorized_profile_id=proposal.authorized_profile_id,
            source_revision_count=proposal.source_revision_count,
            state="PENDING_REVIEW",
            current_revision=1,
        )
        self._session.add(record)
        self._session.flush()
        self._session.add(
            TrustedExperienceEventRecord(
                trusted_experience_id=record.id,
                sequence=1,
                event_type="PROPOSED",
                from_state=None,
                to_state="PENDING_REVIEW",
                actor="SYSTEM",
                decision_comment=None,
            )
        )
        self._session.flush()
        return record

    def get(self, record_id: str) -> TrustedExperienceRecord | None:
        return self._session.scalar(
            select(TrustedExperienceRecord).where(
                TrustedExperienceRecord.id == record_id,
                TrustedExperienceRecord.workspace_id == self._workspace_id,
            )
        )

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[TrustedExperienceRecord], int]:
        filters = [TrustedExperienceRecord.workspace_id == self._workspace_id]
        if state is not None:
            filters.append(TrustedExperienceRecord.state == state)
        statement = (
            select(TrustedExperienceRecord)
            .where(*filters)
            .order_by(
                TrustedExperienceRecord.updated_at.desc(),
                TrustedExperienceRecord.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (
            self._session.scalar(
                select(func.count(TrustedExperienceRecord.id)).where(*filters)
            )
            or 0
        )
        return self._session.scalars(statement).all(), total

    def history(
        self,
        record_id: str,
    ) -> Sequence[TrustedExperienceEventRecord]:
        return self._session.scalars(
            select(TrustedExperienceEventRecord)
            .join(
                TrustedExperienceRecord,
                TrustedExperienceRecord.id
                == TrustedExperienceEventRecord.trusted_experience_id,
            )
            .where(
                TrustedExperienceEventRecord.trusted_experience_id == record_id,
                TrustedExperienceRecord.workspace_id == self._workspace_id,
            )
            .order_by(TrustedExperienceEventRecord.sequence)
        ).all()

    def transition(
        self,
        *,
        record_id: str,
        expected_revision: int,
        expected_state: str,
        target_state: str,
        event_type: str,
        decision_comment: str,
    ) -> TrustedExperienceRecord | None:
        next_revision = expected_revision + 1
        result = self._session.execute(
            update(TrustedExperienceRecord)
            .where(
                TrustedExperienceRecord.id == record_id,
                TrustedExperienceRecord.workspace_id == self._workspace_id,
                TrustedExperienceRecord.state == expected_state,
                TrustedExperienceRecord.current_revision == expected_revision,
            )
            .values(
                state=target_state,
                current_revision=next_revision,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            return None
        self._session.add(
            TrustedExperienceEventRecord(
                trusted_experience_id=record_id,
                sequence=next_revision,
                event_type=event_type,
                from_state=expected_state,
                to_state=target_state,
                actor="OWNER",
                decision_comment=decision_comment,
            )
        )
        self._session.flush()
        return self.get(record_id)

    def state_counts(self) -> dict[str, int]:
        result = {
            "PENDING_REVIEW": 0,
            "TRUSTED": 0,
            "REJECTED": 0,
            "REVOKED": 0,
        }
        rows = self._session.execute(
            select(
                TrustedExperienceRecord.state,
                func.count(TrustedExperienceRecord.id),
            )
            .where(TrustedExperienceRecord.workspace_id == self._workspace_id)
            .group_by(TrustedExperienceRecord.state)
        ).all()
        for state, count in rows:
            if state in result:
                result[state] = int(count)
        return result

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
