"""Orchestration for owner-controlled Project action execution approval."""

from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.services.project_action_execution_approval import (
    ProjectActionExecutionApprovalService,
)


class ProjectActionExecutionApprovalOrchestrator:
    """Coordinate owner approval without executing the Project action."""

    def __init__(
        self,
        approval_service: ProjectActionExecutionApprovalService | None = None,
    ) -> None:
        self._approval_service = (
            approval_service
            or ProjectActionExecutionApprovalService()
        )

    def approve(
        self,
        proposal: ProjectActionExecutionProposal,
    ) -> ProjectActionExecutionProposal:
        return self._approval_service.approve(proposal)

    def reject(
        self,
        proposal: ProjectActionExecutionProposal,
    ) -> ProjectActionExecutionProposal:
        return self._approval_service.reject(proposal)