import os


class LegalAIConfig:
    """
    Global configuration for LegalAI, controlled by environment variables.
    """

    # Base Model
    MODEL_NAME = os.getenv("LEGALAI_MODEL_NAME", "mistralai/Mistral-7B-v0.3")
    EMBEDDING_MODEL_NAME = os.getenv("LEGALAI_EMBEDDING_MODEL_NAME", MODEL_NAME)

    # Vector Store Selection
    #   'FAISS', 'PINECONE', or 'MILVUS'
    VECTOR_STORE_TYPE = os.getenv("LEGALAI_VECTOR_STORE_TYPE", "FAISS").upper()

    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "YOUR-PINECONE-KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV", "YOUR-PINECONE-ENV")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-judgments-index")

    # Milvus
    MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "legal_judgments")
    MILVUS_DIM = int(os.getenv("MILVUS_DIM", "768"))

    # Chunking
    CHUNK_SIZE = int(os.getenv("LEGALAI_CHUNK_SIZE", "300"))
    CHUNK_OVERLAP = int(os.getenv("LEGALAI_CHUNK_OVERLAP", "50"))

    # Retrieval
    RETRIEVAL_TOP_K = int(os.getenv("LEGALAI_RETRIEVAL_TOP_K", "3"))

    # Model/Training
    BATCH_SIZE = int(os.getenv("LEGALAI_BATCH_SIZE", "4"))
    MAX_NEW_TOKENS = int(os.getenv("LEGALAI_MAX_NEW_TOKENS", "128"))

    # Weights & Biases
    WAND_PROJECT = os.getenv("LEGALAI_WANDB_PROJECT", "legalai-project")
    WAND_RUNNAME = os.getenv("LEGALAI_WANDB_RUNNAME", "default-run")
