"""Orchestrate claimed Project action execution."""

from typing import Protocol

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.services.project_action_execution_claim import (
    ProjectActionExecutionClaimService,
)
from app.services.project_action_execution_completion import (
    ProjectActionExecutionCompletionService,
)
from app.services.project_action_execution_failure import (
    ProjectActionExecutionFailureService,
)


class ProjectActionExecutor(Protocol):
    """Execute one already-claimed Project action proposal."""

    def execute(
        self,
        proposal: ProjectActionExecutionProposalRecord,
    ) -> None:
        ...


class ProjectActionExecutionOrchestrator:
    """Coordinate claim, execution, completion, and failure boundaries."""

    def __init__(
        self,
        *,
        claim_service: ProjectActionExecutionClaimService,
        completion_service: ProjectActionExecutionCompletionService,
        failure_service: ProjectActionExecutionFailureService,
        executor: ProjectActionExecutor,
    ) -> None:
        self._claim_service = claim_service
        self._completion_service = completion_service
        self._failure_service = failure_service
        self._executor = executor

    def execute(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        proposal = self._claim_service.claim(
            proposal_id,
        )

        try:
            self._executor.execute(proposal)
        except Exception:
            self._failure_service.fail(
                proposal_id,
            )
            raise

        return self._completion_service.complete(
            proposal_id,
        )