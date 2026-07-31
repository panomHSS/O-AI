from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup

from app.readers.base import DocumentExtractionError, SourceSection


class EmlDocumentReader:
    extensions = frozenset({".eml"})

    def extract(self, path: Path) -> list[SourceSection]:
        try:
            with path.open("rb") as source:
                message = BytesParser(policy=policy.default).parse(source)
            headers = [f"{name}: {message.get(name)}" for name in ("From", "To", "Subject", "Date") if message.get(name)]
            sections = [SourceSection(1, "\n".join(headers), "Email headers")] if headers else []
            sequence = len(sections) + 1
            for part in message.walk():
                if part.is_multipart() or part.get_content_disposition() == "attachment":
                    continue
                content_type = part.get_content_type()
                if content_type not in {"text/plain", "text/html"}:
                    continue
                value = part.get_content()
                text = BeautifulSoup(value, "html.parser").get_text("\n", strip=True) if content_type == "text/html" else str(value).strip()
                if text:
                    locator = "Email HTML body" if content_type == "text/html" else "Email plain-text body"
                    sections.append(SourceSection(sequence, text, locator))
                    sequence += 1
        except Exception as error:
            raise DocumentExtractionError("Unable to extract text from this email message.") from error

        if not sections:
            raise DocumentExtractionError("This email message has no indexable headers or body text.")
        return sections
