import csv
from pathlib import Path

from app.readers.base import DocumentExtractionError, SourceSection


class CsvDocumentReader:
    extensions = frozenset({".csv"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
                rows = list(csv.reader(source))
            sections = [
                SourceSection(sequence=index, text=" | ".join(cell.strip() for cell in row), source_locator=f"CSV rows {index}-{index}", metadata={"atomic": "true"})
                for index, row in enumerate(rows, start=1)
                if any(cell.strip() for cell in row)
            ]
        except Exception as error:
            raise DocumentExtractionError("Unable to extract text from this CSV file.") from error

        if not sections:
            raise DocumentExtractionError("This CSV file has no extractable text.")
        return sections
