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
from app.services.project_action_execution_lookup import (
    ProjectActionExecutionLookupService,
)


class ProjectActionExecutor(Protocol):
    """Execute one already-claimed Project action proposal."""

    def execute(
        self,
        proposal: ProjectActionExecutionProposalRecord,
    ) -> None:
        ...


class ProjectActionCapabilityValidator(Protocol):
    """Validate whether a proposal uses supported execution capabilities."""

    def validate(
        self,
        proposal: ProjectActionExecutionProposalRecord,
    ) -> None:
        ...


class ProjectActionExecutionOrchestrator:
    """Coordinate validation, claim, execution, completion, and failure."""

    def __init__(
        self,
        *,
        claim_service: ProjectActionExecutionClaimService,
        completion_service: ProjectActionExecutionCompletionService,
        failure_service: ProjectActionExecutionFailureService,
        executor: ProjectActionExecutor,
        lookup_service: ProjectActionExecutionLookupService | None = None,
        capability_validator: ProjectActionCapabilityValidator | None = None,
        action_type_validator: ProjectActionActionTypeValidator | None = None,
    ) -> None:
        self._claim_service = claim_service
        self._completion_service = completion_service
        self._failure_service = failure_service
        self._executor = executor
        self._lookup_service = lookup_service
        self._capability_validator = capability_validator
        self._action_type_validator = action_type_validator

    def execute(
        self,
        proposal_id: str,
    ) -> ProjectActionExecutionProposalRecord:
        if self._capability_validator is not None:
            if self._lookup_service is None:
                raise ValueError(
                    "Capability validation requires proposal lookup."
                )

            proposal = self._lookup_service.get(
                proposal_id,
            )

            self._capability_validator.validate(
                proposal,
            )

        if self._action_type_validator is not None:
            if self._lookup_service is None:
                raise ValueError(
                    "Action type validation requires proposal lookup."
                )

            proposal = self._lookup_service.get(
                proposal_id,
            )

            self._action_type_validator.validate(
                proposal,
            )

        proposal = self._claim_service.claim(
            proposal_id,
        )

        try:
            self._executor.execute(
                proposal,
            )
        except Exception:
            self._failure_service.fail(
                proposal_id,
            )
            raise

        return self._completion_service.complete(
            proposal_id,
        )
    
class ProjectActionActionTypeValidator(Protocol):
    """Validate whether a proposal uses supported execution action types."""

    def validate(
        self,
        proposal: ProjectActionExecutionProposalRecord,
    ) -> None:
        ...