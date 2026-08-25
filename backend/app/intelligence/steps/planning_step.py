from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep

from app.services.planning import PlanningService


class PlanningStep(DomainStep):
    """Creates planning metadata from reasoning."""

    def __init__(
        self,
        service: PlanningService,
    ) -> None:
        self._service = service

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:

        reasoning = context.intelligence.reasoning

        if reasoning is None:
            return

        context.intelligence.planning = self._service.plan(
            reasoning,
        )