# LangChain v1 Refactoring Guide

## Overview

This document outlines the migration strategy from LlamaIndex to LangChain v1 for the RAG application.

## Current Architecture (LlamaIndex-based)

### Components

```Bash
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Infrastructure Layer                                        │
│  ├── LLM Providers (openai_provider.py)                     │
│  │   ├── LlamaIndex Settings                                │
│  │   ├── OpenAIEmbedding                                    │
│  │   └── OpenAI (LLM)                                       │
│  │                                                           │
│  ├── Database (chroma_client.py)                            │
│  │   ├── ChromaDB PersistentClient                          │
│  │   ├── ChromaVectorStore (LlamaIndex)                     │
│  │   └── StorageContext (LlamaIndex)                        │
│  │                                                           │
│  └── API (main.py)                                          │
│      └── Endpoints: /ingest-documents, /chat, /eval, etc.   │
│                                                               │
│  Application Layer                                           │
│  └── Services                                                │
│      └── IngestDocumentsService                             │
│          ├── SimpleDirectoryReader (LlamaIndex)             │
│          └── VectorStoreIndex (LlamaIndex)                  │
│                                                               │
│  Domain Layer                                                │
│  ├── Models (Document, IngestionResult)                     │
│  └── Exceptions                                              │
└─────────────────────────────────────────────────────────────┘
```

## Target Architecture (LangChain v1)

### Components2

```Bash
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Infrastructure Layer                                        │
│  ├── LLM Providers (langchain_provider.py)                  │
│  │   ├── ChatOpenAI (LangChain)                             │
│  │   └── OpenAIEmbeddings (LangChain)                       │
│  │                                                           │
│  ├── Database (chroma_client.py)                            │
│  │   ├── ChromaDB PersistentClient                          │
│  │   └── Chroma (LangChain vector store)                    │
│  │                                                           │
│  └── API (main.py)                                          │
│      └── Endpoints: /ingest-documents, /chat, /eval, etc.   │
│                                                               │
│  Application Layer                                           │
│  ├── IngestDocumentsService                                 │
│  │   ├── DirectoryLoader (LangChain)                        │
│  │   ├── RecursiveCharacterTextSplitter (LangChain)         │
│  │   └── Chroma.from_documents()                            │
│  │                                                           │
│  └── ChatService                                             │
│      ├── create_agent() (LangChain v1)                      │
│      ├── Retriever (from Chroma)                            │
│      └── RAG Chain                                           │
│                                                               │
│  Domain Layer                                                │
│  ├── Models (Document, IngestionResult, ChatRequest, etc.)  │
│  └── Exceptions                                              │
└─────────────────────────────────────────────────────────────┘
```

## Migration Steps

### 1. ChromaDB Client Refactoring

**Current (LlamaIndex):**

```python
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
```

**Target (LangChain):**

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vectorstore = Chroma(
    collection_name=collection_name,
    embedding_function=OpenAIEmbeddings(),
    persist_directory=persist_directory
)
```

### 2. LLM Provider Refactoring

**Current (LlamaIndex):**

```python
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

Settings.llm = OpenAI(model=model_name, api_key=api_key)
Settings.embed_model = OpenAIEmbedding(model=embed_model, api_key=api_key)
```

**Target (LangChain):**

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    temperature=temperature
)

embeddings = OpenAIEmbeddings(
    model=embed_model,
    api_key=api_key
)
```

### 3. Document Ingestion Refactoring

**Current (LlamaIndex):**

```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

reader = SimpleDirectoryReader(input_dir=path, recursive=True)
documents = reader.load_data()
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
```

**Target (LangChain):**

```python
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# Load documents
loader = DirectoryLoader(
    path,
    glob="**/*",
    loader_cls=TextLoader,
    show_progress=True
)
documents = loader.load()

# Split documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)
splits = text_splitter.split_documents(documents)

# Create vector store
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    collection_name=collection_name,
    persist_directory=persist_directory
)
```

### 4. Chat Service (New - RAG with LangChain v1)

**Implementation:**

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage

# Create retriever tool
@tool
def retrieve_documents(query: str) -> str:
    """Retrieve relevant documents from the knowledge base."""
    docs = vectorstore.similarity_search(query, k=5)
    return "\n\n".join([doc.page_content for doc in docs])

# Create agent
agent = create_agent(
    model=llm,
    tools=[retrieve_documents],
    system_prompt="You are a helpful assistant that answers questions using the provided context."
)

