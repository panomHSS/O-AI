"""Durable owner decisions for Project action execution proposals."""

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)


class ProjectActionExecutionDurableApprovalService:
    """Persist an owner decision without executing the Project action."""

    def __init__(
        self,
        repository: ProjectActionExecutionProposalRepository,
    ) -> None:
        self._repository = repository

    def approve(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._repository.get(proposal_id)

        if proposal is None:
            raise ValueError(
                "Execution proposal was not found."
            )

        decided = self._repository.decide_if_pending(
            proposal_id,
            status="APPROVED",
            approved=True,
        )

        if not decided:
            self._repository.rollback()
            raise ValueError(
                "Execution proposal has already been decided."
            )

        self._repository.commit()

        updated = self._repository.get(proposal_id)

        if updated is None:
            raise ValueError(
                "Execution proposal was not found after approval."
            )

        return updated

    def reject(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._repository.get(proposal_id)

        if proposal is None:
            raise ValueError(
                "Execution proposal was not found."
            )

        decided = self._repository.decide_if_pending(
            proposal_id,
            status="REJECTED",
            approved=False,
        )

        if not decided:
            self._repository.rollback()
            raise ValueError(
                "Execution proposal has already been decided."
            )

        self._repository.commit()

        updated = self._repository.get(proposal_id)

        if updated is None:
            raise ValueError(
                "Execution proposal was not found after rejection."
            )

        return updated

