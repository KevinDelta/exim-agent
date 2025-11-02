# Compliance Pulse — Ingestion & Update Runbook (SKU + Lane Focus)

**Scope:** Technical playbook for pulling core compliance data sources into the backend (FastAPI + LangGraph + Chroma + Postgres). Covers: HTS (USITC), CBP CROSS rulings, sanctions (CSL/OFAC), FDA import refusals, FSIS import refusals. Includes cadence, schemas, code stubs, and monitoring.

---

## 🔵 IMPLEMENTATION STATUS (Updated: October 2025)

### ✅ Completed

- **Core Architecture**: FastAPI backend with LangGraph execution graphs
- **Vector Store**: ChromaDB with 4 collections (hts_notes, rulings, refusals, policy)
- **Compliance Tools**: Mock implementations of HTS, Sanctions, Refusals, Rulings tools
- **ZenML Pipeline Skeleton**: `compliance_ingestion_pipeline` with 7 steps defined
- **API Endpoints**: `/compliance/snapshot`, `/compliance/ask`, `/chat` routes
- **Domain Models**: Full Pydantic models for SKU, Lane, Events, Tiles, Snapshots
- **Frontend**: Next.js app with basic UI components and compliance workflow hooks

### 🟡 Partially Complete

- **Data Ingestion**: ZenML pipeline exists but uses mock data only
- **Tool Integration**: Tool infrastructure exists but all return hardcoded mock data
- **Collections**: ChromaDB collections initialized but not populated with real data
- **Compliance Graph**: LangGraph workflow exists but doesn't fetch real external data

### ❌ Not Started

- **Real API Integration**: No actual calls to USITC, CBP CROSS, CSL, OFAC, FDA, FSIS
- **Postgres Tables**: Database schemas defined in this doc but not created
- **Raw Data Storage**: Object store structure planned but not implemented
- **Weekly Pulse**: Diff detection and delta analysis logic not built
- **Scheduling**: No cron jobs or automated triggers configured
- **Monitoring**: No ingestion logs, health checks, or alerting
- **Authentication**: No API key management for external services
- **Error Handling**: Basic retry logic exists but no circuit breakers or rate limiting

### 📊 Current Data Flow

```yml
API Request → ComplianceService → LangGraph → Tools (mock data) → ChromaDB (empty) → Response
```

### 🎯 Next Priority Implementation Order

1. **Phase 1 - Real Data Integration** (Weeks 1-2)
   - Implement actual API calls in each tool (HTS, Sanctions, etc.)
   - Test with real API keys and handle rate limits
   - Store raw responses in object storage

2. **Phase 2 - Data Persistence** (Week 3)
   - Create Postgres tables per schema below
   - Implement normalization functions
   - Populate ChromaDB with real data

3. **Phase 3 - Pipeline Automation** (Week 4)
   - Set up daily ZenML pipeline runs
   - Implement diff/delta detection
   - Build weekly pulse digest logic

4. **Phase 4 - Production Readiness** (Week 5)
   - Add monitoring and alerting
   - Implement health checks
   - Set up secret management
   - Document API contracts

---

## 1) Data Sources Overview

| Domain | Source | Method | Auth | Update Cadence | Notes |
|---|---|---|---|---|---|
| Tariff/Classification | USITC HTS | REST search + optional bulk export | None | Nightly + on-demand | Use search for targeted lookups; keep a weekly baseline export snapshot |
| Rulings (classification/origin/valuation) | CBP CROSS | Polite HTML crawl (search → detail) | None | Daily | Cache HTML; parse to Markdown; respect robots and throttle |
| Sanctions/Parties | ITA CSL API | JSON API (fuzzy search, filters) | API key | Daily + on-demand | Good primary API for screening and deltas |
| Sanctions/Parties | OFAC SLS | JSON/CSV downloads (and API-style GET) | None | Daily | Use to validate CSL and compute diffs |
| Health & Safety | FDA Import Refusals | REST API (Data Dashboard) | FDA OII token | Weekly | Page/stream results; track firm+country trends |
| Health & Safety (meat/poultry/egg) | USDA FSIS | ZIP → CSV monthly | None | Monthly | Import lot-level rows; map to countries/products |

