# Compliance Pulse Integration & Enhancement Plan

**Date:** 2025-10-25  
**Foundation:** LangGraph v1 + ChromaDB + mem0 + ZenML + FastAPI  
**Target:** Agentic 3PL Compliance Platform (SKU + Lane Focus)

---

## Executive Summary

Transform current RAG foundation into a compliance intelligence platform by:

1. **Reusing** existing architecture (LangGraph, ChromaDB, mem0, ZenML, FastAPI)
2. **Extending** domain models for compliance entities (SKU, Lane, ComplianceEvent)
3. **Adding** compliance-specific tools and data sources
4. **Enhancing** LangGraph agent for compliance reasoning

---

## Current Foundation Assessment

### ✅ What We Have

| Component | Status | Notes |
|-----------|--------|-------|
| **FastAPI** | ✅ Production-ready | `infrastructure/api/main.py` with lifespan management |
| **LangGraph** | ✅ Working | State machine in `application/chat_service/graph.py` |
| **ChromaDB** | ✅ Initialized | Client in `infrastructure/db/chroma_client.py` |
| **mem0** | ✅ Integrated | Service in `application/memory_service/` |
| **ZenML** | ✅ Available | Pipelines in `application/zenml_pipelines/` |
| **Evaluation** | ✅ Built | Metrics service available |
| **Reranking** | ✅ Built | Context fusion service |

### 🔨 What Needs Building

| Component | Priority | Effort |
|-----------|----------|--------|
| Compliance domain models | P0 | 1 day |
| Compliance tools (HTS, OFAC, FDA, etc.) | P0 | 1 week |
| Compliance-aware LangGraph | P0 | 3 days |
| SKU+Lane-specific ChromaDB collections | P0 | 2 days |
| Weekly pulse pipeline | P1 | 2 days |
| Snapshot API endpoints | P0 | 2 days |

---

## Architecture Mapping

### Current → Target Architecture

**Current RAG System** → **Compliance Pulse System**

```bash
FastAPI (/chat, /ingest)  →  FastAPI + Compliance Routes
                               ├─ /snapshot (SKU+Lane)
                               ├─ /pulse/{client_id}/weekly
                               ├─ /ask (compliance Q&A)
                               └─ /admin/ingest/run

LangGraph (chat graph)     →  ComplianceGraph
  load_memories            →    ├─ load_client_context (mem0)
  retrieve_rag             →    ├─ search_hts (tool)
  rerank                   →    ├─ screen_parties (tool)
  generate                 →    ├─ fetch_refusals (tool)
                                ├─ find_rulings (tool)
                                ├─ retrieve_context (ChromaDB)
                                └─ reason_compliance (synthesizer)

ChromaDB (documents)       →  Compliance Collections
                                ├─ hts_notes
                                ├─ rulings
                                ├─ refusal_summaries
                                └─ policy_snippets

mem0 (user sessions)       →  Compliance Memory
                                ├─ client_profiles
                                ├─ sku_watchlists
                                ├─ lane_definitions
                                └─ dismissed_alerts

ZenML (ingestion)          →  Compliance Pipelines
                                ├─ fetch_normalize_index (daily)
                                └─ weekly_pulse (weekly digest)
```

---

## Implementation Phases

### 📦 Phase 0: Foundation Setup (Days 1-3)

**Goal:** Extend domain models and scaffold compliance structure

**New Directory Structure:**

