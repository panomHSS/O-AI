"""Workspace-scoped persistence boundary for Project action execution proposals."""

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceScope
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)


class ProjectActionExecutionProposalRepository:
    """Persist Project action proposals through exact parent workspace scope."""

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
        project_revision: int,
        source_action: str,
        steps: list[dict],
    ) -> ProjectActionExecutionProposalRecord:
        if not self._parents_match(project_id, conversation_id):
            raise ValueError("workspace_mismatch")

        proposal = ProjectActionExecutionProposalRecord(
            project_id=project_id,
            conversation_id=conversation_id,
            project_revision=project_revision,
            source_action=source_action,
            steps=steps,
            status="PENDING",
            approved=False,
            executed=False,
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def get(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord | None:
        return self._session.scalar(
            select(ProjectActionExecutionProposalRecord).where(
                ProjectActionExecutionProposalRecord.id == proposal_id,
                self._project_visible(),
                self._conversation_visible(),
            )
        )

    def decide_if_pending(
        self,
        proposal_id: str,
        *,
        status: str,
        approved: bool,
    ) -> bool:
        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id == proposal_id,
                ProjectActionExecutionProposalRecord.status == "PENDING",
                self._project_visible(),
                self._conversation_visible(),
            )
            .values(
                status=status,
                approved=approved,
                executed=False,
            )
        )
        return result.rowcount == 1

    def claim_if_executable(
        self,
        proposal_id: str,
    ) -> bool:
        matching_project_revision = exists(
            select(Project.id).where(
                Project.id
                == ProjectActionExecutionProposalRecord.project_id,
                Project.workspace_id == self._workspace_id,
                Project.current_revision
                == ProjectActionExecutionProposalRecord.project_revision,
            )
        )

        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id == proposal_id,
                ProjectActionExecutionProposalRecord.status == "APPROVED",
                ProjectActionExecutionProposalRecord.approved.is_(True),
                ProjectActionExecutionProposalRecord.executed.is_(False),
                matching_project_revision,
                self._conversation_visible(),
            )
            .values(status="EXECUTING")
        )
        return result.rowcount == 1

    def complete_if_executing(
        self,
        proposal_id: str,
    ) -> bool:
        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id == proposal_id,
                ProjectActionExecutionProposalRecord.status == "EXECUTING",
                ProjectActionExecutionProposalRecord.approved.is_(True),
                ProjectActionExecutionProposalRecord.executed.is_(False),
                self._project_visible(),
                self._conversation_visible(),
            )
            .values(
                status="EXECUTED",
                executed=True,
            )
        )
        return result.rowcount == 1

    def fail_if_executing(
        self,
        proposal_id: str,
    ) -> bool:
        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id == proposal_id,
                ProjectActionExecutionProposalRecord.status == "EXECUTING",
                ProjectActionExecutionProposalRecord.approved.is_(True),
                ProjectActionExecutionProposalRecord.executed.is_(False),
                self._project_visible(),
                self._conversation_visible(),
            )
            .values(
                status="FAILED",
                executed=False,
            )
        )
        return result.rowcount == 1

    def list_for_project(
        self,
        project_id: str,
    ) -> list[ProjectActionExecutionProposalRecord]:
        statement = (
            select(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.project_id == project_id,
                self._project_visible(),
                self._conversation_visible(),
            )
            .order_by(
                ProjectActionExecutionProposalRecord.id.asc(),
            )
        )
        return list(self._session.scalars(statement).all())

    def _project_visible(self):
        return exists(
            select(Project.id).where(
                Project.id
                == ProjectActionExecutionProposalRecord.project_id,
                Project.workspace_id == self._workspace_id,
            )
        )

    def _conversation_visible(self):
        return exists(
            select(Conversation.id).where(
                Conversation.id
                == ProjectActionExecutionProposalRecord.conversation_id,
                Conversation.project_id
                == ProjectActionExecutionProposalRecord.project_id,
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
