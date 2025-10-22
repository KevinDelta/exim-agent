# Memory-First Integration Plan for ACC LlamaIndex

**Goal**: Integrate anthropomorphic memory concepts into our existing LangChain v1 RAG system to improve conversation continuity, context management, and retrieval quality.

**Scope**: Both RAG queries and multi-turn chat conversations with persistent memory.

---

## Current Architecture Assessment

### What We Have ✅
- **Vector Store**: ChromaDB for document embeddings
- **Chat Service**: LangChain v1 agents with conversation history
- **Document Ingestion**: Chunking, embedding, and storage pipeline
- **Reranking**: Cross-encoder reranking service (just implemented)
- **Evaluation**: Metrics for RAG quality assessment
- **LLM Provider**: Abstracted provider layer (OpenAI, Anthropic, Groq)
- **API Layer**: FastAPI with async endpoints

### What We Don't Have ❌
- **Neo4j**: No knowledge graph database
- **Redis**: No hot cache layer
- **Memory Broker**: No dedicated memory service
- **Multi-tier Memory**: No WM/EM/SM separation
- **Entity Resolution**: No entity normalization or linking
- **BM25 Pre-filter**: Direct vector search only
- **Session Management**: Conversation history stored in-memory only

---

## Memory Framework Adaptation

### Core Principles We CAN Adopt ✅

1. **LangGraph State Machine** - Explicit state management for memory operations
2. **Memory Tiering** - Separate hot/warm/cold memory
3. **Compression & Distillation** - Summarize conversations into facts
4. **Entity-Centric Retrieval** - Link queries to entities
5. **Provenance Tracking** - Source attribution for all facts
6. **Salience Scoring** - Track which memories are actually useful
7. **Sparse Recall** - Only retrieve what's needed for current intent
8. **Progressive Context** - Start with minimal context, add as needed

### Concepts That DON'T FIT ❌

#### 1. **Neo4j Knowledge Graph** (Not Feasible Initially)
**Why**: 
- Requires completely new infrastructure
- Significant operational complexity (another database to manage)
- Entity resolution/normalization is a major project
- Our supply chain domain has complex entity relationships that need careful modeling

**Alternative**: 
- Use ChromaDB metadata filtering with structured tags
- Store entity relationships as metadata: `{"entity_type": "shipper", "entity_id": "SHIP-123", "related_ports": ["DUR", "LAG"]}`
- Consider graph later if entity-centric queries become dominant

#### 2. **Memory Broker Microservice** (Over-Engineering)
**Why**:
- Adds deployment complexity for marginal benefit
- Our scale doesn't require separate service yet
- Increases latency with network hop

**Alternative**:
- Memory service as a Python module within the app
- Direct database access (ChromaDB + optional Redis)
- Can extract to microservice later if needed

#### 3. **BM25 Pre-filtering** (Premature Optimization)
**Why**:
- ChromaDB vector search is already fast (<100ms)
- BM25 index adds maintenance burden
- No evidence we have recall problems requiring pre-filter

**Alternative**:
- Use ChromaDB metadata filtering (already supported)
- Monitor retrieval latency; add BM25 only if p95 > 500ms

---

## Proposed Memory Architecture

### Three-Tier Memory System

```
┌─────────────────────────────────────────────────────────┐
│                    WORKING MEMORY (WM)                   │
│  Current conversation context (last 3-5 turns)          │
│  Storage: In-memory Python dict per session             │
│  TTL: Session lifetime (~30 min)                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   EPISODIC MEMORY (EM)                   │
│  Distilled conversation summaries & recent facts        │
│  Storage: ChromaDB collection "episodic_memory"         │
│  TTL: 7-14 days, promoted to SM if frequently accessed  │
│  Metadata: {session_id, user_id, timestamp, salience}   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   SEMANTIC MEMORY (SM)                   │
│  Long-term knowledge from documents & promoted facts    │
│  Storage: ChromaDB collection "documents" (existing)    │
│  TTL: Permanent (updated, not deleted)                  │
│  Metadata: {source, entity_tags, verified, salience}    │
└─────────────────────────────────────────────────────────┘
```

### Memory Flow (LangGraph State Machine)

