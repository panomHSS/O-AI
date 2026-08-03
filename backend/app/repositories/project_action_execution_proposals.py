"""Persistence boundary for Project action execution proposals."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.models.project import Project

class ProjectActionExecutionProposalRepository:
    """Persist durable Project action execution proposals."""

    def __init__(
        self,
        session: Session
    ) -> None:
        self._session = session

    def create(
        self,
        project_id: str,
        conversation_id: str,
        project_revision: int,
        source_action: str,
        steps: list[dict],
    ) -> ProjectActionExecutionProposalRecord:
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
        return self._session.get(
            ProjectActionExecutionProposalRecord,
            proposal_id,
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
                ProjectActionExecutionProposalRecord.id
                == proposal_id,
                ProjectActionExecutionProposalRecord.status
                == "PENDING",
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
        matching_project_revision = (
            select(Project.id)
            .where(
                Project.id
                == ProjectActionExecutionProposalRecord.project_id,
                Project.current_revision
                == ProjectActionExecutionProposalRecord.project_revision,
            )
            .exists()
        )

        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id
                == proposal_id,
                ProjectActionExecutionProposalRecord.status
                == "APPROVED",
                ProjectActionExecutionProposalRecord.approved
                .is_(True),
                ProjectActionExecutionProposalRecord.executed
                .is_(False),
                matching_project_revision,
            )
            .values(
                status="EXECUTING",
            )
        )

        return result.rowcount == 1

    def complete_if_executing(
        self,
        proposal_id: str,
    ) -> bool:
        result = self._session.execute(
            update(ProjectActionExecutionProposalRecord)
            .where(
                ProjectActionExecutionProposalRecord.id
                == proposal_id,
                ProjectActionExecutionProposalRecord.status
                == "EXECUTING",
                ProjectActionExecutionProposalRecord.approved
                .is_(True),
                ProjectActionExecutionProposalRecord.executed
                .is_(False),
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
                ProjectActionExecutionProposalRecord.id
                == proposal_id,
                ProjectActionExecutionProposalRecord.status
                == "EXECUTING",
                ProjectActionExecutionProposalRecord.approved
                .is_(True),
                ProjectActionExecutionProposalRecord.executed
                .is_(False),
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
                ProjectActionExecutionProposalRecord.project_id
                == project_id
            )
            .order_by(
                ProjectActionExecutionProposalRecord.id.asc(),
            )
        )

        return list(
            self._session.scalars(statement).all()
        )
    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()