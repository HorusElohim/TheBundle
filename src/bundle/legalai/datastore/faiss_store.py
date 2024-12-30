# legalai/datastore/faiss_store.py
import faiss
import numpy as np
from typing import List, Dict, Any

from .base import BaseVectorStore
from ..config import get_config
from ..model import UnifiedLanguageModel


class FaissVectorStore(BaseVectorStore):
    def __init__(self, model: UnifiedLanguageModel):
        print("[FaissVectorStore] Initializing...")
        self.index = None
        self.chunks: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.dim = None
        # Use UnifiedLanguageModel for all embedding logic
        super().__init__(model)

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        1) Chunk each document
        2) Encode chunk text with UnifiedLanguageModel.encode_texts(...)
        3) Normalize embeddings and add to Faiss index
        """
        chunked_data = []
        chunked_metas = []

        for text, meta in zip(texts, metadatas):
            ctext = BaseVectorStore.chunk_text(text, get_config().chunk_size, get_config().chunk_overlap)
            for c in ctext:
                chunked_data.append(c)
                chunked_metas.append(meta)

        # Encode to embeddings
        embs = self.model.encode_texts(chunked_data)

        # Normalize (for IP / cosine usage)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / (norms + 1e-12)

        # Initialize Faiss index if needed
        if self.index is None:
            self.dim = embs.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)

        # Add embeddings
        self.index.add(embs)

        # Store chunks & metadata
        self.chunks.extend(chunked_data)
        self.metadatas.extend(chunked_metas)
        print(f"[FaissVectorStore] Upserted {len(chunked_data)} chunks.")

    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Encode the query, then retrieve top_k from Faiss index.
        Return a list of {"text": ..., "metadata": ...} dicts.
        """
        if self.index is None or self.dim is None:
            return []

        query_emb = self.model.encode_texts([query])
        norms = np.linalg.norm(query_emb, axis=1, keepdims=True)
        query_emb = query_emb / (norms + 1e-12)

        _, I = self.index.search(query_emb, top_k)
        results = []
        for idx in I[0]:
            if idx < len(self.chunks):
                results.append({"text": self.chunks[idx], "metadata": self.metadatas[idx]})
        return results
