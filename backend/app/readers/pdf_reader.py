from pathlib import Path

from pypdf import PdfReader

from app.readers.base import DocumentExtractionError, SourceSection


class PdfDocumentReader:
    extensions = frozenset({".pdf"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            reader = PdfReader(path)
            sections = [
                SourceSection(sequence=index, text=text, source_locator=f"PDF page {index}")
                for index, page in enumerate(reader.pages, start=1)
                if (text := (page.extract_text() or "").strip())
            ]
        except Exception as error:
            raise DocumentExtractionError("Unable to extract text from this PDF.") from error

        if not sections:
            raise DocumentExtractionError("This PDF has no extractable text. OCR is planned for Release 0.6.1.")
        return sections
