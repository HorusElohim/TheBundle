# legalai/datastore/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import numpy as np


class BaseVectorStore(ABC):
    def __init__(self) -> None:
        """No reference to a model here anymore."""
        super().__init__()

    @abstractmethod
    def upsert(self, texts: List[str], embeddings: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        """
        Upsert documents by providing the raw texts, their pre-encoded vectors,
        and additional metadata. The store can index them appropriately.
        """
        pass

    @abstractmethod
    def query(self, query_emb: np.ndarray, top_k: int) -> List[Dict[str, Any]]:
        """
        Query the store by providing a single pre-encoded query vector
        (of shape [1, dim]) and a desired top_k number of matches.
        Return a list of results with their metadata.
        """
        pass

    @staticmethod
    def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        (Optional) Still keep this helper here if you find it useful for
        external code. But it no longer integrates with the upsert flow
        by default since embeddings must already be provided.
        """
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
