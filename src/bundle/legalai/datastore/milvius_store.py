import numpy as np
from typing import List, Dict, Any
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
from pymilvus.milvus_client import IndexParams

from bundle.core import logger
from .base import BaseVectorStore
from ..config import get_config
from ..model import UnifiedLanguageModel

log = logger.get_logger(__name__)


class MilvusVectorStore(BaseVectorStore):
    """
    A local Milvus (Lite) vector store for embedding storage and retrieval.
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
            # Make sure it’s loaded
            self.client.load_collection(self.collection_name)

    def _create_collection(self) -> None:
        """
        Create a collection schema and index, then load it.
        """
        # 1) Create collection schema
        fields = [
            FieldSchema("id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema("text", dtype=DataType.VARCHAR, max_length=512, is_primary=False, enable_analyzer=True),
        ]
        schema = CollectionSchema(
            fields=fields, description="A collection for storing embeddings and metadata.", enable_dynamic_field=True
        )

        # 2) Create the collection (schema only).
        #    Do NOT confuse metric_type here with the index's metric.
        #    Some Milvus versions do allow metric_type in create_collection,
        #    but it's safer & more flexible to do it in create_index.
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            consistency_level="Strong",  # correct spelling
        )
        log.debug(f"Collection '{self.collection_name}' created with dimension={self.dim}.")

        # 2) Build IndexParams object
        index_params = IndexParams()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",        # or "HNSW", etc.
            index_name="my_vector_idx",  # any name you like
            metric_type="IP",            # must match usage
            params={"nlist": 64}
        )

        self.client.create_index(collection_name=self.collection_name, field_name="vector", index_params=index_params)
        log.debug("Index created on field 'vector' with metric_type=IP.")

        # 4) Load the collection before inserting or searching
        self.client.load_collection(self.collection_name)

    def upsert(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Embed texts and insert them into the collection.
        """
        total_chunks = 0

        # Example snippet to limit inserts for debugging
        # Remove as needed.
        texts = texts[:1]

        for i in range(len(texts)):
            text = texts[i]
            meta = metadatas[i]

            # 1) Chunk text
            ctext = BaseVectorStore.chunk_text(text, get_config().chunk_size, get_config().chunk_overlap)
            ctext = ctext[:1]  # debugging limit

            # 2) Encode text chunks
            embs = self.model.encode_texts(ctext).astype(np.float32)

            if embs.shape[1] != self.dim:
                log.error(f"Embedding dimension={embs.shape[1]} mismatch " f"collection dim={self.dim}. Skipping.")
                continue

            # 3) Prepare records for insertion
            data_to_insert = []
            for j, emb in enumerate(embs):
                data_to_insert.append(
                    {
                        "vector": emb.tolist(),
                        "text": ctext[j],
                    }
                )

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
            log.error(f"Query embedding dimension={query_emb.shape[1]} " f"doesn't match collection dim={self.dim}.")
            return []

        # 2) Search
        search_params = {
            "metric_type": "IP",  # Must match the index's metric_type
            "params": {"nprobe": 10},
        }
        results = self.client.search(
            collection_name=self.collection_name,
            data=query_emb.tolist(),  # each vector is .tolist()
            limit=top_k,
            search_params=search_params,
        )
        log.debug(f"Search results: {results}")

        # 3) Parse results
        if not results or not results[0]:
            return []

        matches = []
        for match in results[0]:
            matches.append(
                {
                    "id": match.id,
                    "score": match.distance,
                    "text": match.entity.get("text", None),
                }
            )
        return matches
