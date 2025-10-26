# Compliance Pulse Implementation Roadmap

**Date:** 2025-10-25  
**Sprint Duration:** 4 weeks (20 working days)  
**Team:** Backend-focused (frontend deferred to V1)

---

## Week 1: Foundation & Tools (Days 1-5)

### Day 1: Domain Models Setup

**Branch:** `feature/compliance-domain-models`

**Tasks:**

- [ ] Create `src/exim_agent/domain/compliance/` directory
- [ ] Implement `enums.py`:
  - `EventType`, `RiskLevel`, `TileStatus`
- [ ] Implement `client_profile.py`:
  - `ClientProfile`, `LaneRef`, `SkuRef` with Pydantic validation
- [ ] Implement `compliance_event.py`:
  - `ComplianceEvent`, `Tile`, `SnapshotResponse`, `Evidence`
- [ ] Write unit tests for model validation
- [ ] Update `pyproject.toml` dependencies (httpx, beautifulsoup4)

**Deliverable:** Validated domain models with 100% test coverage

---

### Day 2: Tools Infrastructure

**Branch:** `feature/compliance-tools-base`

**Tasks:**

- [ ] Create `src/exim_agent/domain/tools/` directory
- [ ] Create base `ComplianceTool` abstract class extending LangChain `BaseTool`
- [ ] Add error handling and retry logic utilities
- [ ] Create tool registry pattern for dynamic tool loading
- [ ] Add caching layer for external API responses
- [ ] Write tool integration test framework

**Deliverable:** Reusable tool infrastructure

---

### Day 3: HTS Tool Implementation

**Branch:** `feature/hts-tool`

**Tasks:**
- [ ] Implement `hts_tool.py`:
  - USITC HTS REST API client
  - HTS code lookup and validation
  - Parse HTS notes, headings, duty rates
  - Error handling for invalid codes
- [ ] Add response caching (24-hour TTL)
- [ ] Create `HTSResponse` model
- [ ] Write integration tests with mocked API
- [ ] Document HTS API endpoints and rate limits

**API Example:**
```python
from exim_agent.domain.tools.hts_tool import HTSTool

tool = HTSTool()
result = tool.run(hts_code="8517.12.00", lane_id="CNSHA-USLAX-ocean")
# Returns: {notes: [...], headings: [...], duty_rate: "Free", sources: [...]}
```

**Deliverable:** Working HTS tool with tests

---

### Day 4: Sanctions Tool Implementation
**Branch:** `feature/sanctions-tool`

**Tasks:**
- [ ] Implement `sanctions_tool.py`:
  - OFAC Consolidated Screening List API client
  - Party name fuzzy matching algorithm
  - CSL list parsing and indexing
  - Confidence scoring for matches
- [ ] Add local caching of CSL data (weekly refresh)
- [ ] Create `SanctionsResponse` model
- [ ] Write tests with sample sanctioned entity names
- [ ] Document screening logic and thresholds

**Deliverable:** Working sanctions screening tool

---

### Day 5: Refusals & Rulings Tools
**Branch:** `feature/refusals-rulings-tools`

**Tasks:**
- [ ] Implement `refusals_tool.py`:
  - FDA Import Refusals API integration
  - FSIS Refusal CSV parser
  - Filter by HTS code, product keywords, country
  - Aggregate refusal trends
- [ ] Implement `rulings_tool.py`:
  - CBP CROSS rulings search
  - HTML/PDF parsing for ruling text
  - Extract HTS classifications and dates
- [ ] Create response models for both tools
- [ ] Write integration tests
- [ ] Document data sources and update frequencies

**Deliverable:** All 4 compliance tools operational

**Week 1 Checkpoint:** ✅ Domain models + 4 compliance tools ready

---

## Week 2: LangGraph & ChromaDB (Days 6-10)

### Day 6: ChromaDB Collections Setup
**Branch:** `feature/compliance-chromadb`

**Tasks:**
- [ ] Create `infrastructure/db/compliance_collections.py`
- [ ] Define collection schemas:
  - `hts_notes` collection with metadata fields
  - `rulings` collection with ruling metadata
  - `refusal_summaries` collection
  - `policy_snippets` collection
- [ ] Implement collection initialization functions
- [ ] Add metadata filtering helpers
- [ ] Write seed data loader for testing (100 sample records)
- [ ] Test retrieval with lane-specific queries

**Deliverable:** ChromaDB collections ready for indexing

---

### Day 7: Data Normalization Service
**Branch:** `feature/compliance-normalizer`