```python
from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict, Any

class MemoryState(TypedDict):
    user_query: str
    session_id: str
    wm_context: List[Dict]  # Working memory (last N turns)
    intent: str
    entities: List[Dict]
    em_results: List[Dict]  # Episodic memory results
    sm_results: List[Dict]  # Semantic memory results
    reranked_context: List[Dict]
    response: str
    citations: List[Dict]
    should_distill: bool

# Define nodes
def load_working_memory(state: MemoryState) -> MemoryState:
    """Load last N conversation turns from session"""
    # Fast, in-memory retrieval
    ...

def classify_intent(state: MemoryState) -> MemoryState:
    """Detect user intent and extract entities"""
    # LLM-based classification
    ...

def query_episodic_memory(state: MemoryState) -> MemoryState:
    """Query EM collection filtered by session + salience"""
    # ChromaDB query with session context
    ...

def query_semantic_memory(state: MemoryState) -> MemoryState:
    """Query SM collection filtered by entities + intent"""
    # ChromaDB query with metadata filters
    ...

def rerank_results(state: MemoryState) -> MemoryState:
    """Combine and rerank EM + SM results"""
    # Use existing reranking service
    ...

def generate_response(state: MemoryState) -> MemoryState:
    """Generate answer with citations"""
    # LLM generation with structured context
    ...

def update_working_memory(state: MemoryState) -> MemoryState:
    """Update WM and check if distillation needed"""
    # Update session state, schedule distillation if needed
    ...

# Build graph
graph = StateGraph(MemoryState)
graph.add_node("load_wm", load_working_memory)
graph.add_node("classify", classify_intent)
graph.add_node("query_em", query_episodic_memory)
graph.add_node("query_sm", query_semantic_memory)
graph.add_node("rerank", rerank_results)
graph.add_node("generate", generate_response)
graph.add_node("update_wm", update_working_memory)

# Define edges (flow)
graph.set_entry_point("load_wm")
graph.add_edge("load_wm", "classify")
graph.add_edge("classify", "query_em")
graph.add_edge("classify", "query_sm")  # Parallel execution
graph.add_edge("query_em", "rerank")
graph.add_edge("query_sm", "rerank")
graph.add_edge("rerank", "generate")
graph.add_edge("generate", "update_wm")
graph.set_finish_point("update_wm")

memory_agent = graph.compile()
```

**Key Benefits of LangGraph**:
- Explicit state management (all memory tiers visible)
- Parallel execution (EM and SM queries run concurrently)
- Easy debugging (inspect state at each node)
- Conditional routing (can skip nodes based on intent)
- Persistent state (can checkpoint for long conversations)

---

## Phase 1: Foundation & LangGraph Migration (Week 1-3)

### Goal
Migrate to LangGraph state machine and establish basic three-tier memory without breaking existing functionality.

### Tasks

#### 1.0 LangGraph Migration
**Add to**: `application/chat_service/`

**New Files**:
- `graph.py` - LangGraph state machine definition
  - Define `MemoryState` TypedDict with all state fields
  - Create node functions for each step (load_wm, classify, query_em, query_sm, etc.)
  - Build graph with proper edge connections
  - Compile graph into executable agent

**Migration Steps**:
1. Install LangGraph: Add `langgraph>=0.2.62` to pyproject.toml
2. Create parallel implementation (keep existing agents working)
3. Define `MemoryState` schema with all required fields
4. Implement node functions (can reuse existing logic)
5. Wire up graph edges (parallel execution for EM/SM queries)
6. Add feature flag to toggle between agents and graph
7. Test graph execution matches agent behavior
8. Gradual rollout (10% → 50% → 100%)

**Key Changes**:
- Replace LangChain agent's tool-calling loop with explicit graph flow
- State is passed between nodes (no hidden context)
- Can inspect/debug state at any point
- Parallel execution improves latency
- Checkpointing enables conversation resume

**Deliverables**:
- ✅ LangGraph state machine operational
- ✅ Feature flag for agent vs graph execution
- ✅ Tests pass for both modes
- ✅ Performance parity or better vs agents

**Done-When**:
- Graph produces same results as agents
- Can toggle between modes via feature flag
- Latency is same or better (parallel execution helps)
- All existing tests pass with graph enabled

#### 1.1 Session Management
**Add to**: `application/chat_service/`

