from pathlib import Path
from typing import Generator, Dict, Any
from .base import BaseDocumentExtractor


class TextDocumentExtractor(BaseDocumentExtractor):
    """Extractor for plain text files."""

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        with self.file_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                text = line.strip()
                chunks = self.chunk_text(text)
                for chunk in chunks:
                    yield {"text": chunk, "meta": {"doc_id": f"{self.file_path.stem}-{i}"}}
