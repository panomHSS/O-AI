"""Execute Project action proposals through the typed dispatcher."""

from typing import Protocol

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)
from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionStepDispatcher(Protocol):
    """Dispatch one validated Project action execution step."""

    def dispatch(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        ...

class ProjectActionExecutionDispatchingExecutor:
    """Execute every proposal step through the typed dispatcher."""

    def __init__(
        self,
        *,
        dispatcher: ProjectActionStepDispatcher,
    ) -> None:
        self._dispatcher = dispatcher

    def execute(
        self,
        proposal: ProjectActionExecutionProposalRecord,
    ) -> None:
        for step in proposal.steps:
            context = ProjectActionExecutionContext(
                proposal_id=proposal.id,
                project_id=proposal.project_id,
                project_revision=proposal.project_revision,
                step=step,
            )
            
            self._dispatcher.dispatch(
                context,
            )