**New Files**:
- `session_manager.py` - Manage in-memory conversation state
  - Store last N turns per session
  - Simple dict: `{session_id: {turns: [], created_at, last_accessed}}`
  - TTL cleanup every 5 minutes
  - Max 100 active sessions (LRU eviction)

**Integration**:
- Modify `chat_service/service.py` to use session manager
- Add `session_id` parameter to chat endpoint
- Return `session_id` in response for client continuity

#### 1.2 Episodic Memory Collection
**Add to**: `infrastructure/db/`

**Tasks**:
- Create new ChromaDB collection `episodic_memory`
- Schema:
  ```python
  {
    "id": "uuid",
    "text": "distilled_fact_or_summary",
    "embedding": [...],
    "metadata": {
      "session_id": "sess_123",
      "user_id": "user_456",  # if multi-tenant
      "timestamp": "2025-01-18T10:00:00Z",
      "salience": 0.5,        # 0-1, increases with use
      "entity_tags": ["shipper:SHIP-123", "port:DUR"],
      "source_turns": [1, 2, 3],  # which WM turns this came from
      "ttl_date": "2025-02-01"
    }
  }
  ```
- Add methods to `chroma_client.py`:
  - `get_episodic_collection()`
  - `query_episodic(session_id, query, k=5)`
  - `write_episodic(items)`

#### 1.3 Enhanced Document Metadata
**Modify**: `application/ingest_documents_service/`

**Tasks**:
- Update document ingestion to add structured metadata:
  ```python
  {
    "entity_tags": ["regulation:PVOC", "country:KE"],
    "document_type": "compliance_guide",
    "verified": True,
    "salience": 0.0,  # Will increase with use
    "provenance": {
      "source_url": "...",
      "ingested_at": "...",
      "version": "v3",
      "hash": "sha256..."
    }
  }
  ```
- Create entity extraction helper (simple LLM function call)
- Add entity tagging to chunking pipeline

**Deliverables**:
- ✅ Session manager with 100 concurrent sessions
- ✅ Episodic memory collection operational
- ✅ Documents have entity tags and provenance
- ✅ Existing RAG still works unchanged

**Done-When**:
- Can store/retrieve session state
- Can write/query episodic facts
- All ingested docs have provenance metadata
- Tests pass for backward compatibility

---

## Phase 2: Intelligent Retrieval (Week 3-4)

### Goal
Implement sparse, intent-driven memory recall across all three tiers.

### Tasks

#### 2.1 Memory Service Module
**Add to**: `application/memory_service/`

**New Files**:
- `service.py` - Main memory orchestrator
  - `recall(query, session_id, intent, k_em=5, k_sm=10)`
  - Orchestrates WM + EM + SM retrieval
  - Combines and deduplicates results
  - Returns ranked list with provenance

- `intent_classifier.py` - Simple intent detection
  - LLM function call: `classify_intent(query) -> {intent, confidence, entities}`
  - Intents: `quote_request`, `compliance_query`, `shipment_tracking`, `general`
  - Cache results for 1 hour (avoid repeated LLM calls)

- `entity_extractor.py` - Entity recognition
  - Regex patterns for common entities (shipment IDs, ports, countries)
  - LLM fallback for complex entities
  - Return: `[{text, type, canonical_id}]`

**Intent Profiles** (YAML config):
```yaml
# config/memory_profiles.yaml
intents:
  quote_request:
    k_em: 5
    k_sm: 12
    entity_types: [shipper, port, incoterm, commodity]
    prefer_recent: True
    
  compliance_query:
    k_em: 3
    k_sm: 15
    entity_types: [country, regulation, hs_code]
    prefer_verified: True
    
  general:
    k_em: 5
    k_sm: 8
    entity_types: []
    prefer_recent: False
```

#### 2.2 Sparse Retrieval Strategy
**Modify**: `application/chat_service/service.py`

**Changes**:
- Replace simple vector search with memory service call
- Add intent classification before retrieval
- Filter ChromaDB by:
  - Intent tags
  - Entity tags (when detected)
  - Verified status (for compliance queries)
  - Salience score (prefer frequently-used items)

