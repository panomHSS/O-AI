from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from app.schemas.reasoning import ReasoningPlan
from app.schemas.planning import PlanningPlan
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis
from app.schemas.project_update_proposals import ProjectUpdateProposalResponse
from app.schemas.project_actions import ProjectActionAnalysis
from app.schemas.project_action_planning import ProjectActionPlan
from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.schemas.execution_approvals import (
    ExecutionApprovalProposalResponse,
)


class ChatRequest(BaseModel):
    """Validated input for a chat turn."""

    message: str = Field(min_length=1, max_length=4_000)
    conversation_id: UUID | None = None
    project_id: UUID | None = None


class ChatActionResponse(BaseModel):
    """Ephemeral D46 owner-review state returned by an action chat turn."""

    status: Literal[
        "pending_approval",
        "rejected",
        "unavailable",
    ]
    reason_code: str
    approval: ExecutionApprovalProposalResponse | None = None


class ChatResponse(BaseModel):
    """Stable response contract for a chat turn."""

    reply: str
    conversation_id: UUID
    action: ChatActionResponse | None = None
    project_update_proposal: ProjectUpdateProposalResponse | None = None
    project_action_analysis: ProjectActionAnalysis | None = None
    memories_used: list["MemoryUsageResponse"] = Field(default_factory=list)
    reasoning_plan: ReasoningPlan | None = None
    planning_plan: PlanningPlan | None = None
    decision_analysis: DecisionAnalysis | None = None
    goal_analysis: GoalAnalysis | None = None
    project_action_plan: ProjectActionPlan | None = None
    project_action_execution_proposal: ProjectActionExecutionProposal | None = None


class MemoryUsageResponse(BaseModel):
    memory_id: UUID
    version: int
    key: str