---

## 2) Pipelines (ZenML)

### 2.1 `fetch_normalize_index` (daily)

**Steps:**

1. `fetch_hts` → query REST for changed terms; weekly bulk snapshot; store raw JSON/CSV.
2. `fetch_csl` → CSL API (name=*, last_updated filter if available); store raw; normalize to `party_screen`.  
3. `fetch_ofac` → pull SLS files/JSON; compute hash diff; normalize.  
4. `fetch_fda_refusals` → FDA API; paginate; store raw; normalize `fda_refusals`.  
5. `fetch_cbp_rulings` → crawl search results for target HTS/keywords; fetch detail pages; parse to `cbp_rulings`.  
6. `embed_all_changed` → upsert normalized docs into Chroma with deterministic IDs.  
7. `commit_metrics` → write `ingestion_log` row with counts and timing.

**Inputs:** None (scheduled / cron).  
**Outputs:** Raw object-store files, normalized tables, updated Chroma embeddings.

### 2.2 `weekly_pulse` (weekly)

**Steps:**

1. `diff_by_sku_lane` → compare normalized tables vs previous week by `sku_id` + `lane_id`.  
2. `summarize_agentic` → LangGraph node converts diffs into `ComplianceEvent` summaries with citations.  
3. `deliver_digest` → persist digest JSON; (optional) email/Slack render.

---

## 3) Data Contracts

### 3.1 Raw Storage (Object Store)

```bash
raw/
  hts/YYYYMMDD/run.json (or CSV)
  csl/YYYYMMDD/page_*.json
  ofac/YYYYMMDD/*.json or *.csv
  fda_refusals/YYYYMMDD/page_*.json
  cbp_html/YYYYMMDD/{ruling_id}.html
meta/
  fetch_manifest_{run_id}.json  # {source, url, fetched_at, http_status, sha256}
```

### 3.2 Normalized (Postgres)

```sql
-- HTS
create table if not exists hts_articles (
  hts_code text primary key,
  description text,
  chapter_note_refs text[],
  duty_rate jsonb,
  effective_from date,
  effective_to date,
  last_seen_at timestamptz,
  source_url text
);

-- CBP Rulings
create table if not exists cbp_rulings (
  ruling_id text primary key,
  date_issued date,
  title text,
  hts_refs text[],
  summary_md text,
  full_text_md text,
  source_url text,
  last_seen_at timestamptz
);

-- Party Screening
create table if not exists party_screen (
  id bigserial primary key,
  name text,
  list text,              -- SDN | Non-SDN | CSL
  program text,
  ids_json jsonb,
  addresses_json jsonb,
  last_updated date,
  source text,            -- CSL | OFAC
  source_url text
);

-- FDA Refusals
create table if not exists fda_refusals (
  id bigserial primary key,
  refusal_date date,
  product_desc text,
  firm_name text,
  country_code text,
  reason text,
  port text,
  source_url text
);

-- FSIS Refusals
create table if not exists fsis_refusals (
  id bigserial primary key,
  fy int,
  lot_id text,
  country text,
  establishment text,
  product text,
  refused boolean,
  reason text,
  source_url text
);

-- Ingestion runs
create table if not exists ingestion_log (
  run_id uuid default gen_random_uuid() primary key,
  source text,
  status text,
  row_count int,
  started_at timestamptz,
  finished_at timestamptz,
  error text
);
```

### 3.3 Vector Store (Chroma)

- Collections: `hts_notes`, `rulings`, `refusal_summaries`, `policy_snippets`  
- Common metadata: `{ doc_type, hts_code?, sku_id?, lane_id?, source_url, last_seen_at, hash }`

---

## 4) Source Adapters Implementation Guide