```bash
src/acc_llamaindex/
├── domain/
│   ├── compliance/                  # NEW
│   │   ├── __init__.py
│   │   ├── client_profile.py       # ClientProfile, LaneRef, SkuRef
│   │   ├── compliance_event.py     # ComplianceEvent, Tile, SnapshotResponse
│   │   └── enums.py                # RiskLevel, EventType, TileStatus
│   └── tools/                       # NEW
│       ├── __init__.py
│       ├── hts_tool.py             # USITC HTS API integration
│       ├── sanctions_tool.py        # OFAC/CSL screening
│       ├── refusals_tool.py        # FDA/FSIS refusal data
│       └── rulings_tool.py         # CBP CROSS rulings
├── application/
│   └── compliance_service/          # NEW
│       ├── __init__.py
│       ├── compliance_graph.py     # LangGraph for compliance
│       ├── service.py              # Compliance business logic
│       └── normalizer.py           # External data → ComplianceEvent
└── infrastructure/
    ├── api/
    │   └── routes/
    │       └── compliance_routes.py # NEW - /snapshot, /pulse, /ask
    └── db/
        └── compliance_collections.py # NEW - ChromaDB schemas
```

**Tasks:**

- [ ] Create domain models with Pydantic validation
- [ ] Set up compliance service directory structure
- [ ] Update API models for compliance endpoints
- [ ] Create mock data for testing (10 sample SKUs with lanes)

---

### 🔧 Phase 1: Tools & Data Sources (Days 4-10)
**Goal:** Build compliance-specific tools and connect to external sources

**Tool Architecture:**
Each tool follows LangChain `BaseTool` pattern for easy LangGraph integration.

**Priority Order:**
1. **HTS Tool** (Days 4-5)
   - USITC HTS REST API integration
   - Parse HTS notes, headings, duty rates
   - Cache responses (daily refresh)
   
2. **Sanctions Tool** (Days 6-7)
   - OFAC Consolidated Screening List
   - CSL party name matching
   - Return match confidence + list source
   
3. **Refusals Tool** (Days 8-9)
   - FDA Import Refusals API
   - FSIS Refusal CSV parsing
   - Filter by HTS code, product keywords
   
4. **Rulings Tool** (Day 10)
   - CBP CROSS rulings search
   - Parse ruling PDFs/HTML
   - Extract relevant HTS classifications

**Data Normalization:**
All external data → `ComplianceEvent` with:
- SKU ID, lane ID, HTS code tags
- Source URL, last_updated timestamp
- Risk level classification
- Structured evidence array

---

### 🧠 Phase 2: Compliance LangGraph (Days 11-15)
**Goal:** Build compliance-aware agent with tool orchestration

**ComplianceState Schema:**
```python
class ComplianceState(TypedDict):
    # Input
    client_id: str
    sku_id: str
    lane_id: str
    query: str
    
    # Context from mem0
    client_context: dict
    sku_metadata: dict
    lane_metadata: dict
    
    # Tool results
    hts_results: list
    sanctions_results: list
    refusals_results: list
    rulings_results: list
    
    # RAG context
    rag_context: list
    
    # Output
    snapshot: SnapshotResponse
    reasoning: str
    citations: list
```

**Graph Flow:**
```
Entry → load_client_context (mem0)
     → Router (based on client preferences)
     → [search_hts, screen_sanctions, fetch_refusals, find_rulings] (parallel)
     → retrieve_context (ChromaDB with lane filter)
     → rerank_and_fuse
     → reason_compliance (synthesize snapshot)
     → End
```

**Key Features:**
- Conditional routing based on client threshold preferences (from mem0)
- Parallel tool execution for speed
- Lane-aware filtering of ChromaDB results
- Citation tracking for all claims
- Uncertainty surfacing ("needs broker review")

---

### 📊 Phase 3: ChromaDB Collections (Days 11-13)
**Goal:** Set up compliance-specific vector storage

**Collection Schemas:**

1. **hts_notes** - HTS tariff classifications
   ```python
   metadata = {
       "hts_code": "8517.12.00",
       "chapter": "85",
       "heading": "8517",
       "source_url": "https://hts.usitc.gov/...",
       "last_updated": "2025-01-15",
       "duty_rate": "Free"
   }
   ```

