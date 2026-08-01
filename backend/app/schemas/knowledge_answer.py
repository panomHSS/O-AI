from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.chat import MemoryUsageResponse
from app.schemas.reasoning import ReasoningPlan
from app.schemas.planning import PlanningPlan
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis

class KnowledgeAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    project_id: UUID | None = None
class CitationResponse(BaseModel):
    id: str; document_id: UUID; file_name: str; source_path: str; source_locator: str; excerpt: str
class ConflictResponse(BaseModel):
    citations: list[str]; reason: str
class RetrievalSummaryResponse(BaseModel):
    candidates_considered: int; evidence_selected: int; duplicates_removed: int; filtered_out: int; conflicting_evidence_count: int; queries_used: list[str]
class KnowledgeAnswerResponse(BaseModel):
    answer: str; citations: list[CitationResponse]; evidence_quality: Literal["high", "medium", "low", "insufficient"]; conversation_id: UUID; retrieval_summary: RetrievalSummaryResponse; conflicts: list[ConflictResponse]; memories_used: list[MemoryUsageResponse] = Field(default_factory=list); reasoning_plan: ReasoningPlan; planning_plan: PlanningPlan; decision_analysis: DecisionAnalysis | None = None; goal_analysis: GoalAnalysis | None = None