> **Current State**: Stubs exist in `/src/exim_agent/domain/tools/` but return mock data only.
> **Next Step**: Replace mock responses with actual API calls in each tool's `_run_impl` method.
> **Location**: All tools inherit from `ComplianceTool` with built-in retry, caching, and circuit breaker support.

### 4.1 USITC HTS — Search + Hydrate

**Current**: `hts_tool.py` returns hardcoded data for 3 HTS codes
**Location**: `/src/exim_agent/domain/tools/hts_tool.py`

**Implementation TODO**:

```python
# In HTSTool._run_impl()
import httpx

def _run_impl(self, hts_code: str, lane_id: str = None) -> Dict[str, Any]:
    # 1. Check cache first (inherited from ComplianceTool)
    
    # 2. Query USITC REST API
    url = f"https://hts.usitc.gov/reststop/tariff/{hts_code}"
    response = httpx.get(url, headers={"Accept": "application/json"})
    
    # 3. Parse response and normalize
    data = response.json()
    normalized = {
        "hts_code": hts_code,
        "description": data.get("article_description"),
        "duty_rate": data.get("general_rate"),
        "unit": data.get("unit_of_quantity"),
        "source_url": f"https://hts.usitc.gov/view/{hts_code}",
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }
    
    # 4. Store raw response in object storage
    self._store_raw(f"hts/{datetime.utcnow().strftime('%Y%m%d')}/{hts_code}.json", data)
    
    return normalized
```

### 4.2 CBP CROSS — Crawl & Parse

**Current**: `rulings_tool.py` returns 2 hardcoded rulings
**Location**: `/src/exim_agent/domain/tools/rulings_tool.py`

**Implementation TODO**:

```python
# In RulingsTool._run_impl()
import httpx
from bs4 import BeautifulSoup
import asyncio

def _run_impl(self, search_term: str) -> Dict[str, Any]:
    # 1. Search for rulings
    search_url = f"https://rulings.cbp.gov/search?query={search_term}"
    html = httpx.get(search_url).text
    
    # 2. Parse search results
    soup = BeautifulSoup(html, 'html.parser')
    ruling_links = soup.select('a[href*="/ruling/"]')[:10]  # Limit to 10
    
    # 3. Fetch each ruling detail (with rate limiting)
    rulings = []
    for link in ruling_links:
        time.sleep(1.5)  # Politeness throttle
        
        ruling_url = f"https://rulings.cbp.gov{link['href']}"
        detail_html = httpx.get(ruling_url).text
        
        # Parse ruling detail page
        ruling = self._parse_ruling_detail(detail_html)
        rulings.append(ruling)
        
        # Store raw HTML
        ruling_id = ruling['ruling_number']
        self._store_raw(f"cbp_html/{datetime.utcnow().strftime('%Y%m%d')}/{ruling_id}.html", detail_html)
    
    return {"rulings": rulings, "count": len(rulings)}

def _parse_ruling_detail(self, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html.parser')
    # Extract: ruling_number, title, date_issued, hts_refs[], full_text_md
    # TODO: Implement HTML parsing logic
    pass
```

**CRITICAL**: Implement robots.txt checking and User-Agent headers:

```python
headers = {"User-Agent": "CompliancePulseBot/1.0 (contact: ops@yourco.com)"}
```

### 4.3 ITA CSL — JSON API

**Current**: `sanctions_tool.py` returns 1 hardcoded match
**Location**: `/src/exim_agent/domain/tools/sanctions_tool.py`

**Implementation TODO**:

