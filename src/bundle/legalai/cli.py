import click
import os
import json
import csv
from PyPDF2 import PdfReader
from .config import get_config
from .retrieval import get_vector_store, retrieve_documents
from .summarization import Summarizer
from .conversation import ConversationMemory
from .model import UnifiedLanguageModel

from bundle.core import logger

log = logger.get_logger(__name__)


@click.group()
def cli():
    """Command-line interface for LegalAI"""
    pass


@cli.command()
@click.argument("doc_path", type=click.Path(exists=True))
def index_documents(doc_path):
    """
    Read documents from doc_path (PDF, JSON, CSV, or text).
    Chunk, embed, and upsert them into the vector store.
    """
    file_ext = os.path.splitext(doc_path)[1].lower()
    log.debug("Reading document")

    docs = []
    metas = []

    if file_ext == ".pdf":
        # --- PDF Handling ---
        # Using PyPDF2 or pypdf to extract text from each page.
        reader = PdfReader(doc_path)
        all_pages_text = []
        page_count = 0
        for page in reader.pages:
            page_count += 1
            log.debug("Reading page: %d", page_count)
            page_text = page.extract_text() or ""
            all_pages_text.append(page_text)

        # Option 1: Combine all pages into one big string
        combined_text = "\n".join(all_pages_text)
        doc_meta = {"doc_id": f"pdf-{os.path.basename(doc_path)}"}
        docs.append(combined_text)
        metas.append(doc_meta)

        # Option 2 (alternative): Create one "doc" per page
        # for i, page_text in enumerate(all_pages_text):
        #     doc_meta = {"doc_id": f"{os.path.basename(doc_path)}-page-{i}"}
        #     docs.append(page_text)
        #     metas.append(doc_meta)

    elif file_ext == ".csv":
        # --- CSV Handling ---
        with open(doc_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Assume each row is either a single column of text or
            # combine multiple columns as needed
            for i, row in enumerate(reader):
                text = " ".join(row).strip()
                doc_meta = {"doc_id": f"csv-{i}"}
                docs.append(text)
                metas.append(doc_meta)

    elif file_ext == ".json":
        # --- JSON Handling ---
        # Example 1: Each line is a JSON object with a "text" field
        with open(doc_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                # If your JSON structure differs, adapt accordingly
                text = data.get("text", "")
                doc_meta = {"doc_id": f"json-{i}"}
                docs.append(text)
                metas.append(doc_meta)

        # Example 2: The file is a single JSON list of documents
        # with open(doc_path, "r", encoding="utf-8") as f:
        #     data_list = json.load(f)
        #     for i, data in enumerate(data_list):
        #         text = data.get("text", "")
        #         doc_meta = {"doc_id": f"json-{i}"}
        #         docs.append(text)
        #         metas.append(doc_meta)

    else:
        # --- Plain Text Handling (Default) ---
        with open(doc_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                text = line.strip()
                doc_meta = {"doc_id": f"text-{i}"}
                docs.append(text)
                metas.append(doc_meta)

    # Now that we have docs + metas, upsert into the vector store
    model = UnifiedLanguageModel()
    store = get_vector_store(model)
    # TMP TBR
    docs = docs[:1]
    metas = metas[:1]
    store.upsert(docs, metas)
    click.echo("Indexing complete.")


@cli.command()
@click.option("--query", prompt="Your query")
def summarize(query):
    """
    Retrieve top-k docs and summarize with the Llama-based Summarizer.
    """
    model = UnifiedLanguageModel()
    store = get_vector_store(model)

    results = retrieve_documents(query, store, get_config().retrieval_top_k)
    context = []
    for r in results:
        # Pinecone returns text=None (metadata only), Faiss & Milvus might store text
        if r.get("text"):
            context.append(r["text"])
        elif r.get("metadata"):
            context.append(str(r["metadata"]))

    summarizer = Summarizer(model)
    summary = summarizer.summarize_context(context, query)
    click.echo(f"\n=== Summary ===\n{summary}")


@cli.command()
def interactive():
    """
    Basic interactive conversation using multi-turn memory.
    """
    # 1) Initialize conversation memory
    memory = ConversationMemory()

    # 2) Initialize a single UnifiedLanguageModel
    model = UnifiedLanguageModel()

    # 3) Build the chosen vector store (MILVUS or FAISS or whatever)
    #    and pass `model` so it reuses the same embeddings
    store = get_vector_store(model)

    # 4) Summarizer also uses the same `UnifiedLanguageModel`
    summarizer = Summarizer(model)

    while True:
        user_query = click.prompt("User")
        if user_query.lower() in ["exit", "quit"]:
            break

        # 5) Retrieve documents from the vector store
        results = retrieve_documents(user_query, store, get_config().retrieval_top_k)

        # 6) Build a context from retrieved docs
        context = []
        for r in results:
            # If your store returns { "text": "...", "metadata": {...} }
            # you can store 'text' or anything else.
            if r.get("text"):
                context.append(r["text"])
            else:
                # In Milvus, you might only have 'id' or 'meta'
                # So we fallback to metadata or a string representation
                context.append(str(r.get("meta", r)))

        # 7) Add user turn and a short system message
        memory.add_turn("user", user_query)
        system_msg = "You are a legal AI specialized in European judgments."
        memory.add_turn("system", system_msg)

        # 8) Build conversation prompt (not strictly used here, but could be for debugging)
        conv_prompt = memory.to_prompt()  # e.g. "User: <...>\nSystem: <...>\n..."

        # 9) Summarize or generate a response from the retrieved context
        summary = summarizer.summarize_context(context, user_query)

        # 10) Add the assistant turn to the memory
        memory.add_turn("assistant", summary)

        click.echo(f"Assistant: {summary}")


if __name__ == "__main__":
    cli()
