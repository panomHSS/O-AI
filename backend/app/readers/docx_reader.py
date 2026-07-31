from pathlib import Path

from docx import Document as DocxFile

from app.readers.base import DocumentExtractionError, SourceSection


class DocxDocumentReader:
    extensions = frozenset({".docx"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            document = DocxFile(path)
            sections = [
                SourceSection(sequence=index, text=text, source_locator=f"Word paragraph {index}")
                for index, paragraph in enumerate(document.paragraphs, start=1)
                if (text := paragraph.text.strip())
            ]
        except Exception as error:
            raise DocumentExtractionError("Unable to extract text from this Word document.") from error

        if not sections:
            raise DocumentExtractionError("This Word document has no extractable text.")
        return sections
