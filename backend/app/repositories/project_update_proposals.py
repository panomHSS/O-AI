from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.models.project_update_proposal import ProjectUpdateProposal


class ProjectUpdateProposalRepository:
    """Persistence boundary for durable Project update proposals."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        project_id: str,
        conversation_id: str,
        base_revision: int,
        proposed_summary: str | None,
        proposed_next_action: str | None,
        reason: str,
    ) -> ProjectUpdateProposal:
        proposal = ProjectUpdateProposal(
            project_id=project_id,
            conversation_id=conversation_id,
            base_revision=base_revision,
            proposed_summary=proposed_summary,
            proposed_next_action=proposed_next_action,
            reason=reason,
            status="PENDING",
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def get(self, proposal_id: str) -> ProjectUpdateProposal | None:
        return self._session.get(ProjectUpdateProposal, proposal_id)

    def list_for_project(
        self,
        project_id: str,
        status: str | None = None,
    ) -> Sequence[ProjectUpdateProposal]:
        statement = select(ProjectUpdateProposal).where(
            ProjectUpdateProposal.project_id == project_id
        )

        if status is not None:
            statement = statement.where(
                ProjectUpdateProposal.status == status
            )

        return self._session.scalars(
            statement.order_by(
                ProjectUpdateProposal.created_at.desc(),
                ProjectUpdateProposal.id.desc(),
            )
        ).all()

    def decide_if_pending(
        self,
        proposal_id: str,
        status: str,
        applied_revision: int | None = None,
    ) -> ProjectUpdateProposal | None:
        result = self._session.execute(
            update(ProjectUpdateProposal)
            .where(
                ProjectUpdateProposal.id == proposal_id,
                ProjectUpdateProposal.status == "PENDING",
            )
            .values(
                status=status,
                decided_at=utc_now(),
                applied_revision=applied_revision,
            )
        )

        if result.rowcount != 1:
            return None

        return self._session.get(ProjectUpdateProposal, proposal_id)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()