2. **rulings** - CBP classification rulings
   ```python
   metadata = {
       "ruling_number": "N123456",
       "hts_codes": ["8517.12.00"],
       "date": "2024-12-01",
       "source_url": "https://rulings.cbp.gov/..."
   }
   ```

3. **refusal_summaries** - FDA/FSIS refusals
   ```python
   metadata = {
       "source": "FDA",
       "product_description": "...",
       "hts_codes": ["8517.12.00"],
       "country": "CN",
       "refusal_date": "2024-11-15"
   }
   ```

4. **policy_snippets** - Regulatory guidance
   ```python
   metadata = {
       "agency": "FDA|CBP|USTR",
       "topic": "sanctions|health_safety|tariffs",
       "effective_date": "2024-01-01"
   }
   ```

**Retrieval Pattern:**
```python
# Lane-aware retrieval
results = chroma_client.query(
    collection="hts_notes",
    query_text="HTS 8517 cellular phones",
    where={
        "$and": [
            {"hts_code": {"$eq": "8517.12.00"}},
            {"lane_id": {"$in": ["CNSHA-USLAX-ocean", "ANY"]}}
        ]
    },
    n_results=10
)
```

---

### 🚀 Phase 4: API Endpoints (Days 14-16)
**Goal:** Expose compliance endpoints

**New Routes (`compliance_routes.py`):**

```python
@router.post("/snapshot", response_model=SnapshotResponse)
async def snapshot(request: SnapshotRequest):
    """Generate SKU+Lane compliance snapshot."""
    
@router.get("/pulse/{client_id}/weekly", response_model=WeeklyPulseResponse)
async def weekly_pulse(client_id: str):
    """Get weekly digest of compliance changes."""
    
@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Ad-hoc compliance Q&A with context."""
    
@router.post("/admin/ingest/run")
async def trigger_ingestion():
    """Manually trigger compliance data ingestion pipeline."""
```

**Request/Response Models:**
```python
class SnapshotRequest(BaseModel):
    client_id: str
    sku_id: str
    lane_id: str

class SnapshotResponse(BaseModel):
    client_id: str
    sku_id: str
    lane_id: str
    tiles: dict  # {hts: Tile, sanctions: Tile, ...}
    sources: list[dict]
    generated_at: str

class WeeklyPulseResponse(BaseModel):
    client_id: str
    period: str  # "2025-W03"
    lanes: list[dict]  # Grouped by lane
    top_skus: list[dict]  # Top 3 SKUs per lane
    summary_md: str
```

**Authentication:**
Simple API key header for MVP:
```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != config.compliance_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

### ⏰ Phase 5: ZenML Pipelines (Days 17-19)
**Goal:** Automated compliance data ingestion and weekly pulse

**Pipeline 1: `compliance_ingestion_pipeline`**
```python
@pipeline
def compliance_ingestion_pipeline():
    """Daily ingestion of compliance data."""
    # Fetch from external sources
    hts_data = fetch_hts_data()
    ofac_data = fetch_ofac_data()
    fda_data = fetch_fda_data()
    fsis_data = fetch_fsis_data()
    cbp_data = fetch_cbp_rulings()
    
    # Normalize to ComplianceEvent
    events = normalize_compliance_events(
        hts_data, ofac_data, fda_data, fsis_data, cbp_data
    )
    
    # Index to ChromaDB collections
    index_to_chroma(events)
    
    # Update mem0 with new context
    update_client_context(events)
```

**Pipeline 2: `weekly_pulse_pipeline`**
```python
@pipeline
def weekly_pulse_pipeline(client_id: str):
    """Generate weekly delta digest for a client."""
    # Load previous week's snapshot
    last_week = load_previous_snapshot(client_id)
    
    # Generate current snapshot for all SKUs
    current = generate_current_snapshot(client_id)
    
    # Compute delta by SKU + lane
    delta = compute_delta(last_week, current)
    
    # Group by lane, rank by impact
    digest = generate_digest(delta)
    
    # Store for retrieval via API
    save_digest(client_id, digest)
    
    return digest
