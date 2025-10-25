# Mem0 Integration Architecture

## Overview

This document outlines integrating **Mem0** as the memory layer while keeping: **LangGraph**, **Chroma**, **FastAPI**, **UV**, **Docker**, and **ZenML**.

---

## Current vs Proposed Stack

### Current (Custom Memory)

```bash
FastAPI → LangGraph → Custom Memory Services → ChromaDB → ZenML
         (7 nodes)   (session_manager.py,
                      deduplication.py,
                      summarization.py,
                      promotion.py,
                      intent_classifier.py,
                      entity_extractor.py)
```

### Proposed (With Mem0)

```bash
FastAPI → LangGraph → Mem0 API → ChromaDB → ZenML
         (4 nodes)    (replaces all custom memory logic)
```

---

## What Gets Replaced

| Component | Current | With Mem0 |
|-----------|---------|-----------|
| **Working Memory** | `session_manager.py` (LRU cache) | Mem0 session memory |
| **Episodic Memory** | Custom ChromaDB collection | Mem0 user/agent memory |
| **Deduplication** | `deduplication.py` (350 lines) | Mem0 built-in |
| **Summarization** | `conversation_summarizer.py` (250 lines) | Mem0 built-in |
| **Promotion** | `promotion.py` (300 lines) | Mem0 automatic |
| **Intent/Entity** | Custom classifiers (400 lines) | Mem0 built-in |
| **Memory Service** | `service.py` (200 lines) | Mem0 wrapper (100 lines) |

Total Code Reduction: ~1,500 lines → ~100 lines

---

## What Stays

- ✅ **LangGraph**: Orchestration (simplified from 7 to 4 nodes)
- ✅ **ChromaDB**: Vector DB backend (Mem0 uses it) + document RAG
- ✅ **FastAPI**: API layer
- ✅ **UV**: Dependency management
- ✅ **Docker**: Containerization
- ✅ **ZenML**: MLOps pipelines (adapted)
- ✅ **Reranking**: Cross-encoder for result fusion
- ✅ **LLM Providers**: Multi-provider architecture

---

## New Dependencies

```toml
# pyproject.toml
dependencies = [
  # Existing
  "langchain>=1.0.0a14",
  "langgraph>=0.2.62",
  "chromadb>=1.1.0",
  "fastapi[standard]",
  "zenml[server]>=0.70.0",
  
  # NEW: Add Mem0
  "mem0ai>=0.1.0",
]
```

---

## Configuration Changes

```python
# config.py (additions)

class Config:
    # ... existing config ...
    
    # Mem0 Settings
    mem0_enabled: bool = True
    mem0_vector_store: str = "chroma"
    mem0_llm_provider: str = "openai"
    mem0_llm_model: str = "gpt-4o-mini"
    mem0_embedder_model: str = "text-embedding-3-small"
    mem0_enable_dedup: bool = True
    mem0_history_limit: int = 10
```

---

## Simplified Directory Structure

```bash
src/acc_llamaindex/
├── application/
│   ├── chat_service/
│   │   ├── graph.py              # Simplified (7 → 4 nodes)
│   │   └── service.py
│   │
│   ├── memory_service/           # REPLACED
│   │   ├── mem0_client.py        # NEW: Thin wrapper (~100 lines)
│   │   └── memory_types.py       # NEW: Type definitions
│   │   # REMOVED:
│   │   # - session_manager.py
│   │   # - deduplication.py
│   │   # - conversation_summarizer.py
│   │   # - promotion.py
│   │   # - intent_classifier.py
│   │   # - entity_extractor.py
│   │   # - salience_tracker.py
│   │   # - background_jobs.py
│   │   # - metrics.py
│   │
│   ├── ingest_documents_service/ # UNCHANGED (RAG documents)
│   └── zenml_pipelines/          # ADAPTED
│       ├── ingestion_pipeline.py       # Document ingestion
│       └── memory_analytics_pipeline.py # NEW: Memory insights
│
├── infrastructure/
│   ├── api/routes/
│   │   ├── chat_routes.py        # UPDATED (use Mem0)
│   │   └── memory_routes.py      # NEW (Mem0 CRUD)
│   └── db/
│       └── chroma_client.py      # SIMPLIFIED (no EM collection)
```

---

## Mem0 Client Wrapper

