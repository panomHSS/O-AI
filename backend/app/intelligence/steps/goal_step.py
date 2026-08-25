from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep

from app.services.goals import GoalService


class GoalStep(DomainStep):
    """Creates goal analysis from reasoning, planning and decision."""

    def __init__(
        self,
        service: GoalService,
    ) -> None:
        self._service = service

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:

        reasoning = context.intelligence.reasoning
        planning = context.intelligence.planning
        decision = context.intelligence.decision

        if (
            reasoning is None
            or planning is None
            or decision is None
        ):
            return

        context.intelligence.goals = self._service.analyze(
            reasoning,
            planning,
            decision,
        )