```

**Scheduling:**
- `compliance_ingestion_pipeline`: Daily at 2 AM UTC
- `weekly_pulse_pipeline`: Sunday at 6 AM UTC per client

---

## Domain Models (Detailed Specifications)

### ClientProfile
```python
from pydantic import BaseModel, Field

class LaneRef(BaseModel):
    lane_id: str = Field(..., description="Unique lane ID (e.g., CNSHA-USLAX-ocean)")
    origin_port: str = Field(..., description="Origin port code")
    destination_port: str = Field(..., description="Destination port code")
    mode: str = Field(..., description="Transport mode: ocean|air|truck")

class SkuRef(BaseModel):
    sku_id: str = Field(..., description="Unique SKU identifier")
    description: str = Field(..., description="Product description")
    hts_code: str = Field(..., description="Harmonized Tariff Schedule code")
    origin_country: str = Field(..., description="ISO country code")
    lanes: list[str] = Field(default_factory=list, description="Associated lane IDs")

class ClientProfile(BaseModel):
    id: str
    name: str
    contact: dict = Field(..., description="Contact info: {email: str, phone: str}")
    lanes: list[LaneRef] = Field(default_factory=list)
    watch_skus: list[SkuRef] = Field(default_factory=list)
    preferences: dict = Field(
        default_factory=dict,
        description="Client preferences: {duty_delta_threshold: 0.01, ...}"
    )
```

### ComplianceEvent

```python
from enum import Enum
from datetime import datetime

class EventType(str, Enum):
    HTS = "HTS"
    FTA = "FTA"
    SANCTIONS = "SANCTIONS"
    HEALTH_SAFETY = "HEALTH_SAFETY"
    RULING = "RULING"

class RiskLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"

class Evidence(BaseModel):
    source: str
    url: str
    snippet: str
    last_updated: str

class ComplianceEvent(BaseModel):
    id: str
    client_id: str
    sku_id: str
    lane_id: str
    type: EventType
    risk_level: RiskLevel
    summary_md: str = Field(..., description="Markdown summary of the event")
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
class TileStatus(str, Enum):
    CLEAR = "clear"
    ATTENTION = "attention"
    ACTION = "action"

class Tile(BaseModel):
    status: TileStatus
    headline: str = Field(..., description="Short headline (< 80 chars)")
    details_md: str = Field(..., description="Markdown details")
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SnapshotResponse(BaseModel):
    client_id: str
    sku_id: str
    lane_id: str
    tiles: dict = Field(..., description="Dict of {tile_name: Tile}")
    sources: list[Evidence] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

---

## Testing Strategy

### Unit Tests
```python
# tests/domain/test_compliance_models.py
def test_client_profile_validation():
    """Test ClientProfile model validation."""
    
def test_compliance_event_creation():
    """Test ComplianceEvent creation with evidence."""

# tests/domain/tools/test_hts_tool.py
@pytest.mark.integration
def test_hts_tool_search():
    """Test HTS tool with real API (mocked)."""
```

### Integration Tests
```python
# tests/application/test_compliance_service.py
@pytest.mark.integration
def test_snapshot_generation_end_to_end():
    """Test full snapshot generation with tools."""
    
def test_weekly_pulse_delta_computation():
    """Test weekly delta computation logic."""
```

### API Tests
```python
# tests/infrastructure/api/test_compliance_routes.py
def test_snapshot_endpoint():
    """Test /snapshot endpoint returns valid response."""
    
def test_ask_endpoint_with_context():
    """Test /ask endpoint with compliance context."""
```

---

## Success Metrics (MVP)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Snapshot latency (p95) | < 5 seconds | API response time |
| SKU coverage | 30-50 SKUs | Active SKUs in system |
| Data accuracy | > 95% | Manual validation sample |
| Tool success rate | > 90% | Tool execution success/total |
| Weekly digest delivery | 100% on-time | Pipeline execution logs |
| Citation completeness | 100% | All tiles have sources |

