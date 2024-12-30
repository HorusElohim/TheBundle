# legalai/datastore/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        pass

    @staticmethod
    def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = words[start:end]
            chunks.append(" ".join(chunk))
            start = end - overlap
            if start < 0:
                start = 0
        return chunks
