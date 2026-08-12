from typing import Any

from pydantic import BaseModel, Field


class ResponseContext(BaseModel):
    """Final response data for a single intelligence execution."""

    answer: str = ""
    citations: list[Any] = Field(default_factory=list)
    evidence_quality: str | None = None