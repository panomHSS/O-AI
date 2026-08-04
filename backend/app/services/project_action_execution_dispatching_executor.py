"""Execute Project action proposals through the typed dispatcher."""

from typing import Protocol

from app.models.project_action_execution_proposal import (
    ProjectActionExecutionProposalRecord,
)


class ProjectActionStepDispatcher(Protocol):
    """Dispatch one validated Project action execution step."""

    def dispatch(
        self,
        step: dict,
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
            self._dispatcher.dispatch(
                step,
            )