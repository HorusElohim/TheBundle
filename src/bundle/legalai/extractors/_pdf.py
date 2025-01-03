from pathlib import Path

from typing import Generator, Dict, Any
from PyPDF2 import PdfReader
from .base import BaseDocumentExtractor


class PDFDocumentExtractor(BaseDocumentExtractor):
    """Extractor for PDF files."""

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        reader = PdfReader(self.file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            chunks = self.chunk_text(text)
            for chunk in chunks:
                yield {"text": chunk, "meta": {"doc_id": f"{self.file_path.stem}-page-{i}"}}
