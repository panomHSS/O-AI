from pydantic import BaseModel, Field

from app.services.knowledge_intelligence import (
    Conflict,
    Evidence,
    IntentAnalysis,
)

class KnowledgeContext(BaseModel):
    """Knowledge retrieval data for a single intelligence execution."""

    intent: IntentAnalysis | None = None
    queries: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    context: list[Evidence] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    records: list[dict[str, object]] = Field(
        default_factory=list,
    )
    duplicates_removed: int = 0
    filtered_out: int = 0