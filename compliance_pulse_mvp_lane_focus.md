
# Compliance Pulse MVP — Architecture & Implementation Blueprint (SKU + Lane Focus)

**Date:** 2025-10-25

## 0) Purpose

Stand up a focused MVP for **3PL import/export compliance intelligence** with deep **SKU + lane awareness**.
The system tracks SKU- and lane-specific compliance changes (tariff/HTS notes, sanctions screening, FDA/FSIS signals, CBP rulings), generates weekly digests, and provides agentic reasoning and actionable summaries for supply-chain teams.
Backend-first design: **LangGraph v1 + ChromaDB + mem0 + ZenML + FastAPI**.
Simple **Next.js** UI for inputs and output rendering — all logic runs in the backend.

---

## 1) High-Level Objectives

- **SKU + Lane centric:** Monitor compliance per SKU *and* per logistics lane (origin–destination–mode).
- **Actionable reasoning:** Agent outputs plain-English insights: what changed, why it matters, and what to do.
- **Weekly digest:** Automated per-client summaries grouped by SKU and lane.
- **Traceable outputs:** Every claim links to sources, timestamps, and lanes.
- **Operator fit:** Results structured for supply-chain & ops teams, not just compliance staff.

---

## 2) System Architecture (Backend-first)

```mermaid
flowchart TD
  subgraph Browser[Next.js Frontend]
    UI1[SKU + Lane Input Form]
    UI2[Snapshot View + Weekly Digest]
  end

  subgraph API[FastAPI]
    EP1[/POST /snapshot/]
    EP2[/GET /pulse/{'}}client_id{{'}/weekly/]
    EP3[/POST /ask/]
  end

  subgraph Orchestrator[LangGraph v1]
    G0[Router]
    G1[Tool: search_hts]
    G2[Tool: screen_parties]
    G3[Tool: fetch_refusals]
    G4[Tool: find_rulings]
    G5[Retrieval: ChromaDB]
    G6[Reasoner]
  end

  subgraph Memory[mem0]
    M1[(Client profiles)]
    M2[(SKU + Lane watchlists)]
    M3[(Dismissed alerts & preferences)]
  end

  subgraph Data[Data & Pipelines]
    D1[(ChromaDB Vector Store)]
    D2[(Object Store: raw html/json)]
    D3[(ZenML: Fetch & Normalize)]
  end

  subgraph Sources[External Sources]
    S1[USITC HTS REST]
    S2[CSL / OFAC lists]
    S3[FDA Import Refusals API]
    S4[FSIS Refusal CSV]
    S5[CBP CROSS rulings]
  end

  Browser -->|HTTPS| EP1
  Browser -->|HTTPS| EP2
  Browser -->|HTTPS| EP3

  EP1 --> G0
  EP2 --> G0
  EP3 --> G0

  G0 --> G1 & G2 & G3 & G4 & G5
  G1 --> S1
  G2 --> S2
  G3 --> S3 & S4
  G4 --> S5
  G5 --> D1
  G0 --> M1 & M2 & M3

  D3 --> D2
  D3 --> D1
  D3 --> M1
```

**Principle:** UI collects SKU/lane data and renders outputs; **all logic lives in FastAPI + LangGraph.**

---

## 3) Core Components

### 3.1 FastAPI (service layer)

- Endpoints: `/snapshot`, `/ask`, `/pulse/{'}}client_id{{'}/weekly`, `/admin/ingest/run`.
- Auth: simple API key header.
- Response schema includes SKU, lane, citations, and timestamps.

### 3.2 LangGraph v1 (agentic control)

- Nodes = **tools + retrieval + reasoning**.
- Routing conditioned on SKU + lane context (mem0 lookup).
- Determines change deltas per SKU + lane pair.

### 3.3 ChromaDB (RAG)

- Collections: `hts_notes`, `rulings`, `refusal_summaries`, `policy_snippets`.
- Indexed by `{sku_id, hts_code, lane_id, source_url}`.

### 3.4 mem0 (context & preferences)

- Stores `clients`, `skus`, `lanes`, `preferences`, `dismissals`.
- Enables per-client thresholds (e.g., duty change ≥ 1%).

### 3.5 ZenML (pipelines)

- `fetch_normalize_index`: daily ingestion by SKU/lane.
- `weekly_pulse`: compiles delta by SKU/lane, pushes digest.

---

## 4) Data Model (with Lane Context)

```yaml
ClientProfile:
  id: str
  name: str
  contact: {email: str}
  lanes: [LaneRef]
  watch_skus: [SkuRef]

LaneRef:
  lane_id: str
  origin_port: str
  destination_port: str
  mode: str  # ocean | air | truck

SkuRef:
  sku_id: str
  description: str
  hts_code: str
  origin_country: str
  lanes: [lane_id]

ComplianceEvent:
  id: str
  client_id: str
  sku_id: str
  lane_id: str
  type: "HTS|FTA|SANCTIONS|HEALTH_SAFETY|RULING"
  risk_level: "info|warn|critical"
  summary_md: str
  evidence: [ {source: str, url: str, snippet: str, last_updated: str} ]
  created_at: str

SnapshotResponse:
  client_id: str
  sku_id: str
  lane_id: str
  tiles:
    hts: Tile
    fta_origin: Tile
    sanctions: Tile
    health_safety: Tile
    rulings: Tile
  sources: [Evidence]
  generated_at: str

Tile:
  status: "clear|attention|action"
  headline: str
  details_md: str
```