**Tasks:**
- [ ] Create `application/compliance_service/normalizer.py`
- [ ] Implement normalizers for each data source:
  - `normalize_hts_data()` → ComplianceEvent
  - `normalize_sanctions_data()` → ComplianceEvent
  - `normalize_refusals_data()` → ComplianceEvent
  - `normalize_rulings_data()` → ComplianceEvent
- [ ] Add SKU/lane tagging logic
- [ ] Implement evidence extraction and citation building
- [ ] Write unit tests for each normalizer
- [ ] Add validation layer (schema compliance)

**Deliverable:** Data normalization pipeline

---

### Day 8: Compliance LangGraph - Part 1 (State & Nodes)
**Branch:** `feature/compliance-langgraph`

**Tasks:**
- [ ] Create `application/compliance_service/compliance_graph.py`
- [ ] Define `ComplianceState` TypedDict
- [ ] Implement core nodes:
  - `load_client_context()` - mem0 integration
  - `search_hts_node()` - wrapper for HTS tool
  - `screen_sanctions_node()` - wrapper for sanctions tool
  - `fetch_refusals_node()` - wrapper for refusals tool
  - `find_rulings_node()` - wrapper for rulings tool
- [ ] Add logging and metrics collection per node
- [ ] Write node unit tests

**Deliverable:** LangGraph nodes implemented

---

### Day 9: Compliance LangGraph - Part 2 (Retrieval & Reasoning)
**Branch:** `feature/compliance-langgraph` (continued)

**Tasks:**
- [ ] Implement retrieval node:
  - `retrieve_context_node()` - ChromaDB RAG with lane filtering
  - Metadata filtering by SKU ID, HTS code, lane ID
  - Top-k retrieval with relevance scoring
- [ ] Implement reasoning node:
  - `reason_compliance_node()` - synthesize snapshot
  - Generate Tile objects for each compliance area
  - Build citations list from all sources
  - Apply client-specific thresholds (from mem0)
- [ ] Add guardrails for uncertainty detection
- [ ] Write integration tests for graph execution

**Deliverable:** Complete LangGraph with reasoning

---

### Day 10: Compliance LangGraph - Part 3 (Routing & Integration)
**Branch:** `feature/compliance-langgraph` (continued)

**Tasks:**
- [ ] Implement routing logic:
  - Entry point → load_client_context
  - Conditional routing based on client preferences
  - Parallel tool execution coordination
  - Error handling and fallback paths
- [ ] Add graph compilation and checkpointing
- [ ] Implement `ComplianceService` wrapper:
  - `snapshot(client_id, sku_id, lane_id)` → SnapshotResponse
  - `ask(client_id, question, context)` → reasoning response
- [ ] Write end-to-end graph tests
- [ ] Document graph flow and decision points

**Deliverable:** Production-ready ComplianceGraph

**Week 2 Checkpoint:** ✅ LangGraph + ChromaDB operational

---

## Week 3: API & Pipelines (Days 11-15)

### Day 11: API Models & Routes Setup
**Branch:** `feature/compliance-api`

**Tasks:**
- [ ] Update `infrastructure/api/models.py`:
  - `SnapshotRequest`, `SnapshotResponse`
  - `WeeklyPulseResponse`, `WeeklyPulseLane`
  - `AskRequest`, `AskResponse`
  - `IngestTriggerRequest`
- [ ] Create `infrastructure/api/routes/compliance_routes.py`
- [ ] Set up router with prefix `/compliance`
- [ ] Add API key authentication dependency
- [ ] Write API model validation tests

**Deliverable:** API models and route scaffolding

---

### Day 12: Snapshot Endpoint Implementation
**Branch:** `feature/compliance-api` (continued)

**Tasks:**
- [ ] Implement `POST /compliance/snapshot`:
  - Validate request (client_id, sku_id, lane_id)
  - Load client profile from mem0
  - Execute ComplianceGraph
  - Return SnapshotResponse with citations
  - Add request logging and metrics
- [ ] Add error handling:
  - Invalid SKU/lane combinations
  - Tool failures (partial snapshot)
  - Rate limiting (per client)
- [ ] Write API integration tests
- [ ] Document endpoint with OpenAPI examples

**Deliverable:** Working `/snapshot` endpoint

---

### Day 13: Ask & Admin Endpoints
**Branch:** `feature/compliance-api` (continued)

