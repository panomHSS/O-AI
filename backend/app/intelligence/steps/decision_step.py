from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep

from app.services.decision import DecisionService


class DecisionStep(DomainStep):
    """Creates decision analysis from reasoning and planning."""

    def __init__(
        self,
        service: DecisionService,
    ) -> None:
        self._service = service

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:

        reasoning = context.intelligence.reasoning
        planning = context.intelligence.planning

        if reasoning is None or planning is None:
            return

        context.intelligence.decision = self._service.analyze(
            reasoning,
            planning,
        )