# Invoke agent
response = agent.invoke({
    "messages": [HumanMessage(content=user_question)]
})
```

## File-by-File Migration Plan

### Infrastructure Layer

#### 1. `infrastructure/llm_providers/langchain_provider.py` (NEW)

- Replace `openai_provider.py`
- Initialize ChatOpenAI and OpenAIEmbeddings
- Remove LlamaIndex Settings
- Return instances instead of setting global state

#### 2. `infrastructure/db/chroma_client.py` (REFACTOR)

- Remove LlamaIndex imports
- Use `langchain_chroma.Chroma` instead of `ChromaVectorStore`
- Update methods to work with LangChain vector store
- Keep similar interface for backward compatibility

### Application Layer

#### 3. `application/ingest_documents_service/service.py` (REFACTOR)

- Replace `SimpleDirectoryReader` with `DirectoryLoader`
- Add `RecursiveCharacterTextSplitter` for chunking
- Use `Chroma.from_documents()` instead of `VectorStoreIndex`
- Support multiple file loaders (PDF, DOCX, TXT, etc.)

#### 4. `application/chat_service/service.py` (NEW)

- Create RAG agent using `create_agent()`
- Implement retriever tool
- Handle conversation history
- Support streaming responses

### API Layer

#### 5. `infrastructure/api/main.py` (UPDATE)

- Update lifespan to initialize LangChain providers
- Add chat endpoint implementation
- Keep ingestion endpoint compatible

#### 6. `infrastructure/api/models.py` (UPDATE)

- Add ChatRequest and ChatResponse models
- Keep existing models compatible

### Configuration

#### 7. `config.py` (UPDATE)

- Add LangChain-specific settings
- Remove LlamaIndex-specific settings
- Add agent configuration options

## Dependency Changes

### Remove

```toml
"llama-index>=0.14.3",
"llama-index-vector-stores-chroma>=0.5.3",
"llama-index-core>=0.14.3",
```

### Keep/Verify

```toml
"langchain>=1.0.0",
"langchain-openai>=0.3.34",
"langchain-core>=1.0.0",
"langchain-chroma>=0.3.0",  # Add if not present
"chromadb>=1.1.0",
"openai>=1.109.1",
```

## Testing Strategy

### Unit Tests

1. Test ChromaDB client with LangChain vector store
2. Test document loading with various file types
3. Test text splitting with different parameters
4. Test embedding creation
5. Test retrieval functionality

### Integration Tests

1. Test end-to-end document ingestion
2. Test RAG chat with retrieval
3. Test API endpoints

### Manual Testing

1. Ingest sample documents
2. Query with various questions
3. Verify responses use retrieved context
4. Test edge cases (no documents, empty query, etc.)

## Rollback Strategy

1. Keep LlamaIndex code in separate branch
2. Use feature flags if deploying incrementally
3. Maintain data compatibility (ChromaDB format unchanged)
4. Document any breaking changes in API

## Benefits of Migration

1. **Modern Framework**: LangChain v1 offers newer agent architecture
2. **Better Tooling**: Enhanced middleware, hooks, and agent capabilities
3. **Flexibility**: Dynamic models, structured outputs, better prompt management
4. **Community**: Larger ecosystem and more examples
5. **Performance**: Better streaming and async support
6. **Observability**: Better integration with LangSmith tracing

## Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes in API | Keep models compatible, version API |
| Performance degradation | Benchmark before/after, optimize chunks |
| Data loss during migration | Use same ChromaDB format, test thoroughly |
| Learning curve | Document well, provide examples |
| Dependency conflicts | Use virtual environment, lock versions |

## Timeline Estimate

- **ChromaDB Client**: 2-3 hours
- **LLM Providers**: 1-2 hours
- **Document Ingestion**: 3-4 hours
- **Chat Service (NEW)**: 4-5 hours
- **API Updates**: 2-3 hours
- **Testing**: 4-5 hours
- **Documentation**: 2-3 hours

**Total**: ~20-25 hours

## Next Steps

1. Review and approve this guide
2. Create feature branch for refactoring
3. Start with infrastructure layer (ChromaDB + LLM providers)
4. Move to application layer (ingestion + chat)
5. Update API and documentation
6. Comprehensive testing
7. Deploy to staging
8. Production deployment

## References

- [LangChain v1 Documentation](https://python.langchain.com/docs/get_started/introduction)
- [LangChain Agents](https://python.langchain.com/docs/concepts/agents)
- [LangChain Chroma Integration](https://python.langchain.com/docs/integrations/vectorstores/chroma)
- [LangChain Document Loaders](https://python.langchain.com/docs/integrations/document_loaders)
