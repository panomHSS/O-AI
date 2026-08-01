"""Safe, non-persistent Goal and Project explanatory metadata."""
from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.reasoning import ReasoningIntent

GoalState = Literal["candidate", "not_applicable"]

class Goal(BaseModel):
    """An explicit user-stated candidate, never a persisted or active goal."""
    id: str = Field(description="Stable deterministic candidate identifier.")
    title: str = Field(description="Normalized explicit user wording only.")

class Project(BaseModel):
    """An explicit user-stated candidate project, never a workflow or persisted project."""
    id: str = Field(description="Stable deterministic candidate identifier.")
    title: str = Field(description="Normalized explicit user wording only.")

class GoalAnalysis(BaseModel):
    """Deterministic explanatory metadata, not an action, commitment, schedule, or status change."""
    intent: ReasoningIntent
    goals: list[Goal] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    status: GoalState = Field(description="candidate means explicit text was recognized; no object was created.")
    missing_information: list[str] = Field(default_factory=list)
