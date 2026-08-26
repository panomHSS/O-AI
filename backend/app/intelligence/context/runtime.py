from typing import Any

from pydantic import BaseModel, Field


class RuntimeContext(BaseModel):
    """Transient runtime state during a single intelligence execution."""

    answer: str = ""

    validated_citations: list[Any] = Field(
        default_factory=list,
    )

    evidence_quality: str | None = None

    citation_snapshots: list[Any] = Field(
        default_factory=list,
    )