**Example ChromaDB Query**:
```python
# Instead of:
docs = vector_store.similarity_search(query, k=20)

# Do:
intent_info = intent_classifier.classify(query)
entities = entity_extractor.extract(query)

# Query EM with session context
em_results = chroma_client.query_episodic(
    collection="episodic_memory",
    query_embedding=embed(query),
    where={
        "session_id": session_id,
        "salience": {"$gte": 0.3}
    },
    n_results=5
)

# Query SM with intent + entity filters
sm_results = chroma_client.query(
    collection="documents",
    query_embedding=embed(query),
    where={
        "$and": [
            {"entity_tags": {"$in": [e.canonical_id for e in entities]}},
            {"intent": intent_info.intent},
            {"verified": True}  # If compliance query
        ]
    },
    n_results=12
)

# Combine + dedupe + rerank
combined = memory_service.merge_results(em_results, sm_results)
final = reranking_service.rerank(query, combined, top_k=8)
```

#### 2.3 Salience Tracking
**Add to**: `application/memory_service/`

**New File**: `salience_tracker.py`
- Track which memories are actually cited in responses
- Increment salience when memory is used: `salience = min(1.0, salience + 0.1)`
- Batch update ChromaDB every 50 citations
- Decay salience weekly: `salience *= 0.95` (prevents stale items from dominating)

**Integration**:
- After generating response, identify which retrieved docs were cited
- Update salience for those items
- Log salience changes for analytics

**Deliverables**:
- ✅ Intent classification working (>80% accuracy on test set)
- ✅ Entity extraction for common types
- ✅ Sparse retrieval reduces over-fetch by 40%+
- ✅ Salience tracking operational

**Done-When**:
- Retrieval filtered by intent + entities
- Precision@k improves by 10%+ on evals
- Over-fetch ratio (unused context) drops by 40%
- Salience scores update correctly

---

## Phase 3: Compression & Distillation (Week 5-6)

### Goal
Automatically compress conversations into reusable facts, reducing context size.

### Tasks

#### 3.1 Conversation Summarizer
**Add to**: `application/memory_service/`

**New File**: `conversation_summarizer.py`
- Triggered after every N turns (N=5) or on session timeout
- LLM chain: `summarize_session(turns) -> bullet_facts`
- Prompt:
  ```
  Extract 3-5 key facts learned in this conversation.
  Format as atomic statements with entities clearly identified.
  
  Example:
  - User is requesting quote for electronics shipment to Durban (Port: DUR)
  - DDP incoterm preferred, PVOC compliance required (Regulation: KE-PVOC)
  - Shipper is based in Shenzhen (Entity: SHIP-123)
  ```
- Each fact gets:
  - Embedding
  - Entity tags extracted
  - Initial salience = 0.5
  - TTL = 14 days

#### 3.2 Fact Deduplication
**Add to**: `memory_service/deduplication.py`

**Logic**:
- Before writing new EM fact, check for similar existing facts
- Similarity threshold: cosine > 0.92
- If duplicate found:
  - Don't write new fact
  - Increment salience of existing fact
  - Update `last_seen` timestamp
  - Extend TTL by 7 days

**Why Important**:
- Prevents memory bloat
- Reinforces important facts (via salience)
- Reduces retrieval noise

#### 3.3 EM → SM Promotion
**Add to**: `memory_service/promotion.py`

**Promotion Rules**:
```python
def should_promote(em_fact):
    return (
        em_fact.salience >= 0.8 and
        em_fact.citation_count >= 5 and
        em_fact.age_days >= 7 and
        em_fact.verified == True  # Manual or automated verification
    )
```

