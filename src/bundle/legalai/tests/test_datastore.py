import numpy as np

from bundle.legalai.datastore import MilvusVectorStore


def test_upsert_and_query_milvus_store():
    # Initialize store (no model reference)
    store = MilvusVectorStore()

    # Prepare test data
    texts = ["Hello world!", "Goodbye world!"]
    dim = store.dim  # As retrieved from config
    embeddings = np.random.rand(len(texts), dim).astype(np.float32)
    metadatas = [
        {"doc_id": 1, "category": "greeting"},
        {"doc_id": 2, "category": "farewell"},
    ]

    # 1) Upsert the data
    store.upsert(texts, embeddings, metadatas)

    # 2) Query using the embedding of the first text
    query_emb = embeddings[0].reshape(1, -1)  # shape [1, dim]
    results = store.query(query_emb=query_emb, top_k=2)

    # 3) Check we got something back
    assert len(results) > 0, "No results returned from Milvus query!"

    # Optionally, do further checks
    # For example, make sure that at least the top match is for "Hello world!"
    # (although random embeddings won't necessarily produce a meaningful result).
