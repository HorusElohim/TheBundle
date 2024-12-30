from .config import LegalAIConfig
from .datastore import BaseVectorStore, FaissVectorStore, MilvusVectorStore


def get_vector_store() -> BaseVectorStore:
    vtype = LegalAIConfig.VECTOR_STORE_TYPE
    if vtype == "MILVUS":
        return MilvusVectorStore()
    elif vtype == "FAISS":
        return FaissVectorStore()
    else:
        raise RuntimeError(f"The '{vtype}' is not supported as VectorStore")


def retrieve_documents(query: str, store: BaseVectorStore, top_k: int = LegalAIConfig.RETRIEVAL_TOP_K):
    return store.query(query, top_k)
