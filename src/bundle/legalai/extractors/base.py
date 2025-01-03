from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Dict, Any, List


class BaseDocumentExtractor(ABC):
    """
    Base class for document extraction. Defines a common interface for extracting
    text and metadata from various file types, with integrated text chunking.
    """

    def __init__(self, file_path: Path, chunk_size: int, overlap: int) -> None:
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.overlap = overlap

    @abstractmethod
    def extract(self) -> Generator[Dict[str, Any], None, None]:
        """
        Extract text and metadata from the document, with text chunking.

        Yields:
            dict: Contains 'text' (chunked) and 'meta' keys.
        """
        pass

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into smaller segments with overlap.

        Args:
            text (str): The text to be chunked.

        Returns:
            List[str]: A list of text chunks.
        """
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk = words[start:end]
            chunks.append(" ".join(chunk))
            start = end - self.overlap
            if start < 0:
                start = 0
        return chunks