```python
# application/memory_service/mem0_client.py

from mem0 import Memory
from typing import List, Dict, Any, Optional
from loguru import logger
from acc_llamaindex.config import config

class Mem0Client:
    """Thin wrapper around Mem0 API."""
    
    def __init__(self):
        self.config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "host": config.chroma_host,
                    "port": config.chroma_port,
                }
            },
            "llm": {
                "provider": config.mem0_llm_provider,
                "config": {
                    "model": config.mem0_llm_model,
                    "api_key": config.openai_api_key,
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": config.mem0_embedder_model,
                }
            },
        }
        self.memory = Memory.from_config(self.config)
        logger.info("Mem0 initialized")
    
    def add(self, messages: List[Dict], user_id: str, session_id: str):
        """Add conversation to memory."""
        return self.memory.add(
            messages=messages,
            user_id=user_id,
            session_id=session_id
        )
    
    def search(self, query: str, user_id: str, session_id: str, limit: int = 10):
        """Search memories."""
        return self.memory.search(
            query=query,
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
    
    def get_all(self, user_id: str = None, session_id: str = None):
        """Get all memories."""
        return self.memory.get_all(user_id=user_id, session_id=session_id)
    
    def delete(self, memory_id: str):
        """Delete memory."""
        return self.memory.delete(memory_id)
    
    def reset(self, user_id: str = None, session_id: str = None):
        """Reset memories."""
        return self.memory.reset(user_id=user_id, session_id=session_id)

# Global instance
mem0_client = Mem0Client()
```

---

## Simplified LangGraph (7 → 4 Nodes)

```python
# application/chat_service/graph.py

from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from acc_llamaindex.application.memory_service.mem0_client import mem0_client

class MemoryState(TypedDict):
    query: str
    user_id: str
    session_id: str
    memories: List[dict]
    rag_docs: List[dict]
    response: str

# Node 1: Load memories (replaces 3 custom nodes)
def load_memories(state: MemoryState) -> MemoryState:
    """Mem0 handles: working memory + episodic + intent/entity extraction"""
    state["memories"] = mem0_client.search(
        query=state["query"],
        user_id=state["user_id"],
        session_id=state["session_id"]
    )
    return state

# Node 2: Query RAG documents (unchanged)
def query_documents(state: MemoryState) -> MemoryState:
    """Query ChromaDB for document context"""
    # ... existing RAG logic ...
    return state

# Node 3: Generate response (unchanged)
def generate_response(state: MemoryState) -> MemoryState:
    """Generate answer with LLM"""
    # ... existing generation logic ...
    return state

# Node 4: Update memories (replaces 3 custom nodes)
def update_memories(state: MemoryState) -> MemoryState:
    """Mem0 handles: deduplication + summarization + promotion"""
    mem0_client.add(
        messages=[
            {"role": "user", "content": state["query"]},
            {"role": "assistant", "content": state["response"]}
        ],
        user_id=state["user_id"],
        session_id=state["session_id"]
    )
    return state

# Build graph: 4 nodes instead of 7
workflow = StateGraph(MemoryState)
workflow.add_node("load_memories", load_memories)
workflow.add_node("query_documents", query_documents)
workflow.add_node("generate_response", generate_response)
workflow.add_node("update_memories", update_memories)

workflow.set_entry_point("load_memories")
workflow.add_edge("load_memories", "query_documents")
workflow.add_edge("query_documents", "generate_response")
workflow.add_edge("generate_response", "update_memories")
workflow.add_edge("update_memories", END)

memory_graph = workflow.compile()
```

---

## API Endpoints

### Memory Routes (NEW)

```python
# infrastructure/api/routes/memory_routes.py

from fastapi import APIRouter
from acc_llamaindex.application.memory_service.mem0_client import mem0_client

router = APIRouter(prefix="/memory", tags=["memory"])

@router.post("/search")
async def search_memory(query: str, user_id: str, session_id: str):
    """Search memories"""
    results = mem0_client.search(query, user_id, session_id)
    return {"memories": results}

@router.get("/all")
async def get_all_memories(user_id: str = None, session_id: str = None):
    """Get all memories"""
    memories = mem0_client.get_all(user_id, session_id)
    return {"memories": memories}

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete memory"""
    mem0_client.delete(memory_id)
    return {"status": "deleted"}

@router.post("/reset")
async def reset_memories(user_id: str = None, session_id: str = None):
    """Reset all memories"""
    mem0_client.reset(user_id, session_id)
    return {"status": "reset"}
```

---

## ZenML Adaptations

### Document Ingestion (UNCHANGED)

- Still ingests documents into ChromaDB
- Mem0 doesn't handle document RAG, only conversational memory

### Memory Analytics (NEW)

```python
# application/zenml_pipelines/memory_analytics_pipeline.py

from zenml import pipeline, step
from acc_llamaindex.application.memory_service.mem0_client import mem0_client

@step
def fetch_memories(user_id: str):
    return mem0_client.get_all(user_id=user_id)

@step
def analyze_patterns(memories):
    # Analyze memory usage, trends, etc.
    return {"total": len(memories), "stats": {...}}

@pipeline
def memory_analytics_pipeline(user_id: str):
    memories = fetch_memories(user_id)
    stats = analyze_patterns(memories)
    return stats
```

