from collections.abc import Sequence

from app.intelligence.protocols import DomainStep

from app.intelligence.context import ExecutionContext


class Pipeline:
    """Executes an ordered sequence of domain steps."""

    def __init__(
        self,
        steps: Sequence[DomainStep],
    ) -> None:
        self._steps = tuple(steps)

    def run(
        self,
        context: ExecutionContext,
    ) -> None:
        """Execute every domain step in order."""

        for step in self._steps:
            step.execute(context)