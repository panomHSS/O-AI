from pathlib import Path

from bs4 import BeautifulSoup

from app.readers.base import DocumentExtractionError, SourceSection


class HtmlDocumentReader:
    extensions = frozenset({".html", ".htm"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            markup = path.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(markup, "html.parser")
            for element in soup(["script", "style", "noscript"]):
                element.decompose()
            text = soup.get_text("\n", strip=True)
        except Exception as error:
            raise DocumentExtractionError("Unable to extract text from this HTML document.") from error

        if not text:
            raise DocumentExtractionError("This HTML document has no extractable text.")
        return [SourceSection(1, text, "HTML body")]
