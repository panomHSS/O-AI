"""Read-only lookup boundary for Project action execution proposals."""

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)


class ProjectActionExecutionLookupService:
    """Read execution proposals without changing execution state."""

    def __init__(
        self,
        repository: ProjectActionExecutionProposalRepository,
    ) -> None:
        self._repository = repository

    def get(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._repository.get(
            proposal_id,
        )

        if proposal is None:
            raise ValueError(
                "Execution proposal was not found."
            )

        return proposal