**Promotion Process**:
1. Check promotion rules weekly (background job)
2. Mark EM facts for promotion
3. Optional: Human review queue for high-value facts
4. Copy to SM collection with enriched metadata
5. Keep EM version (don't delete - continuity)

**Background Job**:
- Run nightly
- Process all EM facts older than 7 days
- Promote qualifying facts
- Delete EM facts past TTL

#### 3.4 Atomic Fact Storage
**Modify**: EM write logic

**Change**:
Instead of storing multi-sentence summaries, break into atomic facts:

**Before**:
```
"User requested quote for electronics to Durban under DDP. 
PVOC compliance is required. Shipper is in Shenzhen."
```

**After** (3 separate EM entries):
```
1. "Quote request: electronics shipment to Durban (Port: DUR), incoterm: DDP"
2. "PVOC compliance required for Kenya imports (Regulation: KE-PVOC)"
3. "Shipper location: Shenzhen, China (Entity: SHIP-123)"
```

**Benefits**:
- More precise retrieval (match specific fact, not whole summary)
- Better deduplication (can match individual facts)
- Easier promotion (promote single fact, not entire summary)

**Deliverables**:
- ✅ Conversation summaries generated automatically
- ✅ Facts are atomic and entity-tagged
- ✅ Deduplication prevents memory bloat
- ✅ Promotion pipeline operational

**Done-When**:
- Context size reduced by 30%+ (fewer tokens per query)
- No duplicate facts in EM (>95% dedupe rate)
- High-value facts automatically promoted to SM
- Groundedness maintained (citations still work)

---

## Phase 4: Integration & Optimization (Week 7-8)

### Goal
Polish the system, add observability, and optimize performance.

### Tasks

#### 4.1 Unified Memory API
**Add to**: `infrastructure/api/main.py`

**New Endpoints**:
```python
POST /memory/recall
{
  "query": "What PVOC docs are needed?",
  "session_id": "sess_123",
  "intent": "compliance_query",  # optional, will auto-detect
  "k": 10
}
Response: {
  "results": [
    {
      "text": "...",
      "source": "EM|SM",
      "salience": 0.8,
      "provenance": {...},
      "entities": [...]
    }
  ],
  "query_metadata": {
    "intent": "compliance_query",
    "entities_detected": [...],
    "retrieval_ms": 120
  }
}

POST /memory/distill
{
  "session_id": "sess_123",
  "force": false  # If true, summarize immediately
}
Response: {
  "facts_created": 4,
  "duplicates_merged": 1
}

GET /memory/session/{session_id}
Response: {
  "wm_turns": 5,
  "em_facts": 12,
  "last_distilled": "2025-01-18T10:00:00Z"
}

POST /memory/promote/{fact_id}
# Manual promotion trigger (admin use)

DELETE /memory/session/{session_id}
# Clear session (privacy/testing)
```

#### 4.2 Observability & Metrics
**Add to**: `application/memory_service/metrics.py`

**Track**:
- **Retrieval Metrics**:
  - Latency by tier (WM/EM/SM)
  - Cache hit rate (how often EM satisfies query)
  - Over-fetch ratio (unused context)
  
- **Memory Metrics**:
  - Total items (WM/EM/SM)
  - Promotion rate (EM → SM per week)
  - Salience distribution
  - TTL expiration rate
  
- **Quality Metrics**:
  - Citation rate (% responses with 2+ sources)
  - Precision@k (on eval set)
  - Deduplication rate

**Logging**:
- Structure logs for easy querying:
  ```python
  logger.info(
      "memory_recall",
      extra={
          "session_id": session_id,
          "intent": intent,
          "entities": entities,
          "em_hits": 3,
          "sm_hits": 8,
          "latency_ms": 145,
          "over_fetch_ratio": 0.22
      }
  )
  ```

**Dashboard** (simple):
- Add metrics endpoint: `GET /metrics`
- Return JSON with key stats
- Frontend can be built later (or use Grafana)

#### 4.3 Configuration Management
**Add**: `config/memory_config.py`

**Settings**:
```python
class MemorySettings(BaseSettings):
    # Working Memory
    wm_max_turns: int = 10
    wm_session_ttl_minutes: int = 30
    wm_max_sessions: int = 100
    
    # Episodic Memory
    em_collection_name: str = "episodic_memory"
    em_ttl_days: int = 14
    em_distill_every_n_turns: int = 5
    em_k_default: int = 5
    em_salience_threshold: float = 0.3
    
    # Semantic Memory
    sm_collection_name: str = "documents"
    sm_k_default: int = 10
    sm_verified_only: bool = False  # For compliance queries
    
    # Promotion
    promotion_salience_threshold: float = 0.8
    promotion_citation_count: int = 5
    promotion_age_days: int = 7
    
    # Intent Profiles
    intent_config_path: str = "config/memory_profiles.yaml"
    
    # Performance
    enable_em_cache: bool = True
    max_context_tokens: int = 8000
    rerank_enabled: bool = True  # Use existing reranking service
```

#### 4.4 Testing & Validation
**Add**: `tests/memory/`

**Test Suites**:
1. **Unit Tests**:
   - Session manager (create, expire, evict)
   - Entity extraction (accuracy)
   - Intent classification (accuracy)
   - Deduplication (no false positives)
   - Salience updates (correct math)

2. **Integration Tests**:
   - End-to-end memory flow (WM → EM → SM)
   - Distillation pipeline
   - Promotion pipeline
   - API endpoints

3. **Performance Tests**:
   - Retrieval latency (p50, p95, p99)
   - Memory growth rate (items/day)
   - Deduplication efficiency

4. **Quality Tests** (using eval set):
   - Precision@k with memory system
   - Citation rate
   - Over-fetch ratio
   - Compare vs baseline (no memory system)

**Deliverables**:
- ✅ All endpoints operational
- ✅ Metrics tracked and logged
- ✅ Configuration externalized
- ✅ Tests passing (>90% coverage)

**Done-When**:
- API docs updated with memory endpoints
- Metrics visible via `/metrics` endpoint
- All tests green
- Performance benchmarks meet targets

---

## What We're NOT Doing (And Why)

### 1. ❌ Neo4j Knowledge Graph
**Reason**: 
- High operational complexity (new DB to maintain)
- Entity resolution is a major AI project itself
- ChromaDB metadata filtering achieves 80% of the benefit
- Can add later if entity-centric queries become dominant

**Mitigation**:
- Use structured metadata in ChromaDB as poor man's graph
- Store entity relationships as JSON: `{"related_entities": ["SHIP-123", "PORT-DUR"]}`

### 2. ❌ Memory Broker Microservice
**Reason**:
- Over-engineering for current scale
- Adds latency (network hop)
- Complicates deployment

**Mitigation**:
- Keep memory service as Python module
- Can extract later if scale demands

### 3. ❌ BM25 Pre-filter
**Reason**:
- ChromaDB is already fast (<100ms)
- Adds complexity (maintain separate index)
- No evidence we have recall problems

**Mitigation**:
- Use ChromaDB's built-in metadata filtering
- Monitor latency; add BM25 only if needed

### 4. ❌ Redis Hot Cache
**Reason**:
- Another dependency to manage
- In-memory Python dict works for 100 sessions
- Can add later if session count grows

**Mitigation**:
- Use simple Python dict for WM
- Persist critical sessions to EM on timeout

### 5. ❌ Streaming Retrieval
**Reason**:
- Complex implementation
- Marginal latency benefit (retrieval is already fast)
- Can add later if first-token latency is critical

**Mitigation**:
- Focus on reducing context size (compression)
- Optimize retrieval filters (intent + entities)

---

## Success Metrics

### Must Achieve (Phase 1-4)
- ✅ **Context Reduction**: 30%+ fewer tokens per query with same quality
- ✅ **Precision Improvement**: Precision@k up by 10%+ on eval set
- ✅ **Citation Rate**: 80%+ responses have 2+ distinct sources
- ✅ **Over-fetch Reduction**: 40%+ drop in unused context
- ✅ **Latency**: p95 retrieval < 300ms (WM+EM+SM+rerank)
- ✅ **Memory Growth**: Sublinear (deduplication working)
- ✅ **Session Continuity**: Multi-turn conversations maintain context

### Nice-to-Have (Future)
- ✅ **Hot Hit Rate**: 60%+ queries satisfied by EM alone
- ✅ **Promotion Rate**: 5-10% of EM facts promoted weekly
- ✅ **Zero Duplicates**: >98% deduplication rate
- ✅ **Self-Healing**: Salience decay removes stale facts automatically

---

## Timeline & Effort

### Phase 1: Foundation & LangGraph Migration (3 weeks)
- **Effort**: 90-120 hours (includes 30-40 hours for LangGraph migration)
- **Risk**: Medium (architectural change but parallel implementation mitigates)
- **Dependencies**: None

### Phase 2: Intelligent Retrieval (2 weeks)
- **Effort**: 60-80 hours
- **Risk**: Medium (modifies retrieval logic)
- **Dependencies**: Phase 1 complete

### Phase 3: Compression & Distillation (2 weeks)
- **Effort**: 50-70 hours
- **Risk**: Medium (background jobs, LLM accuracy)
- **Dependencies**: Phase 1 complete

### Phase 4: Integration & Optimization (2 weeks)
- **Effort**: 40-60 hours
- **Risk**: Low (polish, testing)
- **Dependencies**: Phases 1-3 complete

**Total**: 9 weeks, 240-330 hours

**LangGraph Migration Impact**: +1 week, +30-40 hours
- Benefit: Explicit state management, parallel execution, better debugging
- Risk: Managed via feature flag and gradual rollout
- Payoff: Enables advanced memory patterns (checkpointing, branching, conditional flows)

---

## Migration Strategy

### Backward Compatibility
- All existing endpoints continue to work
- Old `chat` endpoint uses memory system transparently
- No client changes required

### Feature Flags
```python
# config.py
use_langgraph: bool = True  # Toggle LangGraph vs LangChain agents
enable_memory_system: bool = True  # Toggle entire memory system
enable_em_distillation: bool = True
enable_sm_promotion: bool = True
enable_intent_classification: bool = True
```

### Rollout Plan
1. **Week 1-3**: Deploy Phase 1 (LangGraph + memory foundation)
   - LangGraph: Internal testing with feature flag (10% traffic)
   - Memory system: Disabled initially
2. **Week 4**: Enable LangGraph for all internal users (100% internal)
3. **Week 5**: Deploy Phases 2-3, enable memory for beta users (50% traffic)
4. **Week 6**: Full rollout of memory system (100% traffic)
5. **Week 7-9**: Deploy Phase 4, optimization and monitoring

### Rollback Plan
- Disable feature flags → system reverts to baseline
- EM/SM collections are additive (deleting them doesn't break anything)
- Session manager can be bypassed

---

## Open Questions & Decisions Needed

### 1. Multi-Tenancy
**Question**: Do different users/orgs need isolated memory?

**Options**:
- A) Single shared memory (current approach)
- B) Per-user EM + shared SM
- C) Fully isolated (user_id in all queries)

