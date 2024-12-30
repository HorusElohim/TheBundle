import numpy as np
from typing import List, Dict, Any
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
from tqdm import tqdm

from bundle.core import logger
from .base import BaseVectorStore
from ..config import get_config
from ..model import UnifiedLanguageModel

log = logger.get_logger(__name__)


class MilvusVectorStore(BaseVectorStore):
    """
    A local Milvus Lite-based vector store for embedding storage and retrieval.
    """

    def __init__(self, model: UnifiedLanguageModel):
        """
        Initialize local Milvus Lite DB and collection.
        """
        self.model = model
        # The local DB file name
        milvus_db_file = f"{get_config().milvus_collection_name}.db"
        log.debug(f"Using Milvus Lite with local file: {milvus_db_file}")

        # Create local MilvusClient
        self.client = MilvusClient(milvus_db_file)

        # Collection name + dimension from config
        self.collection_name = get_config().milvus_collection_name
        self.dim = get_config().milvus_dim

        # Check if collection exists, else create it
        if not self.client.has_collection(self.collection_name):
            log.debug(f"Creating local collection '{self.collection_name}' with dimension={self.dim}.")
            self._create_collection()
        else:
            log.debug(f"Collection '{self.collection_name}' already exists.")

    def _create_collection(self):
        """
        Create a collection schema and initialize it.
        """
        fields = [
            FieldSchema("id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("vector", DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema("text", dtype=DataType.VARCHAR, is_primary=False, max_length=512, enable_analyzer=True),
        ]
        schema = CollectionSchema(fields=fields, description="Test book search", enable_dynamic_field=True)
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            description="A collection for storing embeddings and metadata.",
            metric_type="IP",
            consitency_level="strong",
        )
        log.debug(f"Collection '{self.collection_name}' created with dimension={self.dim}.")

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Embed texts and insert them into the collection.
        """
        total_chunks = 0

        texts = texts[:1]

        for i in tqdm(range(len(texts)), desc="Upserting docs"):
            text = texts[i]
            meta = metadatas[i]

            # 1) Chunk text
            ctext = BaseVectorStore.chunk_text(text, get_config().chunk_size, get_config().chunk_overlap)

            ctext = ctext[:1]

            # 2) Encode text chunks
            embs = self.model.encode_texts(ctext).astype(np.float32)

            if embs.shape[1] != self.dim:
                log.error(f"Embedding dimension={embs.shape[1]} mismatch collection dim={self.dim}. Skipping.")
                continue

            # 3) Prepare records for insertion
            data_to_insert = [{"id": (i * 1000) + j, "vector": emb, "text": ctext[j]} for j, emb in enumerate(embs)]

            # Insert into the collection
            self.client.insert(collection_name=self.collection_name, data=data_to_insert)
            total_chunks += len(data_to_insert)

        log.debug(f"Upserted {total_chunks} embeddings into '{self.collection_name}'.")

    def query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Search the collection for the top-k closest embeddings to the query.
        """
        # 1) Encode the query
        log.debug(f"Query: {query}")

        query_emb = self.model.encode_texts([query]).astype(np.float32)

        log.debug(f"Query embedding shape: {query_emb.shape}")

        if query_emb.shape[1] != self.dim:
            log.error(f"Query embedding dimension={query_emb.shape[1]} doesn't match collection dim={self.dim}.")
            return []

        # Search with limit
        results = self.client.search(
            collection_name=self.collection_name,
            data=query_emb.tolist(),
            limit=top_k,
            search_params={"metric_type": "IP", "params": {}},
            # search_params=search_params
        )
        log.debug(f"Search results: {results}")
        # 3) Parse results
        # matches = [{"id": match.id, "score": match.distance, "text": match.entity.get("text")} for match in results[0]]
        return results