```python
# In SanctionsTool._run_impl()
import httpx
from exim_agent.config import config

def _run_impl(self, entity_name: str, country_code: str = None) -> Dict[str, Any]:
    # 1. Build CSL API query
    params = {
        "name": entity_name,
        "sources": "all",
        "fuzzy_name": "true"
    }
    if country_code:
        params["countries"] = country_code
    
    # 2. Query CSL API with API key
    url = "https://api.trade.gov/consolidated_screening_list/v1/search"
    headers = {"apikey": config.csl_api_key}  # Add to config.py
    
    response = httpx.get(url, params=params, headers=headers)
    data = response.json()
    
    # 3. Normalize results
    matches = []
    for result in data.get("results", []):
        matches.append({
            "name": result.get("name"),
            "list": result.get("source"),
            "program": result.get("programs", []),
            "addresses": result.get("addresses", []),
            "last_updated": result.get("last_updated")
        })
    
    # 4. Store raw response
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    self._store_raw(f"csl/{timestamp}/{entity_name}.json", data)
    
    return {"matches": matches, "total": len(matches)}
```

**Config Addition Needed**:

```python
# In config.py
csl_api_key: str = Field(default="", env="CSL_API_KEY")
```

**Environment Variable**:

```bash
export CSL_API_KEY="your-csl-api-key-here"
```

### 4.4 OFAC SLS — Download & Diff

**Current**: Not implemented (CSL tool partially covers this)
**Location**: Create new `/src/exim_agent/domain/tools/ofac_tool.py`

**Implementation TODO**:

```python
# New tool: ofac_tool.py
import httpx
import hashlib
from pathlib import Path

class OFACTool(ComplianceTool):
    def _run_impl(self) -> Dict[str, Any]:
        # 1. Download SDN list
        url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
        response = httpx.get(url)
        
        # 2. Compute hash for diff detection
        current_hash = hashlib.sha256(response.content).hexdigest()
        previous_hash = self._get_previous_hash("ofac_sdn")
        
        # 3. Store raw if changed
        if current_hash != previous_hash:
            timestamp = datetime.utcnow().strftime('%Y%m%d')
            self._store_raw(f"ofac/{timestamp}/sdn.csv", response.content)
            self._update_hash("ofac_sdn", current_hash)
            
            # 4. Parse and detect changes
            changes = self._detect_changes(response.text)
            return {"status": "updated", "changes": changes}
        
        return {"status": "no_changes", "last_hash": current_hash}
```

### 4.5 FDA Import Refusals — REST

**Current**: `refusals_tool.py` returns hardcoded country-level summaries
**Location**: `/src/exim_agent/domain/tools/refusals_tool.py`

**Implementation TODO**:

```python
# In RefusalsTool._run_impl()
import httpx
from exim_agent.config import config

def _run_impl(self, country: str = None, product_type: str = None, hts_code: str = None) -> Dict[str, Any]:
    # 1. Build FDA API query
    params = {"limit": 5000}
    if country:
        params["search"] = f"country:{country}"
    if product_type:
        params["search"] += f" AND product_code_desc:{product_type}"
    
    # 2. Query FDA API
    url = "https://api.fda.gov/food/enforcement.json"  # Note: Updated endpoint
    headers = {"Authorization": f"Bearer {config.fda_oii_token}"}  # Add to config
    
    response = httpx.get(url, params=params, headers=headers)
    data = response.json()
    
    # 3. Normalize and aggregate
    refusals = []
    for result in data.get("results", []):
        refusals.append({
            "product": result.get("product_description"),
            "firm": result.get("recalling_firm"),
            "country": result.get("country"),
            "reason": result.get("reason_for_recall"),
            "date": result.get("recall_initiation_date"),
            "classification": result.get("classification")
        })
    
    # 4. Aggregate insights
    insights = self._aggregate_refusals(refusals, country)
    
    # 5. Store raw
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    self._store_raw(f"fda_refusals/{timestamp}/page.json", data)
    
    return {
        "refusals": refusals[:50],  # Top 50
        "insights": insights,
        "total": len(refusals)
    }
```

**Config Addition Needed**:

```python
# In config.py
fda_oii_token: str = Field(default="", env="FDA_OII_TOKEN")
```

### 4.6 FSIS Import Refusals — ZIP→CSV

**Current**: Not implemented
**Location**: Create new `/src/exim_agent/domain/tools/fsis_tool.py`

**Implementation TODO**:

