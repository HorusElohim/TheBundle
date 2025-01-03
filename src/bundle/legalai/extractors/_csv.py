import csv
from pathlib import Path
from typing import Generator, Dict, Any
from .base import BaseDocumentExtractor


class CSVDocumentExtractor(BaseDocumentExtractor):
    """Extractor for CSV files."""

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        with self.file_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                text = " ".join(row).strip()
                chunks = self.chunk_text(text)
                for chunk in chunks:
                    yield {"text": chunk, "meta": {"doc_id": f"{self.file_path.stem}-{i}"}}
