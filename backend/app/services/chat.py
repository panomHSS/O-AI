from dataclasses import dataclass
from typing import Protocol, Sequence

from app.services.memory_resolver import MemoryContextBuilder, ResolvedMemory
from app.schemas.reasoning import ReasoningPlan
from app.services.reasoning import ReasoningContextBuilder
from app.schemas.planning import PlanningPlan
from app.services.planning import PlanningContextBuilder
from app.schemas.decision import DecisionAnalysis
from app.services.decision import DecisionContextBuilder


class ChatProvider(Protocol):
    """Provider contract that keeps transport code independent of an LLM vendor."""

    def generate_reply(self, message: str) -> str:
        """Return one reply for a user message."""


class ChatServiceError(Exception):
    """Base exception for safe chat-service failures."""


class ChatConfigurationError(ChatServiceError):
    """Raised when a configured chat provider cannot be used."""


class ChatProviderError(ChatServiceError):
    """Raised when a chat provider cannot complete a request safely."""


@dataclass(frozen=True)
class ChatContextMessage:
    role: str
    content: str


class ChatService:
    """Application service for chat interactions."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def send_message(self, message: str, recent_messages: Sequence[ChatContextMessage] = (), memories: Sequence[ResolvedMemory] = (), reasoning_plan: ReasoningPlan | None = None, planning_plan: PlanningPlan | None = None, decision_analysis: DecisionAnalysis | None = None) -> str:
        return self._provider.generate_reply(self._format_provider_input(message, recent_messages, memories, reasoning_plan, planning_plan, decision_analysis))

    @staticmethod
    def _format_provider_input(message: str, recent_messages: Sequence[ChatContextMessage], memories: Sequence[ResolvedMemory], reasoning_plan: ReasoningPlan | None = None, planning_plan: PlanningPlan | None = None, decision_analysis: DecisionAnalysis | None = None) -> str:
        blocks: list[str] = []
        if recent_messages:
            blocks.append("Conversation context:\n" + "\n".join(f"{item.role}: {item.content}" for item in recent_messages))
        if reasoning_plan:
            blocks.append(ReasoningContextBuilder.build(reasoning_plan))
        if planning_plan:
            blocks.append(PlanningContextBuilder.build(planning_plan))
        if decision_analysis:
            blocks.append(DecisionContextBuilder.build(decision_analysis))
        if memories:
            blocks.append(MemoryContextBuilder.build(memories))
        blocks.append(f"Current user message:\n{message}")
        return "\n\n".join(blocks)