```python
# New tool: fsis_tool.py
import httpx
import zipfile
import csv
from io import BytesIO

class FSISTool(ComplianceTool):
    def _run_impl(self) -> Dict[str, Any]:
        # 1. Get latest ZIP URL from FSIS listing page
        listing_url = "https://www.fsis.usda.gov/inspection/import-export/import-information/foreign-establishments/foreign-establishments-can"
        html = httpx.get(listing_url).text
        
        # Parse for ZIP link (TODO: implement scraping logic)
        zip_url = self._extract_latest_zip_url(html)
        
        # 2. Download ZIP
        zip_response = httpx.get(zip_url)
        
        # 3. Extract and parse CSV
        with zipfile.ZipFile(BytesIO(zip_response.content)) as z:
            csv_file = z.namelist()[0]
            csv_data = z.read(csv_file).decode('utf-8')
        
        # 4. Parse CSV rows
        refusals = []
        for row in csv.DictReader(csv_data.splitlines()):
            refusals.append({
                "establishment": row.get("Establishment Name"),
                "country": row.get("Country"),
                "product": row.get("Product"),
                "reason": row.get("Reason"),
                "refused": row.get("Status") == "Refused"
            })
        
        # 5. Store raw
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        self._store_raw(f"fsis/{timestamp}/refusals.zip", zip_response.content)
        
        return {"refusals": refusals, "total": len(refusals)}
```

---

## 5) Normalization (Python fast-path examples)

```python
def normalize_hts_article(raw: dict) -> dict:
    return {
        "hts_code": raw.get("htsno"),
        "description": raw.get("article_desc"),
        "chapter_note_refs": raw.get("notes", []),
        "duty_rate": raw.get("rates", {}),
        "effective_from": raw.get("effective_from"),
        "effective_to": raw.get("effective_to"),
        "last_seen_at": now_iso(),
        "source_url": raw.get("url"),
    }
```

```python
def normalize_cbp_ruling(parsed: dict) -> dict:
    return {
        "ruling_id": parsed["ruling_id"],
        "title": parsed["title"],
        "date_issued": parsed["date_issued"],
        "hts_refs": parsed.get("hts_refs", []),
        "summary_md": parsed.get("summary_md"),
        "full_text_md": parsed["full_text_md"],
        "source_url": parsed["source_url"],
        "last_seen_at": now_iso(),
    }
```

```python
def normalize_party_record(rec: dict, source: str) -> dict:
    return {
        "name": rec.get("name"),
        "list": rec.get("list", "CSL"),
        "program": rec.get("program"),
        "ids_json": rec.get("ids"),
        "addresses_json": rec.get("addresses"),
        "last_updated": rec.get("last_updated"),
        "source": source,
        "source_url": rec.get("source_url"),
    }
```

---

## 6) Embedding & Indexing (Chroma)

- Deterministic doc IDs: sha256(source_url + title_or_id) to dedupe.  
- Chunk sizes: 512–1024 tokens; include headers so tiles can cite specific sections.  
- Metadata enrichment: `sku_id` and `lane_id` when you can map via mem0 (e.g., country → lane origin).  
- Collections:  
  - `hts_notes` → chapter notes + duty text  
  - `rulings` → holding + summary  
  - `refusal_summaries` → FDA/FSIS normalized fields + short context

---

## 7) Scheduling & Monitoring

- **Schedulers:** cron or ZenML orchestrator.  
- **Retries:** exponential backoff with jitter; circuit-breaker to avoid bans.  
- **Health checks:** compare record counts to rolling 7‑day averages.  
- **Alerts:** Slack/email on ingestion failure or large negative diffs.  
- **Observability:** store `row_count`, `latency_ms`, `error_rate` in `ingestion_log`.  
- **Provenance:** every chunk retains `source_url`, `last_seen_at`, and content hash.

---

## 8) Guardrails & Compliance

