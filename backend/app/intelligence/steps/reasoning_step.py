from app.intelligence.context import ExecutionContext
from app.intelligence.protocols import DomainStep

from app.schemas.memory import MemoryReference

from app.services.memory_resolver import MemoryResolver
from app.services.reasoning import ReasoningService


class ReasoningStep(DomainStep):
    """Creates reasoning analysis for the execution context."""

    def __init__(
        self,
        service: ReasoningService,
        memory_resolver: MemoryResolver | None = None,
    ) -> None:
        self._service = service
        self._memory_resolver = memory_resolver

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:

        memories = (
            self._memory_resolver.resolve(
                context.request.question,
            )
            if self._memory_resolver
            else ()
        )

        context.conversation.memories = [
            MemoryReference(
                memory_id=str(item.memory_id),
                version=item.version,
                key=item.key,
            )
            for item in memories
        ]

        context.intelligence.reasoning = self._service.plan(
            question=context.request.question,
            memories=memories,
            evidence=context.knowledge.context,
        )