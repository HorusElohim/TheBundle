from pathlib import Path
from typing import Generator, Dict, Any
from .base import BaseDocumentExtractor


class Document(BaseDocumentExtractor):
    """Extractor for JSON files."""

    def __init__(self, chunk_size: int, overlap: int) -> None:
        super().__init__(Path().cwd(), chunk_size, overlap)

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        raise RuntimeError("No extraction is supported")
