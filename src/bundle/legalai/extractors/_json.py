import json

from typing import Generator, Dict, Any
from .base import BaseDocumentExtractor


class JSONDocumentExtractor(BaseDocumentExtractor):
    """Extractor for JSON files."""

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        with self.file_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                text = data.get("text", "")
                chunks = self.chunk_text(text)
                for chunk in chunks:
                    yield {"text": chunk, "meta": {"doc_id": f"{self.file_path.stem}-{i}"}}
