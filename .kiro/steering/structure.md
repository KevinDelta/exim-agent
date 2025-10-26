# Project Structure & Architecture

## Clean Architecture Pattern

The project follows **Clean Architecture** principles with clear separation of concerns:

```
src/exim_agent/
├── domain/                    # Business logic & entities
├── application/               # Use cases & services  
├── infrastructure/            # External concerns (API, DB, LLM)
└── config.py                  # Application configuration
```

## Domain Layer (`domain/`)
- **models.py**: Core business entities (Document, IngestionResult)
- **exceptions.py**: Domain-specific exceptions
- **compliance/**: Compliance domain models and enums
- **tools/**: Business logic tools (HTS, sanctions, rulings)

## Application Layer (`application/`)
Service-oriented architecture with focused responsibilities:

- **chat_service/**: RAG chat with LangGraph state machines
- **compliance_service/**: Compliance monitoring and snapshots
- **ingest_documents_service/**: Document processing pipeline
- **evaluation_service/**: RAG quality metrics and evaluation
- **memory_service/**: Mem0 conversational memory management
- **reranking_service/**: Context reranking for improved retrieval
- **zenml_pipelines/**: MLOps pipeline orchestration

## Infrastructure Layer (`infrastructure/`)
External system integrations:

- **api/**: FastAPI routes and HTTP models
- **db/**: ChromaDB client and collection management
- **llm_providers/**: Multi-provider LLM abstraction (OpenAI, Anthropic, Groq)

## Key Conventions

### File Organization
- Each service has its own directory with `__init__.py` and `service.py`
- Domain models are grouped by business area (compliance, memory, etc.)
- Infrastructure concerns are separated by technology (api, db, llm_providers)

### Naming Patterns
- Services: `{domain}_service` (e.g., `chat_service`, `compliance_service`)
- Models: PascalCase with descriptive names (`ComplianceEvent`, `ClientProfile`)
- Enums: Descriptive names with string values (`EventType`, `RiskLevel`)
- Configuration: Single `config.py` with Pydantic Settings

### Import Structure
- Domain layer imports nothing from application/infrastructure
- Application layer can import from domain
- Infrastructure layer can import from domain and application
- Use relative imports within packages, absolute for cross-package

### Data Flow
1. **API Layer** receives requests and validates input
2. **Application Services** orchestrate business logic
3. **Domain Models** represent business entities
4. **Infrastructure** handles external system interactions

## Configuration Management
- **Environment Variables**: `.env` file with `.env.example` template
- **Pydantic Settings**: Type-safe configuration in `config.py`
- **Docker Overrides**: Container-specific paths in `docker-compose.yaml`

## Testing Structure
```
tests/
├── conftest.py               # Shared test fixtures
├── test_*.py                 # Unit tests matching src structure
└── __pycache__/              # Python cache (gitignored)
```

## Data Directories
```
data/
├── documents/                # Source documents for ingestion
│   ├── pdf/                 # PDF files
│   ├── txt/                 # Text files
│   └── csv/                 # CSV files
├── chroma_db/               # ChromaDB vector storage
└── mem0_history.db          # SQLite conversation history
```