**Tasks:**
- [ ] Implement `POST /compliance/ask`:
  - Parse natural language question
  - Load client/SKU/lane context from mem0
  - Execute reasoning subgraph
  - Return answer with citations
- [ ] Implement `POST /compliance/admin/ingest/run`:
  - Trigger ZenML ingestion pipeline
  - Return job ID and status
- [ ] Add authentication checks for admin endpoint
- [ ] Write tests for both endpoints
- [ ] Update API documentation

**Deliverable:** All core endpoints functional

---

### Day 14: ZenML Ingestion Pipeline
**Branch:** `feature/zenml-compliance-ingestion`

**Tasks:**
- [ ] Create `application/zenml_pipelines/compliance_ingestion.py`
- [ ] Implement pipeline steps:
  - `@step fetch_hts_data()` - call HTS tool for all tracked HTS codes
  - `@step fetch_ofac_data()` - download latest CSL
  - `@step fetch_fda_data()` - query FDA refusals
  - `@step fetch_fsis_data()` - download FSIS CSV
  - `@step fetch_cbp_rulings()` - search recent rulings
  - `@step normalize_events()` - run normalizer
  - `@step index_to_chroma()` - index to ChromaDB
  - `@step update_mem0()` - update client context
- [ ] Add pipeline configuration (YAML)
- [ ] Test pipeline execution locally
- [ ] Set up daily schedule (2 AM UTC)

**Deliverable:** Automated daily ingestion pipeline

---

### Day 15: Weekly Pulse Pipeline
**Branch:** `feature/zenml-weekly-pulse`

**Tasks:**
- [ ] Create `application/zenml_pipelines/weekly_pulse.py`
- [ ] Implement pipeline steps:
  - `@step load_previous_snapshot()` - fetch last week's data
  - `@step generate_current_snapshot()` - run snapshot for all SKUs
  - `@step compute_delta()` - diff by SKU + lane
  - `@step rank_by_impact()` - prioritize critical changes
  - `@step generate_digest()` - create WeeklyPulseResponse
  - `@step save_digest()` - store in database/mem0
- [ ] Implement `GET /compliance/pulse/{client_id}/weekly` endpoint
- [ ] Test pulse generation for sample client
- [ ] Set up weekly schedule (Sunday 6 AM UTC)

**Deliverable:** Weekly pulse pipeline + endpoint

**Week 3 Checkpoint:** ✅ API + pipelines ready for testing

---

## Week 4: Testing & Deployment (Days 16-20)

### Day 16: Integration Testing
**Branch:** `test/end-to-end-compliance`

**Tasks:**
- [ ] Create end-to-end test suite:
  - Test full snapshot generation (mock external APIs)
  - Test weekly pulse delta computation
  - Test ask endpoint with compliance questions
  - Test pipeline execution with ZenML
- [ ] Set up test fixtures:
  - 10 sample SKUs with real HTS codes
  - 3 sample lanes (China→US, Mexico→US, Vietnam→US)
  - 1 sample client profile with preferences
- [ ] Run tests with coverage reporting (target: >85%)
- [ ] Fix any failing tests

**Deliverable:** Passing end-to-end test suite

---

### Day 17: Performance & Load Testing
**Branch:** `test/performance`

**Tasks:**
- [ ] Create performance test scripts:
  - Snapshot latency test (target: <5s p95)
  - Concurrent request handling (10 clients)
  - ChromaDB query performance
  - Tool response time benchmarks
- [ ] Identify and optimize bottlenecks:
  - Add caching where needed
  - Optimize ChromaDB queries
  - Parallelize tool calls in LangGraph
- [ ] Document performance baselines
- [ ] Set up monitoring/alerting

**Deliverable:** Performance-optimized system

---

### Day 18: Documentation & Examples
**Branch:** `docs/compliance-platform`

**Tasks:**
- [ ] Write user documentation:
  - API endpoint guide with curl examples
  - Client onboarding guide (how to add SKUs/lanes)
  - Snapshot interpretation guide (what each tile means)
  - Troubleshooting guide
- [ ] Create developer documentation:
  - Architecture diagrams
  - Tool development guide
  - LangGraph extension guide
  - ZenML pipeline guide
- [ ] Add docstrings to all public functions
- [ ] Generate API docs with FastAPI/OpenAPI

**Deliverable:** Complete documentation

---

### Day 19: Demo Preparation
**Branch:** `demo/mvp-pilot`

**Tasks:**
- [ ] Set up pilot client data:
  - 30 real SKUs across 3-5 lanes
  - Client profile with realistic preferences
  - Historical data for delta testing
