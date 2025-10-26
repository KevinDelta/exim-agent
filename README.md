# EXIM Agent - Trade Compliance Intelligence Platform

An AI-powered trade compliance agent built with **LangChain v1**, **LangGraph**, and **Mem0** for intelligent export-import operations.

## Features

### Core Capabilities

* **Compliance Intelligence**: Automated compliance checks with HTS codes, sanctions screening, refusals analysis, and rulings lookup
* **Memory System**: Long-term conversational memory using Mem0 for personalized interactions
* **RAG Chat**: Document-grounded question answering with reranking and context fusion
* **Document Ingestion**: Multi-format document processing with intelligent chunking
* **Evaluation Suite**: Built-in RAG evaluation with faithfulness, relevance, and precision metrics
* **MLOps Integration**: Optional ZenML pipelines for experiment tracking and lineage

### Architecture

* **LangGraph Workflows**: Multi-agent orchestration for compliance and chat workflows
* **Vector Storage**: ChromaDB for document embeddings and retrieval
* **RESTful API**: FastAPI with async support and interactive docs
* **Observability**: LangSmith integration for tracing and monitoring

## Tech Stack

* **LangChain v1**: Agent framework with tools and middleware
* **LangGraph**: State machine orchestration for multi-step workflows
* **Mem0**: Persistent conversational memory system
* **ChromaDB**: Vector database for RAG and compliance data
* **OpenAI**: GPT-4 and embeddings (text-embedding-3-small)
* **FastAPI**: Modern async API framework
* **ZenML**: MLOps orchestration (optional)
* **Python 3.11+**: Type hints and modern Python features

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
# Required
OPENAI_API_KEY="your-openai-key"

# Mem0 Configuration (Optional - uses Qdrant for memory storage)
MEM0_API_KEY="your-mem0-key"  # If using Mem0 cloud
MEM0_ENABLED=true

# LangSmith Tracing (Optional)
LANGCHAIN_API_KEY="your-langsmith-key"
LANGCHAIN_PROJECT="exim-agent"
LANGCHAIN_TRACING_V2=true

# Application Settings
ENABLE_RERANKING=true  # Enable context reranking
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

## Project Structure

```bash
src/exim_agent/
├── application/
│   ├── chat_service/          # RAG chat with LangGraph + Mem0
│   ├── compliance_service/    # Compliance workflow (HTS, sanctions, etc.)
│   ├── evaluation_service/    # RAG evaluation metrics
│   ├── ingest_documents_service/  # Document processing
│   ├── memory_service/        # Mem0 memory management
│   ├── reranking_service/     # Context reranking
│   └── zenml_pipelines/       # MLOps orchestration (optional)
├── domain/
│   ├── compliance/            # Compliance models and enums
│   ├── models.py              # Domain models
│   ├── tools.py               # LangChain tools
│   └── exceptions.py          # Custom exceptions
├── infrastructure/
│   ├── api/                   # FastAPI endpoints and routes
│   ├── db/                    # ChromaDB and compliance collections
│   └── llm_providers/         # OpenAI and LangChain providers
└── config.py                  # Application settings (Pydantic)
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

### Core Endpoints

* `POST /chat` - Chat with RAG + Mem0 memory capabilities
* `POST /ingest-documents` - Ingest documents into vector store
* `POST /reset-memory` - Clear vector store
* `POST /evaluate` - Evaluate RAG response quality
* `GET /evaluation/metrics` - List available evaluation metrics
* `GET /health` - System health check

### Memory Management (Mem0)

* `POST /memory/add` - Add memory for a user
* `GET /memory/get` - Retrieve user memories
* `POST /memory/search` - Search memories
* `POST /memory/update` - Update existing memory
* `DELETE /memory/delete` - Delete specific memory
* `DELETE /memory/delete-all` - Clear all memories for a user
* `GET /memory/history` - Get conversation history

### ZenML Pipelines (Optional)

* `POST /pipelines/ingest` - Run ingestion via ZenML pipeline
* `POST /pipelines/analytics` - Run memory analytics pipeline
* `GET /pipelines/status` - Check ZenML integration status

### Documentation

* `GET /docs` - Interactive Swagger UI
* `GET /redoc` - Alternative API documentation

## Additional Documentation

* **[Ingestion Guide](INGESTION_GUIDE.md)**: Complete guide to document ingestion
* **[LangChain v1 Refactor Guide](LANGCHAIN_V1_REFACTOR_GUIDE.md)**: Migration details
* **[Implementation Progress](IMPLEMENTATION_PROGRESS_REPORT.md)**: Development roadmap and status
* **API Docs**: Visit `http://localhost:8000/docs` when running

## Development

### Running Tests

```bash
pytest tests/
```

### Docker Support

```bash
# Build and run
docker build -t exim-agent .
docker run -p 8000:8000 exim-agent

# Or use make
make start-project
```

## Credits

Built with modern AI stack: **LangChain v1**, **LangGraph**, **Mem0**, and **ZenML**.

Original template from [agent-api-cookiecutter](https://github.com/neural-maze/agent-api-cookiecutter).
