# LegalAI Project

## Overview
LegalAI is a modular, scalable, and extensible framework designed for processing, analyzing, and summarizing legal documents. It leverages state-of-the-art AI technologies to handle embeddings, retrieval, summarization, and conversation flows tailored for legal applications.

---

## Features
1. **Configuration Management**:
   - Centralized configuration in `config.py` for easy setup and customization.

2. **Embeddings**:
   - Generates embeddings using transformer-based models for semantic understanding.

3. **Document Retrieval**:
   - Supports multiple vector storage backends, including FAISS and Milvus.

4. **Summarization**:
   - Extracts concise and relevant summaries from lengthy legal documents.

5. **Conversation Handling**:
   - Manages context-aware conversations through memory persistence.

6. **CLI Interface**:
   - Command-line tools for indexing, retrieval, and other interactions.

7. **Modularity**:
   - Easy to extend or replace components, such as vector stores or summarizers.

---

## Project Structure
```
legalai/
├── core/                  # Core business logic
│   ├── conversation.py    # Conversation flow management
│   ├── evaluation.py      # Model and performance evaluation
│   ├── retrieval.py       # Document retrieval interface
│   ├── summarization.py   # Summarization logic
├── datastore/             # Vector store management
│   ├── base.py            # Abstract base class for vector stores
│   ├── faiss_store.py     # FAISS-based vector store implementation
│   ├── milvius_store.py   # Milvus-based vector store implementation
├── cli/                   # CLI tools
│   ├── cli.py             # Command-line interface implementation
├── config.py              # Centralized configuration
├── training.py            # Training pipeline
└── tests/                 # Unit and integration tests
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Virtual environment (recommended)
- Libraries and dependencies (see `requirements.txt`)
- FAISS or Milvus server for vector storage (if applicable)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/legalai.git
cd legalai

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Settings
Modify the `config.py` file to set up your model names, vector store type, and other parameters:
```python
model_name = "mistralai/Mistral-7B-v0.3"
vector_store_type = "FAISS"  # Options: FAISS, MILVUS
```

### 4. Run CLI Commands
- Index documents:
  ```bash
  python -m legalai.cli index_documents /path/to/documents
  ```
- Retrieve documents:
  ```bash
  python -m legalai.cli retrieve "Your query here"
  ```

---

## Usage

### Example Workflow
1. **Indexing**:
   - Parse and index legal documents into the vector store.
2. **Querying**:
   - Use the retrieval module to fetch relevant documents.
3. **Summarization**:
   - Summarize retrieved documents for quick insights.
4. **Conversational AI**:
   - Handle user queries interactively with memory-enabled conversations.

---

## Contributing
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes and push:
   ```bash
   git commit -m "Description of feature"
   git push origin feature-name
   ```
4. Create a pull request.

---

## Future Plans
- Add support for distributed vector search.
- Optimize for multi-GPU setups.
- Extend summarization for multi-document contexts.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

---
