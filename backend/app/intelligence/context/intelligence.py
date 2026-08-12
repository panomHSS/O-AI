from pydantic import BaseModel

from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis
from app.schemas.planning import PlanningPlan
from app.schemas.reasoning import ReasoningPlan


class IntelligenceContext(BaseModel):
    """Intelligence analysis results for a single execution."""

    reasoning: ReasoningPlan | None = None
    planning: PlanningPlan | None = None
    decision: DecisionAnalysis | None = None
    goals: GoalAnalysis | None = None