# RAG Application with LangChain v1

A production-ready RAG (Retrieval-Augmented Generation) application powered by **LangChain v1** agents.

## Features

* **Document Ingestion**: Multi-format document processing with intelligent chunking
* **Vector Storage**: Persistent ChromaDB storage with OpenAI embeddings
* **RAG Chat**: LangChain v1 agent with retrieval capabilities
* **RESTful API**: FastAPI endpoints for ingestion and chat
* **LangSmith Integration**: Built-in observability and tracing

## Tech Stack

* **LangChain v1**: Agent framework with tools and middleware
* **ChromaDB**: Vector database for embeddings storage
* **OpenAI**: LLM (gpt-5-nano) and embeddings (text-embedding-3-small)
* **FastAPI**: Modern async API framework
* **Python 3.10+**: Type hints and modern Python features

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

Create a `.env` file:

```bash
OPENAI_API_KEY="your-key-here"
LANGCHAIN_API_KEY="your-langsmith-key"  # Optional
LANGCHAIN_PROJECT="your-project"  # Optional
```

### 3. Start the API

```bash
# Development mode
fastapi dev src/exim_agent/infrastructure/api/main.py

# Or using Docker
make start-project
```

### 4. Ingest Documents

```bash
# Add some documents
mkdir -p data/documents
echo "LangChain is a framework for building LLM applications." > data/documents/intro.txt

# Ingest via API
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. Chat with Your Documents

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is LangChain?"}'
```

## Documentation

* **[Ingestion Guide](INGESTION_GUIDE.md)**: Complete guide to document ingestion
* **[Refactoring Guide](LANGCHAIN_V1_REFACTOR_GUIDE.md)**: Details on LangChain v1 migration
* **API Docs**: Visit `http://localhost:8000/docs` when running

## Project Structure

```bash
src/exim_agent/
├── application/
│   ├── chat_service/          # RAG chat with LangChain agents
│   └── ingest_documents_service/  # Document processing
├── domain/
│   ├── models.py              # Domain models
│   └── exceptions.py          # Custom exceptions
├── infrastructure/
│   ├── api/                   # FastAPI endpoints
│   ├── db/                    # ChromaDB client
│   └── llm_providers/         # LangChain LLM/embeddings
└── config.py                  # Application settings
```

## Supported File Formats

* Text files (`.txt`, `.md`)
* PDFs (`.pdf`)
* Word documents (`.docx`)
* CSV files (`.csv`)
* JSON files (`.json`)
* HTML files (`.html`)
* EPUB files (`.epub`)

## API Endpoints

* `POST /ingest-documents` - Ingest documents into vector store
* `POST /chat` - Chat with RAG capabilities
* `POST /reset-memory` - Clear vector store
* `GET /docs` - Interactive API documentation

## Credits

This package was created with [Cookiecutter](https://github.com/audreyfeldroy/cookiecutter) and the [agent-api-cookiecutter](https://github.com/neural-maze/agent-api-cookiecutter) project template.

Refactored to use **LangChain v1** for modern agent capabilities.
