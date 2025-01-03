# legalai/datastore/milvus_store.py
import asyncio
import numpy as np
from typing import List, Dict, Any
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
from pymilvus.milvus_client import IndexParams

from bundle.core import logger, data
from .base import BaseVectorStore
from ..config import get_config

log = logger.get_logger(__name__)


class QueryResult(data.Data):
    """
    A single query result with text and metadata.
    """

    id: int
    text: str
    metadata: Dict[str, Any]
    distance: float


class QueryResults(data.Data):
    """
    A list of query results.
    """

    results: List[QueryResult] = data.Field(default_factory=list)

    def get_text(self) -> list[str]:
        return [r.text for r in self.results]

    def __len__(self) -> int:
        return len(self.results)


class MilvusVectorStore(BaseVectorStore):
    """
    A local Milvus (Lite) vector store for embedding storage and retrieval.
    """

    def __init__(self):
        """
        Initialize local Milvus Lite DB and collection.
        No reference to any model inside this class.
        """
        super().__init__()

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
            # Make sure it’s loaded
            self.client.load_collection(self.collection_name)

    def _create_collection(self) -> None:
        """
        Create a collection schema and index, then load it.
        """
        fields = [
            FieldSchema("id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema("text", dtype=DataType.VARCHAR, max_length=512, is_primary=False, enable_analyzer=True),
        ]
        schema = CollectionSchema(
            fields=fields, description="A collection for storing embeddings and metadata.", enable_dynamic_field=True
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            consistency_level="Strong",
        )
        log.debug(f"Collection '{self.collection_name}' created with dimension={self.dim}.")

        index_params = IndexParams()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",  # or "HNSW", etc.
            index_name="my_vector_idx",
            metric_type="IP",  # must match usage
            params={"M": 8, "efConstruction": 64},
        )

        self.client.create_index(collection_name=self.collection_name, index_params=index_params)
        log.debug("Index created on field 'vector' with metric_type=IP.")
        self.client.load_collection(self.collection_name)

    def upsert(self, texts: List[str], embeddings: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        """
        Insert embeddings + text + metadata into the collection.
        """
        if embeddings.shape[0] != len(texts):
            log.error("Number of embeddings doesn't match number of texts.")
            return
        if embeddings.shape[0] != len(metadatas):
            log.error("Number of embeddings doesn't match number of metadata records.")
            return
        if embeddings.shape[1] != self.dim:
            log.error(f"Embedding dimension={embeddings.shape[1]} " f"mismatch collection dim={self.dim}. Skipping.")
            return

        data_to_insert = []
        for i, emb in enumerate(embeddings):
            # Convert the numpy vector to a standard list for insertion.
            record = {
                "vector": emb.tolist(),
                "text": texts[i],
                # Merge metadata dict into top-level fields:
                **metadatas[i],
            }
            data_to_insert.append(record)

        self.client.insert(collection_name=self.collection_name, data=data_to_insert)
        log.debug(f"Upserted {len(data_to_insert)} embeddings into '{self.collection_name}'.")

    def query(self, query_emb: np.ndarray, top_k: int) -> QueryResults:
        """
        Search the collection for the top-k closest embeddings to the given embedding.
        query_emb is expected to be shape [1, dim].
        """
        if query_emb.shape[1] != self.dim:
            log.error(f"Query embedding dimension={query_emb.shape[1]} " f"doesn't match collection dim={self.dim}.")
            return []

        search_params = {
            "metric_type": "IP",  # Must match the index's metric_type
            "params": {"nprobe": 10},
        }
        results = self.client.search(
            collection_name=self.collection_name,
            data=query_emb.tolist(),  # each vector is .tolist()
            limit=top_k,
            search_params=search_params,
            output_fields=["text"],
        )

        query_results = QueryResults()

        if not results or not results[0]:
            return query_results

        for match in results[0]:
            query_result = QueryResult(id=match["id"], distance=match["distance"], text=match["entity"]["text"], metadata={})
            query_results.results.append(query_result)

        log.debug("Search results: %s", asyncio.run(query_results.as_json()))
        return query_results