---

## Benefits of Mem0 Integration

### 1. **Massive Code Reduction**

- **Before**: ~1,500 lines of custom memory code
- **After**: ~100 lines (thin wrapper)
- **Reduction**: 93% less code to maintain

### 2. **Built-in Features**

- ✅ Automatic deduplication (no custom similarity checks)
- ✅ Conversation summarization (no custom LLM prompts)
- ✅ Temporal decay (memories fade naturally)
- ✅ Smart promotion (episodic → long-term)
- ✅ Entity extraction (no custom NER)
- ✅ Intent classification (no custom classifier)

### 3. **Simplified Architecture**

- **LangGraph**: 7 nodes → 4 nodes (43% reduction)
- **Memory Service**: 9 files → 2 files
- **Maintenance**: Much lower complexity

### 4. **Keep Your Strengths**

- ✅ LangGraph orchestration
- ✅ Multi-provider LLM architecture
- ✅ Cross-encoder reranking
- ✅ ZenML pipelines
- ✅ FastAPI endpoints
- ✅ Docker deployment

---

## Migration Strategy

### Phase 1: Install & Configure

1. Add `mem0ai` to `pyproject.toml`
2. Run `uv sync`
3. Add Mem0 config to `config.py`

### Phase 2: Create Wrapper

1. Create `memory_service/mem0_client.py`
2. Test Mem0 connection
3. Verify ChromaDB integration

### Phase 3: Simplify LangGraph

1. Update `graph.py` (7 → 4 nodes)
2. Wire Mem0 into nodes
3. Test end-to-end flow

### Phase 4: Remove Custom Code

1. Delete `session_manager.py`
2. Delete `deduplication.py`
3. Delete `conversation_summarizer.py`
4. Delete `promotion.py`
5. Delete `intent_classifier.py`
6. Delete `entity_extractor.py`

### Phase 5: Add Memory Routes

1. Create `memory_routes.py`
2. Add to FastAPI app
3. Test CRUD operations

### Phase 6: Adapt ZenML

1. Keep document ingestion pipeline
2. Add memory analytics pipeline
3. Remove distillation/promotion pipelines

---

## Docker Compose

```yaml
# docker-compose.yaml (updated)

services:
  # Existing ChromaDB (used by Mem0)
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma
  
  # Your FastAPI app
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MEM0_ENABLED=true
      - CHROMA_HOST=chromadb
    depends_on:
      - chromadb

volumes:
  chroma_data:
```

---

## Comparison Table

| Feature | Custom Implementation | With Mem0 |
|---------|----------------------|-----------|
| **Lines of Code** | ~1,500 | ~100 |
| **LangGraph Nodes** | 7 | 4 |
| **Memory Files** | 9 files | 2 files |
| **Deduplication** | Custom similarity | Built-in |
| **Summarization** | Custom LLM calls | Built-in |
| **Promotion** | Custom salience logic | Automatic |
| **Intent/Entity** | Custom classifiers | Built-in |
| **Temporal Decay** | Manual TTL | Automatic |
| **Memory Types** | 2 (WM, EM) | 3 (User, Agent, Session) |
| **Maintenance** | High | Low |

---

## Final Architecture Diagram

```mermaid
┌─────────────────────────────────────────────────┐
│              FastAPI (API Layer)                 │
│  /chat, /memory/*, /pipelines/*                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│          LangGraph (Orchestration)               │
│  4 nodes: load → query → generate → update      │
└─────────────────────────────────────────────────┘
                      ↓
┌────────────────────┬────────────────────────────┐
│  Mem0 Memory API   │   RAG Document Service     │
│  (conversational)  │   (knowledge base)         │
└────────────────────┴────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│           ChromaDB (Vector Store)                │
│  • Mem0 collections (user/agent/session)        │
│  • Documents collection (RAG)                   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│            ZenML (MLOps)                         │
│  • Document ingestion pipeline                  │
│  • Memory analytics pipeline                    │
└─────────────────────────────────────────────────┘
```

---

## Recommendation

**Use Mem0** if you want:

- ✅ Less code to maintain (93% reduction)
- ✅ Production-ready memory features
- ✅ Faster development
- ✅ Focus on your domain logic (RAG, reranking, providers)

**Keep custom** if you want:

- ⚠️ Full control over every memory operation
- ⚠️ Custom promotion algorithms
- ⚠️ No external dependencies

**Verdict**: Mem0 integration aligns perfectly with your stack while dramatically simplifying memory management.
