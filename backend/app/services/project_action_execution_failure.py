"""Durable failure handling for Project action execution proposals."""

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)


class ProjectActionExecutionFailureService:
    """Persist failed execution of a claimed Project action."""

    def __init__(
        self,
        repository: ProjectActionExecutionProposalRepository,
    ) -> None:
        self._repository = repository

    def fail(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._repository.get(proposal_id)

        if proposal is None:
            raise ValueError(
                "Execution proposal was not found."
            )

        failed = self._repository.fail_if_executing(
            proposal_id,
        )

        if not failed:
            self._repository.rollback()
            raise ValueError(
                "Execution proposal is not executing."
            )

        self._repository.commit()

        updated = self._repository.get(proposal_id)

        if updated is None:
            raise ValueError(
                "Execution proposal was not found after failure."
            )

        return updated