- [ ] Run full ingestion pipeline
- [ ] Generate sample snapshots for all SKUs
- [ ] Create weekly pulse digest
- [ ] Prepare demo script and talking points
- [ ] Test in staging environment

**Deliverable:** Working demo with real data

---

### Day 20: MVP Review & Handoff
**Branch:** `release/compliance-pulse-mvp`

**Tasks:**
- [ ] Code review and cleanup:
  - Address linting warnings
  - Remove debug code
  - Optimize imports
  - Add type hints where missing
- [ ] Final testing pass:
  - Smoke tests in production-like environment
  - Security audit (API keys, data access)
  - Error handling verification
- [ ] Deployment preparation:
  - Environment variable documentation
  - Docker/deployment scripts
  - Database migration scripts (if needed)
- [ ] Stakeholder demo and feedback
- [ ] Document known issues and V1 roadmap

**Deliverable:** Production-ready MVP

**Week 4 Checkpoint:** 🎯 MVP COMPLETE

---

## Post-MVP: V1 Features (Weeks 5-8)

### Week 5-6: Memory & Personalization
- [ ] Client preference learning (mem0 patterns)
- [ ] Dismissal memory and false positive tracking
- [ ] Change context delta (new/resolved/escalated)
- [ ] Causal insights ("why did this change occur?")

### Week 7-8: Workflow Automation & Coverage
- [ ] Slack/Email digest delivery
- [ ] CSV/JSON exports for BI tools
- [ ] FTA rules integration
- [ ] Sanctions delta tracking over time
- [ ] Lane heatmap analytics

---

## Deployment Checklist

### Environment Setup
- [ ] Production `.env` configured
- [ ] External API keys/access verified
- [ ] ChromaDB persistent storage configured
- [ ] mem0 database configured
- [ ] ZenML server deployed (if using remote)
- [ ] Logging/monitoring configured (e.g., Datadog, Sentry)

### Security
- [ ] API key rotation policy established
- [ ] Rate limiting configured
- [ ] HTTPS/TLS certificates
- [ ] Data retention policy documented
- [ ] Audit logging enabled

### Operations
- [ ] Backup strategy for ChromaDB/mem0
- [ ] Pipeline monitoring and alerting
- [ ] On-call rotation for production issues
- [ ] Runbook for common operations

---

## Success Criteria (MVP Acceptance)

| Criterion | Target | Status |
|-----------|--------|--------|
| Snapshot latency (p95) | < 5 seconds | ⏳ |
| SKU coverage | 30-50 SKUs | ⏳ |
| Data accuracy | > 95% | ⏳ |
| Tool success rate | > 90% | ⏳ |
| Weekly digest on-time | 100% | ⏳ |
| Citation completeness | 100% | ⏳ |
| API uptime | > 99% | ⏳ |
| Test coverage | > 85% | ⏳ |

---

## Risk Mitigation Plan

### High-Risk Items
1. **External API reliability**
   - Mitigation: Caching + fallback to last-known-good data
   - Monitoring: Alert on tool failure rate > 10%

2. **Tool execution latency**
   - Mitigation: Parallel execution + timeouts
   - Monitoring: p95 latency alerts

3. **Data quality issues**
   - Mitigation: Validation layer + human review flagging
   - Monitoring: Track accuracy metrics

### Medium-Risk Items
1. **Complex lane-specific logic**
   - Mitigation: Start with simple 1-2 lanes, iterate
   - Monitoring: User feedback loop

2. **Memory growth (ChromaDB/mem0)**
   - Mitigation: Retention policies + archival
   - Monitoring: Database size alerts

---

## Communication Plan

### Daily Standups
- Progress on current phase
- Blockers and dependencies
- Demo of working features

### Weekly Demos
- End-of-week feature showcase
- Stakeholder feedback session
- Adjust priorities based on feedback

### Milestone Reviews
- End of Week 1: Tools + models review
- End of Week 2: LangGraph + ChromaDB review
- End of Week 3: API + pipelines review
- End of Week 4: MVP demo + go/no-go decision

---

## Contact & Escalation

**Technical Lead:** [Name]  
**Product Owner:** [Name]  
**Stakeholders:** [Names]

**Escalation Path:**
1. Blocker identified → Notify tech lead within 2 hours
2. External dependency issue → Notify stakeholders same day
3. Timeline risk → Review and re-plan within 24 hours

---

**Last Updated:** 2025-10-25  
**Next Review:** Daily during implementation
