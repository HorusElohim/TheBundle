# legalai/datastore/milvus_store.py
import numpy as np
from typing import List, Dict, Any

from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

from .base import BaseVectorStore
from ..embeddings import LlamaEmbeddingWrapper
from ..config import LegalAIConfig


class MilvusVectorStore(BaseVectorStore):
    """
    A self-hosted Milvus-based vector store.
    Expects a Milvus server running at config MILVUS_HOST:MILVUS_PORT.
    """

    def __init__(self):
        print("[MilvusVectorStore] Initializing connection...")
        self.embedding_model = LlamaEmbeddingWrapper()
        self.collection_name = LegalAIConfig.MILVUS_COLLECTION_NAME
        self.dim = LegalAIConfig.MILVUS_DIM

        # 1) Connect
        connections.connect(alias="default", host=LegalAIConfig.MILVUS_HOST, port=LegalAIConfig.MILVUS_PORT)

        # 2) Create or load existing collection
        if not utility.has_collection(self.collection_name):
            print(f"[MilvusVectorStore] Creating collection {self.collection_name}...")
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            ]
            schema = CollectionSchema(fields, description="LegalAI collection schema.")
            self.collection = Collection(name=self.collection_name, schema=schema)
            # Create index
            index_params = {"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 1024}}
            self.collection.create_index(field_name="embedding", index_params=index_params)
        else:
            print(f"[MilvusVectorStore] Loading existing collection {self.collection_name}...")
            self.collection = Collection(self.collection_name)

        # 3) Load collection to memory
        self.collection.load()

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        # We’ll store embeddings, but we also want to keep the chunk text or doc_id somewhere.
        # For a more advanced schema, add additional fields.
        # For demonstration, we only store 'embedding' in Milvus.

        total_chunks = 0
        for text, meta in zip(texts, metadatas):
            ctext = BaseVectorStore.chunk_text(text, LegalAIConfig.CHUNK_SIZE, LegalAIConfig.CHUNK_OVERLAP)
            embs = self.embedding_model.encode_texts(ctext)
            # Normalize
            norms = np.linalg.norm(embs, axis=1, keepdims=True)
            embs = embs / (norms + 1e-12)

            n = embs.shape[0]
            # Insert in batches
            self.collection.insert([[emb.tolist() for emb in embs]], fields=["embedding"])  # shape: (n, 768)
            total_chunks += n

        self.collection.load()
        print(f"[MilvusVectorStore] Upserted {total_chunks} total chunks into collection '{self.collection_name}'.")

    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        query_emb = self.embedding_model.encode_texts([query])
        # Normalize
        norms = np.linalg.norm(query_emb, axis=1, keepdims=True)
        query_emb = query_emb / (norms + 1e-12)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10},
        }

        results = self.collection.search(
            data=[query_emb[0].tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["id"],  # or any other fields you've added
        )

        # results is a list of the queries, each query is a list of hits
        matches_list = results[0]

        matches = []
        for hit in matches_list:
            # For advanced usage, we’d store doc_id or chunk text in separate fields
            # or in a parallel DB. For now, just storing the milvus ID & distance.
            matches.append(
                {
                    "metadata": {"milvus_id": hit.id},
                    "score": hit.distance,
                }
            )
        return matches
