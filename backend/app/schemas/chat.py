from uuid import UUID

from pydantic import BaseModel, Field
from app.schemas.reasoning import ReasoningPlan
from app.schemas.planning import PlanningPlan
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis


class ChatRequest(BaseModel):
    """Validated input for a chat turn."""

    message: str = Field(min_length=1, max_length=4_000)
    conversation_id: UUID | None = None
    project_id: UUID | None = None


class ChatResponse(BaseModel):
    """Stable response contract for a chat turn."""

    reply: str
    conversation_id: UUID
    memories_used: list["MemoryUsageResponse"] = Field(default_factory=list)
    reasoning_plan: ReasoningPlan | None = None
    planning_plan: PlanningPlan | None = None
    decision_analysis: DecisionAnalysis | None = None
    goal_analysis: GoalAnalysis | None = None


class MemoryUsageResponse(BaseModel):
    memory_id: UUID
    version: int
    key: str
