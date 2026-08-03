"""Durable atomic claiming for Project action execution proposals."""

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)


class ProjectActionExecutionClaimService:
    """Atomically claim an eligible proposal without executing its action."""

    def __init__(
        self,
        repository: ProjectActionExecutionProposalRepository,
    ) -> None:
        self._repository = repository

    def claim(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._repository.get(proposal_id)

        if proposal is None:
            raise ValueError(
                "Execution proposal was not found."
            )

        claimed = self._repository.claim_if_executable(
            proposal_id,
        )

        if not claimed:
            self._repository.rollback()
            raise ValueError(
                "Execution proposal is not eligible to be claimed."
            )

        self._repository.commit()

        updated = self._repository.get(proposal_id)

        if updated is None:
            raise ValueError(
                "Execution proposal was not found after claim."
            )

        return updated