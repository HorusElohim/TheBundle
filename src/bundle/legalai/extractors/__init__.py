from __future__ import annotations

from pathlib import Path

from .base import BaseDocumentExtractor
from ._csv import CSVDocumentExtractor
from ._json import JSONDocumentExtractor
from ._pdf import PDFDocumentExtractor
from ._text import TextDocumentExtractor
from ._document import Document


class DocumentExtractorFactory:

    @staticmethod
    def create(file_path: Path | None = None, chunk_size: int = 512, overlap: int = 50) -> BaseDocumentExtractor:
        """
        Factory method to create the appropriate extractor for a given file type.

        Args:
            file_path (Path): Path to the document.
            chunk_size (int): Size of each text chunk.
            overlap (int): Overlap between consecutive chunks.

        Returns:
            BaseDocumentExtractor: An instance of the appropriate extractor.
        """
        if file_path is None:
            return Document(chunk_size, overlap)

        file_ext = file_path.suffix.lower()
        match file_ext:
            case ".pdf":
                return PDFDocumentExtractor(file_path, chunk_size, overlap)
            case ".csv":
                return CSVDocumentExtractor(file_path, chunk_size, overlap)
            case ".json":
                return JSONDocumentExtractor(file_path, chunk_size, overlap)
            case ".txt" | "":
                return TextDocumentExtractor(file_path, chunk_size, overlap)
            case _:
                raise ValueError(f"Unsupported file extension: {file_ext}")
