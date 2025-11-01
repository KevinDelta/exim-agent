
# Compliance Pulse — Ingestion & Update Runbook (SKU + Lane Focus)

**Scope:** Technical playbook for pulling core compliance data sources into the backend (FastAPI + LangGraph + ZenML + Chroma + Postgres). Covers: HTS (USITC), CBP CROSS rulings, sanctions (CSL/OFAC), FDA import refusals, FSIS import refusals. Includes cadence, schemas, code stubs, and monitoring.

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
```
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

## 4) Source Adapters (Code Stubs)

> All stubs are backend-only. Use retries + exponential backoff and structured logging. Replace `...` with your actual logic.

### 4.1 USITC HTS — Search + Hydrate (TypeScript)
```ts
export async function searchHTS(keyword: string) {
  const url = `https://hts.usitc.gov/reststop/search?keyword=${encodeURIComponent(keyword)}`;
  const res = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!res.ok) throw new Error(`HTS search failed: ${res.status}`);
  const data = await res.json();
  return data; // hydrate by following item URLs if available
}
```

### 4.2 CBP CROSS — Crawl & Parse (TypeScript)
```ts
export async function fetchCBPRulingsForHTS(hts: string) {
  const url = `https://rulings.cbp.gov/search?query=${encodeURIComponent(hts)}`;
  const html = await fetchText(url);
  const links = parseRulingLinks(html); // returns ["/ruling/H289712", ...]
  const out: any[] = [];
  for (const rel of links.slice(0, 50)) {
    await delay(1500); // politeness throttle
    const page = await fetchText(`https://rulings.cbp.gov${rel}`);
    const rec = parseRulingDetail(page); // {ruling_id, title, date_issued, hts_refs[], full_text_md, source_url}
    out.push(rec);
  }
  return out;
}
```

### 4.3 ITA CSL — JSON API (TypeScript)
```ts
export async function cslSearch(name: string) {
  const url = `https://api.trade.gov/consolidated_screening_list/v1/search?name=${encodeURIComponent(name)}&sources=all&fuzzy_name=true`;
  const res = await fetch(url, { headers: { "apikey": process.env.CSL_API_KEY! } });
  if (!res.ok) throw new Error(`CSL search failed: ${res.status}`);
  return await res.json();
}
```

### 4.4 OFAC SLS — Download & Diff (TypeScript)
```ts
export async function fetchOFACFiles() {
  // example: SDN zip / JSON endpoints published by OFAC SLS
  const files = [
    "https://sanctionslist.ofac.treas.gov/SLSDocs/SDNList_Acrobat.zip"
  ];
  for (const u of files) {
    const buf = await fetchBuffer(u);
    await saveRaw("ofac", buf, u);
  }
}
```

### 4.5 FDA Import Refusals — REST (TypeScript)
```ts
export async function fetchFDARefusals(params: Record<string,string>) {
  const q = new URLSearchParams({ limit: "5000", **params }).toString();
  const url = `https://api-datadashboard.fda.gov/v1/import_refusals?${q}`;
  const res = await fetch(url, { headers: { "Authorization": `Bearer ${process.env.FDA_OII_TOKEN!}` }});
  if (!res.ok) throw new Error(`FDA refusals failed: ${res.status}`);
  return await res.json();
}
```

### 4.6 FSIS Import Refusals — ZIP→CSV (TypeScript)
```ts
export async function fetchFSISLatestZip(listingUrl: string) {
  // 1) scrape listing page for latest ZIP
  // 2) download ZIP to raw/ofac/YYYYMMDD/
  // 3) unzip to temp, parse CSV rows, normalize
}
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

```
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

## 10) Quick Checklist

- [ ] Create raw + normalized storage layout  
- [ ] Implement each source adapter with retries + logging  
- [ ] Build `fetch_normalize_index` ZenML pipeline  
- [ ] Build `weekly_pulse` pipeline (diff + summaries)  
- [ ] Add deterministic IDs + metadata for embeddings  
- [ ] Wire FastAPI admin hooks `/admin/ingest/run`  
- [ ] Set cron/ZenML schedules + Slack alerts  
- [ ] Backfill last 12 months for rulings/refusals  
- [ ] QA with 10–50 SKUs and 2–3 lanes  
- [ ] Document API contracts and example payloads

---

**End of Runbook**
