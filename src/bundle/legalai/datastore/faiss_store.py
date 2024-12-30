import faiss
import numpy as np
from typing import List, Dict, Any
from .base import BaseVectorStore
from ..embeddings import LlamaEmbeddingWrapper
from ..config import LegalAIConfig


class FaissVectorStore(BaseVectorStore):
    def __init__(self):
        print("[FaissVectorStore] Initializing...")
        self.embedding_model = LlamaEmbeddingWrapper()
        self.index = None
        self.chunks: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.dim = None

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        chunked_data = []
        chunked_metas = []

        for text, meta in zip(texts, metadatas):
            ctext = BaseVectorStore.chunk_text(text, LegalAIConfig.CHUNK_SIZE, LegalAIConfig.CHUNK_OVERLAP)
            for c in ctext:
                chunked_data.append(c)
                chunked_metas.append(meta)

        embs = self.embedding_model.encode_texts(chunked_data)
        # Normalize
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / (norms + 1e-12)

        if self.index is None:
            self.dim = embs.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(embs)

        self.chunks.extend(chunked_data)
        self.metadatas.extend(chunked_metas)
        print(f"[FaissVectorStore] Upserted {len(chunked_data)} chunks.")

    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        if self.index is None or self.dim is None:
            return []

        query_emb = self.embedding_model.encode_texts([query])
        norms = np.linalg.norm(query_emb, axis=1, keepdims=True)
        query_emb = query_emb / (norms + 1e-12)

        D, I = self.index.search(query_emb, top_k)
        results = []
        for idx in I[0]:
            if idx < len(self.chunks):
                results.append({"text": self.chunks[idx], "metadata": self.metadatas[idx]})
        return results
