from dataclasses import dataclass
from typing import Sequence

from app.providers.base import (
    ChatConfigurationError,
    ChatProvider,
    ChatProviderError,
    ChatServiceError,
)
from app.contracts.ai import AIAdapter, AIRequest

from app.services.memory_resolver import MemoryContextBuilder, ResolvedMemory
from app.schemas.reasoning import ReasoningPlan
from app.services.reasoning import ReasoningContextBuilder
from app.schemas.planning import PlanningPlan
from app.services.planning import PlanningContextBuilder
from app.schemas.decision import DecisionAnalysis
from app.services.decision import DecisionContextBuilder
from app.schemas.goals import GoalAnalysis
from app.services.goals import GoalContextBuilder
from app.services.project_context import ProjectContext, ProjectContextBuilder


@dataclass(frozen=True)
class ChatContextMessage:
    role: str
    content: str


class ChatService:
    """Application service for chat interactions."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def default_ai_adapter(self) -> AIAdapter:
        """Expose the configured legacy provider through AI Adapter v1."""
        if isinstance(self._provider, AIAdapter):
            return self._provider
        from app.adapters.chatgpt import ChatGPTAdapter

        return ChatGPTAdapter(self._provider)

    def send_message(self, message: str, recent_messages: Sequence[ChatContextMessage] = (), memories: Sequence[ResolvedMemory] = (), reasoning_plan: ReasoningPlan | None = None, planning_plan: PlanningPlan | None = None, decision_analysis: DecisionAnalysis | None = None, goal_analysis: GoalAnalysis | None = None, project_context: ProjectContext | None = None, ai_adapter: AIAdapter | None = None) -> str:
        formatted = self._format_provider_input(message, recent_messages, memories, reasoning_plan, planning_plan, decision_analysis, goal_analysis, project_context)
        if ai_adapter is not None:
            return ai_adapter.generate(AIRequest(content=formatted)).content
        return self._provider.generate_reply(formatted)

    @staticmethod
    def _format_provider_input(message: str, recent_messages: Sequence[ChatContextMessage], memories: Sequence[ResolvedMemory], reasoning_plan: ReasoningPlan | None = None, planning_plan: PlanningPlan | None = None, decision_analysis: DecisionAnalysis | None = None, goal_analysis: GoalAnalysis | None = None, project_context: ProjectContext | None = None) -> str:
        blocks: list[str] = []
        if recent_messages:
            blocks.append("Conversation context:\n" + "\n".join(f"{item.role}: {item.content}" for item in recent_messages))
        if reasoning_plan:
            blocks.append(ReasoningContextBuilder.build(reasoning_plan))
        if planning_plan:
            blocks.append(PlanningContextBuilder.build(planning_plan))
        if decision_analysis:
            blocks.append(DecisionContextBuilder.build(decision_analysis))
        if goal_analysis:
            blocks.append(GoalContextBuilder.build(goal_analysis))
        if project_context:
            blocks.append(ProjectContextBuilder.build(project_context))
        if memories:
            blocks.append(MemoryContextBuilder.build(memories))
        blocks.append(f"Current user message:\n{message}")
        return "\n\n".join(blocks)
