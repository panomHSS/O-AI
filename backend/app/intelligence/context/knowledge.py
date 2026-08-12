from pydantic import BaseModel, Field

from app.services.knowledge_intelligence import (
    Conflict,
    Evidence,
)


class KnowledgeContext(BaseModel):
    """Knowledge retrieval data for a single intelligence execution."""

    queries: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)