---

## 5) Tools & Endpoints (MVP)

### 5.1 LangGraph Tools

- `search_hts(term|hts_code, lane) ->{notes, headings, urls}`
- `screen_parties(names, lane) ->{matches, lists}`
- `fetch_refusals(sku|keywords, lane) ->{signals, urls}`
- `find_rulings(hts_code, lane) ->{cases[], urls}`
- `retrieve_context(query, lane) ->{chunks[], citations[]}`

### 5.2 FastAPI Endpoints

- `POST /snapshot` → `{client_id, sku_id, lane_id}` → returns lane-specific snapshot.
- `GET /pulse/{'}}client_id{{'}/weekly` → SKU+lane deltas for digest.
- `POST /ask` → `{client_id, sku_id?, lane_id?, question}` → context-aware Q&A.
- `POST /admin/ingest/run` → triggers ZenML pipeline.

---

## 6) Implementation Strategy (Phased)

- **Phase 0:** Scaffold backend; add mock SKU+lane data.
- **Phase 1:** Real sources (HTS, CSL/OFAC, FDA/FSIS, CROSS) by SKU/lane; normalize to `complianceEvents` and index to chroma; build `POST` /snapshot` end to end with real citations.
- **Phase 2:** Weekly pulse deltas grouped by SKU and lane; ZenML `weekly_pulse` pipeline (diff vs. last week per client/SKU); mem0: store dismissed alerts and thresholds; filter snapshot outputs; Add `GET /pulse/{client_id}/weekly` and email/slack rendering (server‑side).
- **Phase 3:** Frontend snapshot + digest views with lane grouping; Next.js: form for `client_id + sku_id`, display 5‑tile **Snapshot** card + Sources list; Add “Explain this” modal (calls `/ask` with prefilled question).

---

## 7) Frontend (Next.js Minimal)

- **Routes:** `/` (SKU+lane input), `/pulse/[clientId]` (digest).
- **Components:** `SnapshotCard.tsx` shows SKU, lane, tiles, 'whyflagged', and sources.
- **UI Principle:** Backend authoritative; frontend only renders data.

---

## 8) Agentic Reasoning + Weekly Digest + Guardrails & Ops

- The LangGraph reasoner summarizes *why* a change matters for a SKU/lane.
- Weekly digest groups changes by lane and shows top 3 SKUs per lane.
- Each section: lane overview → affected SKUs → recommended actions.
- mem0 stores dismissed alerts and user comments for continuity.
- **Citations & freshness**: every tile must include `last_updated` and a link.
- **Uncertainty surfacing**: if classification conflicts, return `status: attention` + “needs broker review” banner.

---

## 9) Metrics & Deliverables

- **Metrics:** snapshot latency (p95), SKU+lane coverage, alert accuracy, weekly user retention.
- **Deliverables:** FastAPI, LangGraph graph, Chroma collections, mem0 store, ZenML pipelines, Next.js UI, and weekly digest PDF/JSON.

---

## 10) Messaging & Differentiation

- “We watch your SKUs *and* the lanes they travel.”
- “Compliance built for operators — not just compliance specialists.”
- “Agentic insights, weekly digests, real sources.”

---

## 11) Deliverables Checklist (copy/paste to tracker)

- [ ] FastAPI app with `/snapshot`, `/ask`, `/pulse/*`, `/admin/ingest/run`
- [ ] LangGraph v1 graph with tools wired + guardrails
- [ ] ChromaDB collections created and seeded
- [ ] mem0 stores: clients, SKUs, prefs, dismissals
- [ ] ZenML pipelines: `fetch_normalize_index`, `weekly_pulse`
- [ ] Source adapters: HTS, CSL/OFAC, FDA, FSIS, CROSS
- [ ] Snapshot card JSON contract finalized
- [ ] Next.js minimal UI (form + Snapshot card + Pulse page)
- [ ] Logging/metrics; basic API key auth
- [ ] Pilot run with 10–30 SKUs; weekly digest sent

---

## 12) Next Steps

- Add lane mapping feature in UI.
- Implement per-lane analytics dashboard (lane heatmap of changes).
- Integrate Slack/email delivery of weekly digests.
- Add FTA/origin rules, quota monitors, and duty‑change deltas.
- Role‑based access + client self‑service upload of SKU lists.

---

## 13) Team Notes

- Keep **backend the single source of truth**; frontend remains thin.
- Prefer **clear, deterministic tool routing** over "open" agent behavior for MVP.
- Always ship with **source links + dates** to build trust with operators.
