# legalai/datastore/milvus_store.py
import numpy as np
from typing import List, Dict, Any

from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

from .base import BaseVectorStore
from ..config import get_config
from ..model import UnifiedLanguageModel


class MilvusVectorStore(BaseVectorStore):
    """
    A self-hosted Milvus-based vector store, now using UnifiedLanguageModel for embeddings.
    Expects a running Milvus server at config milvus_host:milvus_port.
    """

    def __init__(self, model: UnifiedLanguageModel):
        print("[MilvusVectorStore] Initializing connection...")

        self.collection_name = get_config().milvus_collection_name
        self.dim = get_config().milvus_dim

        # 1) Connect to Milvus
        connections.connect(alias="default", host=get_config().milvus_host, port=str(get_config().milvus_port))

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
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 1024},
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)
        else:
            print(f"[MilvusVectorStore] Loading existing collection {self.collection_name}...")
            self.collection = Collection(self.collection_name)

        # 3) Load collection
        self.collection.load()

        # Use UnifiedLanguageModel for all embedding logic
        super().__init__(model)

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        1) Chunk docs
        2) Encode them with self.model.encode_texts(...)
        3) Insert embeddings into Milvus
        """
        total_chunks = 0
        for text, meta in zip(texts, metadatas):
            ctext = BaseVectorStore.chunk_text(text, get_config().chunk_size, get_config().chunk_overlap)
            embs = self.model.encode_texts(ctext)

            # Normalize
            norms = np.linalg.norm(embs, axis=1, keepdims=True)
            embs = embs / (norms + 1e-12)

            # Insert in Milvus
            # Each row is a float vector
            self.collection.insert([[emb.tolist() for emb in embs]], fields=["embedding"])
            total_chunks += embs.shape[0]

        self.collection.load()
        print(f"[MilvusVectorStore] Upserted {total_chunks} total chunks into collection '{self.collection_name}'.")

    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Encode query using self.model and do a vector search in Milvus.
        Return a list of relevant hits with optional metadata/distance.
        """
        query_emb = self.model.encode_texts([query])
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
            output_fields=["id"],
        )

        # results is a list of hits for each query (we have only 1 query)
        matches_list = results[0]

        matches = []
        for hit in matches_list:
            matches.append(
                {
                    "metadata": {"milvus_id": hit.id},
                    "score": hit.distance,
                }
            )
        return matches
