from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class KnowledgeAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
class CitationResponse(BaseModel):
    id: str; document_id: UUID; file_name: str; source_path: str; source_locator: str; excerpt: str
class ConflictResponse(BaseModel):
    citations: list[str]; reason: str
class RetrievalSummaryResponse(BaseModel):
    candidates_considered: int; evidence_selected: int; duplicates_removed: int; filtered_out: int; conflicting_evidence_count: int; queries_used: list[str]
class KnowledgeAnswerResponse(BaseModel):
    answer: str; citations: list[CitationResponse]; evidence_quality: Literal["high", "medium", "low", "insufficient"]; conversation_id: UUID; retrieval_summary: RetrievalSummaryResponse; conflicts: list[ConflictResponse]
