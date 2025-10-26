# Technology Stack

## Core Framework
- **Python 3.10+**: Modern Python with type hints
- **FastAPI**: Async web framework for REST APIs
- **LangChain v1**: Agent framework with tools and middleware
- **LangGraph v1**: State machine for complex agent workflows
- **Pydantic v2**: Data validation and settings management

## AI/ML Stack
- **OpenAI**: Primary LLM (gpt-5-nano) and embeddings (text-embedding-3-small)
- **Anthropic Claude**: Alternative LLM provider
- **Groq**: High-speed inference option
- **Sentence Transformers**: Cross-encoder reranking models
- **Mem0**: Conversational memory system

## Data & Storage
- **ChromaDB**: Vector database for embeddings storage
- **SQLite**: Local database for Mem0 conversation history
- **Unstructured**: Multi-format document processing

## MLOps & Monitoring
- **ZenML**: ML pipeline orchestration and experiment tracking
- **LangSmith**: LLM observability and tracing
- **MLflow**: Model and experiment tracking

## Build System & Dependencies
- **uv**: Fast Python package manager and dependency resolver
- **pyproject.toml**: Modern Python project configuration
- **Docker**: Containerization with multi-stage builds
- **Docker Compose**: Local development orchestration

## Development Tools
- **Ruff**: Fast Python linter and formatter (line length: 120)
- **pytest**: Testing framework
- **pre-commit**: Git hooks for code quality
- **Loguru**: Structured logging

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Start development server
fastapi dev src/exim_agent/infrastructure/api/main.py

# Run tests
pytest

# Format and lint
ruff format .
ruff check .
```

### Docker Operations
```bash
# Build and start services
make start-project

# Stop services
make stop-project

# Check ChromaDB collections
make check-collections
```

### ZenML Pipelines
```bash
# Initialize ZenML
zenml init

# List pipeline runs
zenml pipeline runs list

# Run ingestion pipeline
curl -X POST http://localhost:8000/pipelines/ingest
```

## Configuration
- Environment variables via `.env` file
- Pydantic Settings for type-safe configuration
- Docker volume mounts for persistent data storage
- Health checks and graceful shutdown support