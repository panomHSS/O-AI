"""Persistence orchestration for Project action execution proposals."""

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)


class ProjectActionExecutionPersistenceService:
    """Persist an approval-gated execution proposal."""
    def __init__(
        self,
        repository: ProjectActionExecutionProposalRepository,
    ) -> None:
        self._repository = repository

    def persist(
    self,
    proposal: ProjectActionExecutionProposal,
    *,
    project_id: str,
    conversation_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        if (
            proposal.status != "awaiting_owner_approval"
            or not proposal.owner_approval_required
        ):
            raise ValueError(
                "Execution proposal is not eligible for persistence."
            )

        record = self._repository.create(
            project_id=project_id,
            conversation_id=conversation_id,
            project_revision=proposal.project_revision,
            source_action=proposal.source_action,
            steps=[
                step.model_dump()
                for step in proposal.steps
            ],
        )

        self._repository.commit()

        return record