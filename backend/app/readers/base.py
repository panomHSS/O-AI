from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class DocumentExtractionError(Exception):
    """Raised when a supported document cannot yield safe text."""


@dataclass(frozen=True)
class SourceSection:
    """Ordered extracted text with a human-useful citation location."""

    sequence: int
    text: str
    source_locator: str
    metadata: dict[str, str] = field(default_factory=dict)


class DocumentReader(Protocol):
    extensions: frozenset[str]

    def extract(self, path: Path) -> list[SourceSection]:
        """Extract source sections without database or HTTP concerns."""
