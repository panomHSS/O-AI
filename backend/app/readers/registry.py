from pathlib import Path

from app.readers.base import DocumentReader


class DocumentReaderRegistry:
    def __init__(self, readers: list[DocumentReader]) -> None:
        self._readers = {extension: reader for reader in readers for extension in reader.extensions}

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset(self._readers)

    def get(self, path: Path) -> DocumentReader | None:
        return self._readers.get(path.suffix.lower())
