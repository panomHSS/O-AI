from pathlib import Path

from app.readers.base import DocumentExtractionError, SourceSection


class TextDocumentReader:
    extensions = frozenset({".txt", ".md"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            raise DocumentExtractionError("Unable to read this text document.") from error

        if not text.strip():
            raise DocumentExtractionError("This text document is empty.")
        return [SourceSection(1, text, f"Text lines 1-{max(1, text.count(chr(10)) + 1)}")]
