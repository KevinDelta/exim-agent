# ChromaDB Shared Client Architecture

## Production-Ready Design

### Architecture Overview

Single ChromaDB client instance shared across all services with separate collections:

```bash
ChromaDB Client (Singleton)
├── documents collection (RAG)
├── mem0_memories collection (Mem0)
└── mem0migrations collection (Mem0 internal)
```

### Implementation

#### 1. Shared Client Manager (`chroma_client.py`)

```python
class ChromaDBClient:
    """
    Shared ChromaDB client managing multiple collections.
    Single client instance for connection pooling across all services.
    """
    
    def initialize(self):
        # Create single persistent client
        self._client = chromadb.PersistentClient(
            path=config.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        
        # Initialize RAG collection
        self._rag_vector_store = Chroma(
            client=self._client,
            collection_name="documents",
            embedding_function=self._embeddings,
        )
    
    def get_client(self):
        """Expose client for other services (Mem0)."""
        return self._client
```

#### 2. Mem0 Integration (`mem0_client.py`)

```python
def initialize(self):
    from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
    
    # Get shared ChromaDB client
    shared_client = chroma_client.get_client()
    
    # Mem0 creates its own collection on shared client
    mem0_config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "mem0_memories",
                "client": shared_client,
                "path": config.chroma_db_path,  # Required for Mem0 validation
            }
        },
        # ... rest of config
    }
```

**Note**: Mem0's validation requires `path` parameter even when `client` is provided. The `client` takes precedence at runtime.

#### 3. Initialization Order

```python
# main.py lifespan
async def lifespan(app: FastAPI):
    get_llm()                    # 1. Initialize LLM
    get_embeddings()             # 2. Initialize embeddings
    chroma_client.initialize()   # 3. Initialize shared ChromaDB client
    chat_service.initialize()    # 4. Initialize services (including Mem0)
```

### Key Benefits

1. **Single Connection Pool**: One ChromaDB client reduces resource usage
2. **No Singleton Conflicts**: Shared client eliminates initialization errors
3. **Collection Isolation**: RAG and Mem0 data remain separate
4. **Production Ready**: Clean architecture with proper error handling
5. **Scalable**: Easy to add more collections as needed

### Verification

```bash
# Check collections
docker exec agent-api /app/.venv/bin/python -c "
import chromadb
client = chromadb.PersistentClient(path='/app/data/chroma_db')
for col in client.list_collections():
    print(f'{col.name}: {col.count()} documents')
"

# Expected output:
# documents: X documents (RAG)
# mem0_memories: Y documents (Mem0)
# mem0migrations: 2 documents (Mem0 internal)
```

### Docker Configuration

Environment variables ensure correct paths in containers:

```yaml
# docker-compose.yaml
environment:
  - DOCUMENTS_PATH=/app/data/documents
  - CHROMA_DB_PATH=/app/data/chroma_db
  - MEM0_HISTORY_DB_PATH=/app/data/mem0_history.db

volumes:
  - ./data:/app/data  # Persistent storage
```

### Testing

```bash
# Start services
docker compose up --build -d

# Test chat (stores in Mem0)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is Kevin"}'

# Verify health
curl http://localhost:8000/health
```

## Summary

This architecture provides a production-ready solution with:

- ✅ Single ChromaDB client (no singleton conflicts)
- ✅ Separate collections for RAG and Mem0
- ✅ Proper connection pooling
- ✅ Clean service boundaries
- ✅ Full Docker support with health checks
