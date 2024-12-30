from pathlib import Path
from typing import cast

from bundle.core import data
from bundle.core.utils import ensure_path


class LegalAIConfig(data.Data):
    """
    Global configuration for LegalAI, utilizing TheBundle's Data class for validation and management.
    """

    # Base Model
    model_name: str = data.Field(default="mistralai/Mistral-7B-v0.3")
    embedding_model_name: str = data.Field(default="")  # This will be dynamically set to model_name

    # Vector Store Selection
    vector_store_type: str = data.Field(default="FAISS")

    # Pinecone
    pinecone_api_key: str = data.Field(default="YOUR-PINECONE-KEY")
    pinecone_env: str = data.Field(default="YOUR-PINECONE-ENV")
    pinecone_index_name: str = data.Field(default="legal-judgments-index")

    # Milvus
    milvus_host: str = data.Field(default="127.0.0.1")
    milvus_port: int = data.Field(default=19530)
    milvus_collection_name: str = data.Field(default="legal_judgments")
    milvus_dim: int = data.Field(default=768)

    # Chunking
    chunk_size: int = data.Field(default=300)
    chunk_overlap: int = data.Field(default=50)

    # Retrieval
    retrieval_top_k: int = data.Field(default=3)

    # Model/Training
    batch_size: int = data.Field(default=4)
    max_new_tokens: int = data.Field(default=128)

    # Weights & Biases
    wandb_project: str = data.Field(default="legalai-project")
    wandb_run: str = data.Field(default="default-run")

    @data.model_validator(mode="after")
    def sync_embedding_model_name(cls, instance):
        """
        Synchronize embedding_model_name with model_name after validation.
        """
        instance.embedding_model_name = instance.model_name
        return instance


DEFAULT_CONFIG_PATH = Path.home() / ".LegalAI" / "configuration-v0.1.json"
ensure_path(DEFAULT_CONFIG_PATH)

if DEFAULT_CONFIG_PATH.exists():
    CONFIG = LegalAIConfig.from_json(DEFAULT_CONFIG_PATH)
else:
    CONFIG = LegalAIConfig()


def get_config() -> LegalAIConfig:
    return cast(LegalAIConfig, CONFIG)
