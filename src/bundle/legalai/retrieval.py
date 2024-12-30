from .config import get_config
from .datastore import BaseVectorStore, FaissVectorStore, MilvusVectorStore
from .model import UnifiedLanguageModel


def get_vector_store(model: UnifiedLanguageModel) -> BaseVectorStore:
    vtype = get_config().vector_store_type
    if vtype == "MILVUS":
        return MilvusVectorStore(model)
    elif vtype == "FAISS":
        return FaissVectorStore(model)
    else:
        raise RuntimeError(f"The '{vtype}' is not supported as VectorStore")


def retrieve_documents(query: str, store: BaseVectorStore, top_k: int = get_config().retrieval_top_k):
    return store.query(query, top_k)