- **Robots/TOS:** throttle CROSS crawler (< 1 rps), set a descriptive User‑Agent, honor robots.txt.  
- **Secrets:** keep `CSL_API_KEY` and `FDA_OII_TOKEN` in secret manager; never expose in frontend.  
- **PII:** if sanctions records include addresses or individuals, avoid persisting unnecessary fields in logs.  
- **Citations:** every UI tile must include a link and a “last updated” timestamp.

---

## 9) Environment & Config

```bash
ENV=prod
DATABASE_URL=postgres://...
CHROMA_URL=http://chroma:8000
CSL_API_KEY=***
FDA_OII_TOKEN=***
HTTP_USER_AGENT=CompliancePulseBot/1.0 (contact: ops@yourco.com)
FETCH_CONCURRENCY=2
FETCH_TIMEOUT_MS=30000
CRAWL_RPS=0.7
```

---

## 10) Implementation Checklist

### Phase 1: Real Data Integration (Weeks 1-2)

- [ ] Add API keys to config.py: `CSL_API_KEY`, `FDA_OII_TOKEN`
- [ ] Implement real USITC HTS API calls in `hts_tool.py`
- [ ] Implement CSL API integration in `sanctions_tool.py`
- [ ] Implement FDA API integration in `refusals_tool.py`
- [ ] Implement CBP CROSS scraping in `rulings_tool.py` (with rate limiting)
- [ ] Create `ofac_tool.py` for OFAC SDN downloads
- [ ] Create `fsis_tool.py` for FSIS ZIP processing
- [ ] Implement object storage layer: `_store_raw()` method in base tool
- [ ] Test each tool individually with real API credentials
- [ ] Validate rate limiting and error handling

### Phase 2: Data Persistence (Week 3)

- [ ] Create Postgres migration for all tables (see schema in section 3.2)
- [ ] Implement normalization functions (see section 5)
- [ ] Update `compliance_ingestion_pipeline.py` to use real tools
- [ ] Populate ChromaDB collections with real data
- [ ] Create `ingestion_log` table and logging logic
- [ ] Implement deterministic document IDs: `sha256(source_url + title)`
- [ ] Test end-to-end pipeline: fetch → normalize → store → embed

### Phase 3: Pipeline Automation (Week 4)

- [ ] Set up ZenML schedule for daily runs: `compliance_ingestion_pipeline(lookback_days=1)`
- [ ] Implement diff detection logic for weekly pulse
- [ ] Build `weekly_pulse` ZenML pipeline (see section 2.2)
- [ ] Create `/admin/ingest/run` FastAPI endpoint for manual triggers
- [ ] Add `/admin/ingest/status` endpoint to check pipeline runs
- [ ] Implement SKU/Lane-specific filtering in diff logic
- [ ] Test weekly pulse with historical data

### Phase 4: Production Readiness (Week 5)

- [ ] Add health checks: compare record counts to 7-day rolling average
- [ ] Set up Slack/email alerts for ingestion failures
- [ ] Implement circuit breakers in ComplianceTool base class
- [ ] Add retry logic with exponential backoff
- [ ] Configure secret management (AWS Secrets Manager / Vault)
- [ ] Set up observability: log row_count, latency_ms, error_rate
- [ ] Create monitoring dashboard for ingestion metrics
- [ ] Backfill last 3-6 months of rulings and refusals
- [ ] QA with 10-50 real SKUs and 2-3 lanes
- [ ] Document all API contracts and payload examples

### Quick Wins (Can do in parallel)

- [ ] Update config.py with HTTP_USER_AGENT for crawling
- [ ] Create raw data directory structure: `data/raw/{source}/YYYYMMDD/`
- [ ] Add robots.txt checker for CBP CROSS
- [ ] Implement hash-based change detection for OFAC
- [ ] Add metadata enrichment: link HTS codes to SKU via mem0

---

**End of Runbook**: This document provides a comprehensive guide for implementing the Compliance Pulse ingestion system. Follow the phases and checklists to build a robust, scalable compliance data pipeline.