---

## Dependencies & Environment Setup

### External API Access
- USITC HTS REST API (public, no key required)
- Treasury OFAC CSL (public, no key required)
- FDA Import Refusals API (public, no key required)
- FSIS Refusal CSV (public download)
- CBP CROSS Rulings (public search)

### Environment Variables (`.env` additions)
```bash
# Compliance Platform
COMPLIANCE_API_KEY="your-secure-key-here"
COMPLIANCE_HTS_API_URL="https://hts.usitc.gov/api"
COMPLIANCE_OFAC_URL="https://api.trade.gov/consolidated_screening_list/search"
COMPLIANCE_FDA_REFUSALS_URL="https://www.accessdata.fda.gov/scripts/importrefusals/"
COMPLIANCE_FSIS_REFUSALS_URL="https://www.fsis.usda.gov/inspection/import-export"
COMPLIANCE_CBP_CROSS_URL="https://rulings.cbp.gov"

# Feature Flags
COMPLIANCE_ENABLE_WEEKLY_PULSE=true
COMPLIANCE_ENABLE_SLACK_NOTIFICATIONS=false
```

### Package Dependencies (already in `pyproject.toml`)
- ✅ LangChain, LangGraph
- ✅ ChromaDB
- ✅ mem0ai
- ✅ ZenML
- ✅ FastAPI
- ✅ Pydantic v2

**New dependencies needed:**
```toml
dependencies = [
    # ... existing ...
    "httpx>=0.27.0",      # For external API calls
    "beautifulsoup4",      # For HTML parsing (CROSS rulings)
    "tabula-py",           # For PDF table extraction (optional)
]
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| External API rate limits | High | Daily batch + caching; fallback to last-known data |
| Data quality/freshness | Medium | Validation layer; staleness warnings in UI |
| Tool failures | Medium | Graceful degradation; partial snapshots with warnings |
| Memory growth (ChromaDB) | Low | Retention policy; archive old data quarterly |
| Complex lane logic | Medium | Start with 1-2 lanes; iterate; clear docs |
| HTS code changes | High | Version tracking; diff alerts in digest |

---

## Implementation Timeline

### Week 1 (Days 1-5)
- ✅ Phase 0: Domain models + directory structure
- ✅ Phase 1: HTS Tool + Sanctions Tool

### Week 2 (Days 6-10)
- ✅ Phase 1: Refusals Tool + Rulings Tool
- ✅ Phase 3: ChromaDB collections setup

### Week 3 (Days 11-16)
- ✅ Phase 2: ComplianceGraph implementation
- ✅ Phase 4: API endpoints

### Week 4 (Days 17-20)
- ✅ Phase 5: ZenML pipelines
- ✅ Testing + bug fixes
- ✅ Documentation
- 🎯 **MVP Demo**: End-to-end snapshot + weekly digest

---

## Next Immediate Actions

1. **Review & Approve** this plan with stakeholders
2. **Create feature branch**: `feature/compliance-pulse-mvp`
3. **Set up project board** with tasks from each phase
4. **Gather sample data**: 10 real SKUs with HTS codes + lanes
5. **Start Phase 0**: Create domain models (Day 1)

---

## Questions for Product/Stakeholders

1. **Data source priority**: Which 2-3 sources for MVP? (Recommend: HTS + OFAC + FDA)
2. **Sample SKU data**: Can we get 10-30 real SKUs with HTS codes and lanes?
3. **Pilot client**: Who is the target client? How many SKUs/lanes?
4. **Digest delivery**: Email, Slack, or JSON API for MVP?
5. **Authentication**: Simple API key sufficient, or need OAuth?
6. **Frequency**: Daily ingestion acceptable, or need real-time?

---

**End of Integration Plan**
