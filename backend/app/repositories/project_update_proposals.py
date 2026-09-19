from collections.abc import Sequence

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.project_update_proposal import ProjectUpdateProposal


class ProjectUpdateProposalRepository:
    """Workspace-scoped persistence boundary for Project update proposals."""

    def __init__(
        self,
        session: Session,
        workspace_scope: WorkspaceScope,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    def create(
        self,
        project_id: str,
        conversation_id: str,
        base_revision: int,
        proposed_summary: str | None,
        proposed_next_action: str | None,
        reason: str,
    ) -> ProjectUpdateProposal:
        if not self._parents_match(project_id, conversation_id):
            raise ValueError("workspace_mismatch")

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

    def get(
        self,
        proposal_id: str,
    ) -> ProjectUpdateProposal | None:
        return self._session.scalar(
            select(ProjectUpdateProposal).where(
                ProjectUpdateProposal.id == proposal_id,
                self._project_visible(),
                self._conversation_visible(),
            )
        )

    def list_for_project(
        self,
        project_id: str,
        status: str | None = None,
    ) -> Sequence[ProjectUpdateProposal]:
        statement = select(ProjectUpdateProposal).where(
            ProjectUpdateProposal.project_id == project_id,
            self._project_visible(),
            self._conversation_visible(),
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
                self._project_visible(),
                self._conversation_visible(),
            )
            .values(
                status=status,
                decided_at=utc_now(),
                applied_revision=applied_revision,
            )
        )

        if result.rowcount != 1:
            return None

        return self.get(proposal_id)

    def _project_visible(self):
        return exists(
            select(Project.id).where(
                Project.id == ProjectUpdateProposal.project_id,
                Project.workspace_id == self._workspace_id,
            )
        )

    def _conversation_visible(self):
        return exists(
            select(Conversation.id).where(
                Conversation.id == ProjectUpdateProposal.conversation_id,
                Conversation.project_id == ProjectUpdateProposal.project_id,
                Conversation.workspace_id == self._workspace_id,
            )
        )

    def _parents_match(
        self,
        project_id: str,
        conversation_id: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(Project.id)
                .join(
                    Conversation,
                    Conversation.project_id == Project.id,
                )
                .where(
                    Project.id == project_id,
                    Project.workspace_id == self._workspace_id,
                    Conversation.id == conversation_id,
                    Conversation.workspace_id == self._workspace_id,
                )
                .limit(1)
            )
            is not None
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
