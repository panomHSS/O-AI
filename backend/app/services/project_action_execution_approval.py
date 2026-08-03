"""Owner-controlled approval for Project action execution proposals."""

from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)


class ProjectActionExecutionApprovalService:
    """Approve or reject a proposal without executing its action."""

    def approve(
        self,
        proposal: ProjectActionExecutionProposal,
    ) -> ProjectActionExecutionProposal:
        if (
            proposal.status != "awaiting_owner_approval"
            or not proposal.owner_approval_required
        ):
            raise ValueError(
                "Execution proposal is not eligible for owner approval."
            )

        return proposal.model_copy(
            update={
                "status": "approved",
                "approved": True,
                "executed": False,
            }
        )

    def reject(
        self,
        proposal: ProjectActionExecutionProposal,
    ) -> ProjectActionExecutionProposal:
        if (
            proposal.status != "awaiting_owner_approval"
            or not proposal.owner_approval_required
        ):
            raise ValueError(
                "Execution proposal is not eligible for owner approval."
            )

        return proposal.model_copy(
            update={
                "status": "rejected",
                "approved": False,
                "executed": False,
            }
        )