**Recommendation**: Start with A, add B if needed

### 2. Entity Canonicalization
**Question**: How to normalize entities? (e.g., "Durban" vs "DUR" vs "Durban Port")

**Options**:
- A) Simple string matching + LLM fallback
- B) Maintain entity synonym table
- C) Full entity resolution system (Neo4j)

**Recommendation**: A for now, B if conflicts arise

### 3. Fact Verification
**Question**: How to verify facts before promoting EM → SM?

**Options**:
- A) Auto-promote if high salience (trust the system)
- B) Manual review queue (admin approves)
- C) LLM-based verification (check against sources)

**Recommendation**: A for non-critical, B for compliance facts

### 4. Privacy & Data Retention
**Question**: How long to keep conversation data?

**Options**:
- A) Delete WM after session (privacy-first)
- B) Delete EM after TTL (14 days)
- C) Keep everything (analytics)

**Recommendation**: A + B (can add opt-in logging later)

---

## Conclusion

This plan adapts the memory-first punch list to our architecture by:

✅ **Adopting LangGraph**: Explicit state management for memory operations
✅ **Keeping what works**: ChromaDB, FastAPI, existing LLM providers
✅ **Adding what's practical**: Three-tier memory, intent-driven retrieval, distillation
✅ **Skipping what doesn't fit**: Neo4j, microservices, BM25, Redis (for now)

The result is a **pragmatic, incremental** approach that:
- Migrates to LangGraph for better state management and debugging
- Improves context management (30%+ token reduction)
- Enhances retrieval quality (10%+ precision gain)
- Maintains conversation continuity (session memory)
- Stays within our technical constraints (no new databases except LangGraph state)

**Next Steps**:
1. Review and approve this plan
2. Set up eval harness (golden test set)
3. Start Phase 1 implementation
4. Measure baseline metrics before changes
5. Iterate based on real performance data

**Key Risks**:
- **LangGraph migration**: Architectural change (mitigated by feature flag + gradual rollout)
- **LLM-based distillation accuracy**: Needs monitoring and prompt tuning
- **Deduplication false positives**: Needs testing with diverse data
- **Memory growth rate**: Needs salience decay and TTL enforcement

**Success Criteria**:
- LangGraph migration complete with no regressions
- All must-achieve metrics hit
- No regression in answer quality
- System maintains <300ms p95 latency (or better with parallel execution)
