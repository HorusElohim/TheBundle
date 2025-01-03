import click
from pathlib import Path
import numpy as np
from typing import List
from bundle.core import logger

from .config import get_config
from .extractors import DocumentExtractorFactory
from .datastore import MilvusVectorStore
from .model import UnifiedLanguageModel
from .summarization import Summarizer
from .conversation import ConversationMemory


log = logger.get_logger(__name__)


@click.group()
def cli():
    """Command-line interface for LegalAI."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def index_documents(file_path: str) -> None:
    """
    Read documents from file_path, chunk, embed, and upsert them into the vector store.
    """
    config = get_config()
    # Select the appropriate document extractor
    extractor = DocumentExtractorFactory.create(
        file_path=Path(file_path), chunk_size=config.chunk_size, overlap=config.chunk_overlap
    )

    # Initialize model and vector store
    model = UnifiedLanguageModel()
    store = MilvusVectorStore()

    texts: List[str] = []
    metas: List[dict] = []

    # Extract documents and metadata
    for doc in extractor.extract():
        texts.append(doc["text"])
        metas.append(doc["meta"])

    # Chunk documents
    combined_texts: List[str] = []
    combined_metas: List[dict] = []
    for text, meta in zip(texts, metas):
        chunks = store.chunk_text(text, chunk_size=get_config().chunk_size, overlap=get_config().chunk_overlap)
        combined_texts.extend(chunks)
        combined_metas.extend([meta] * len(chunks))

    # Encode chunks
    embeddings = model.encode_texts(combined_texts).astype(np.float32)

    # Upsert into vector store
    store.upsert(combined_texts, embeddings, combined_metas)
    log.info("Indexing complete!")


@cli.command()
@click.option("--query", prompt="Your query")
def summarize(query: str) -> None:
    """
    Retrieve top-k docs and summarize with the summarizer.
    """

    # Chunk and encode query
    document = DocumentExtractorFactory.create(chunk_size=get_config().chunk_size, overlap=get_config().chunk_overlap)
    chunked_query = document.chunk_text(query)
    model = UnifiedLanguageModel()
    query_embs = model.encode_texts(chunked_query).astype(np.float32)
    query_emb = np.mean(query_embs, axis=0, keepdims=True)

    # Query vector store
    store = MilvusVectorStore()
    results = store.query(query_emb=query_emb, top_k=3)

    # Summarize results
    context = results.get_text()
    summarizer = Summarizer(model)
    summary = summarizer.summarize_context(context, query)
    log.info(f"Summary:\n{summary}")


@cli.command()
def interactive():
    """
    Basic interactive conversation using multi-turn memory.
    """
    memory = ConversationMemory()
    model = UnifiedLanguageModel()
    store = MilvusVectorStore()
    summarizer = Summarizer(model)

    while True:
        user_query = click.prompt("User")
        if user_query.lower() in ["exit", "quit"]:
            break

        document = DocumentExtractorFactory.create(chunk_size=get_config().chunk_size, overlap=get_config().chunk_overlap)
        chunked_query = document.chunk_text(user_query)
        query_embs = model.encode_texts(chunked_query).astype(np.float32)
        mean_query_emb = np.mean(query_embs, axis=0, keepdims=True)

        results = store.query(mean_query_emb, top_k=2)
        context = results.get_text()

        memory.add_turn("user", user_query)
        system_msg = "You are a legal AI specialized in European judgments."
        memory.add_turn("system", system_msg)

        summary = summarizer.summarize_context(context, user_query)
        memory.add_turn("assistant", summary)
        log.info(f"\nAssistant: {summary}\n")


if __name__ == "__main__":
    cli()
