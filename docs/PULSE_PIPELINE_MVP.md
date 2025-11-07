# Weekly/Daily Pulse Pipeline MVP (Core Architecture)

Last updated: 2025-11-06

Objective: Make `src/exim_agent/application/zenml_pipelines/weekly_pulse.py` the core of the MVP, driving both a Weekly Pulse (period_days=7) and a Daily Pulse (period_days=1). This document maps all required modules, data contracts, and execution flows, and aligns the Unsloth fine‑tuning program to optimize Pulse generation quality and efficiency.

---

## 1) Outcomes

- Weekly and Daily “Compliance Pulse” digests saved to Supabase and optionally indexed in Chroma for semantic search.
- Each digest summarizes change deltas across client SKU+Lane portfolios, ranks impact, and includes actionable highlights.
- Pipeline uses our existing Compliance Graph (LangGraph), domain tools, Mem0 (optional), and LLM providers.
- Training program (Unsloth) prioritizes Pulse‑critical tasks and ships evaluated adapters into serving.

---

## 2) Pipeline: Steps and Ownership

Implemented in: `src/exim_agent/application/zenml_pipelines/weekly_pulse.py`

- Step 1: `load_client_sku_lanes(client_id)`
  - Source client portfolio (SKU+Lane+HTS) from DB/config. MVP: static sample; production: DB query.
- Step 2: `load_previous_snapshots(client_id, sku_lanes)`
  - Fetch prior snapshot baselines for diffing. MVP: empty; production: Supabase or events collection.
- Step 3: `generate_current_snapshots(client_id, sku_lanes)`
  - Calls `compliance_service.snapshot()` per SKU+Lane; internally runs Compliance Graph and domain tools.
- Step 4: `compute_deltas(previous, current)`
  - Compute change events; MVP: simple tile risk deltas; production: deep compare + per‑tile logic.
- Step 5: `rank_by_impact(changes)`
  - Sort by severity/business impact; MVP: priority field; production: rules + learned re‑ranker.
- Step 6: `generate_digest(client_id, changes, current_snapshots, period_start, period_end)`
  - Summarize metrics, top changes, and status into a digest payload.
- Step 7: `save_digest(client_id, digest)`
  - Persist to Supabase (`weekly_pulse_digests`) and optionally index summary text in Chroma.

Daily Pulse = same pipeline with `period_days=1` and a lighter change threshold.

---

## 3) Module Map (What this pipeline depends on)

- Compliance graph and service
  - `src/exim_agent/application/compliance_service/service.py` (entrypoint; `snapshot()`)
  - `src/exim_agent/application/compliance_service/compliance_graph.py` (LangGraph; nodes)
- Domain tools (currently mock data; wire to real APIs per runbook)
  - `src/exim_agent/domain/tools/hts_tool.py`
  - `src/exim_agent/domain/tools/sanctions_tool.py`
  - `src/exim_agent/domain/tools/refusals_tool.py`
  - `src/exim_agent/domain/tools/rulings_tool.py`
- Vector storage / RAG
  - `src/exim_agent/infrastructure/db/compliance_collections.py` (Chroma collections)
  - `src/exim_agent/infrastructure/db/chroma_client.py` (shared persistent client)
- Memory (optional)
  - `src/exim_agent/application/memory_service/mem0_client.py` (Mem0 wrapper; shared client)
- Storage and retrieval (primary transactional store)
  - `src/exim_agent/infrastructure/db/supabase_client.py` (weekly pulse digests, compliance_data)
- LLM providers
  - `src/exim_agent/infrastructure/llm_providers/openai_provider.py` (current default)
  - `src/exim_agent/infrastructure/llm_providers/langchain_provider.py` (embeddings)
- API layer (to fetch digests/view status)
  - `src/exim_agent/infrastructure/api/routes/compliance_routes.py` (pulse retrieval)
- Config
  - `src/exim_agent/config.py` (.env settings for Supabase, LLMs, Chroma, Mem0)

---

## 4) Data Contracts

- Supabase
  - Table `weekly_pulse_digests` (source of truth): see `docs/WEEKLY_PULSE_IMPLEMENTATION.md` for schema and indexes.
  - Table `compliance_data`: storage for normalized source content and crawl metadata.
- Chroma (optional indexing/search)
  - Collections: `compliance_policy_snippets` (summary indexing), `compliance_events` (historical events), `compliance_hts_notes`, `compliance_rulings`, `compliance_refusal_summaries`.
- Events (optional extension)
  - Use `compliance_events` collection to persist granular change events with metadata for search.

---

## 5) Execution Flow (Weekly/Daily)

```mermaid
flowchart TD
    SCHED[Scheduler (cron/ZenML)] --> RUN[weekly_pulse_pipeline(period_days)]
    RUN --> L1[load_client_sku_lanes]
    L1 --> P1[load_previous_snapshots]
    P1 --> G1[generate_current_snapshots]
    G1 --> D1[compute_deltas]
    D1 --> R1[rank_by_impact]
    R1 --> G2[generate_digest]
    G2 --> SV[save_digest → Supabase]
    G2 -. optional .-> IX[Index digest summary → Chroma]
    SV --> API[GET /compliance/pulse/{client_id}/weekly|daily]
```

Daily vs Weekly differences:

- period_days: 1 vs 7
- thresholds: lower for Daily; more aggressive aggregation for Weekly
- optional delivery: Daily → dashboard counters; Weekly → email/Slack summary (future)

---

## 6) Minimal Wiring to Ship MVP

- Configure environment
  - `.env`: Supabase URL + anon/service keys, Chroma path, LLM keys, Mem0 toggles
- Database
  - Run `weekly_pulse_digests` migration (see `docs/WEEKLY_PULSE_IMPLEMENTATION.md`)
- Collections
  - Ensure Chroma persistent path exists; initialize via `compliance_collections.initialize()`
- Pipeline run
  - `uv run python -c "from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline; print(weekly_pulse_pipeline(client_id='demo'))"`
- API exposure
  - Use existing pulse retrieval route in `infrastructure/api/routes/compliance_routes.py`

Known MVP limits (intentional): domain tools use mock data; previous snapshot store returns empty; deltas are coarse.

---

## 7) Near‑Term Enhancements (Core MVP+)

- Replace mock tools with real adapters (see `compliance_pulse_ingestion_runbook.md`)
  - CSL (sanctions_tool) → API calls with `apikey`
  - OFAC downloads → new tool; hash‑diff + normalize; store in `compliance_data`
  - USITC HTS hydrator → API‑like endpoints + weekly snapshots
  - CBP CROSS crawler → polite crawl; HTML→Markdown; normalize
  - FDA/FSIS adapters → JSON/CSV
- Previous snapshot source
  - Use latest digest per SKU+Lane as baseline (Supabase) and/or derived `compliance_events`
- Deltas
  - Tile‑level schemas and change types; severity heuristics + learned re‑ranking
- Events
  - Persist granular events into `compliance_events` for search and drill‑down
- Delivery
  - Add `/compliance/pulse/{client_id}/daily` route and optional email/Slack notifiers

---

## 8) Aligning the Unsloth Training Program to Pulse

Goal: Optimize models for the pipeline’s two most impactful ML tasks.

- Task A: Snapshot Tile Generation (tool‑aware summarization)
  - Input: tool outputs + retrieved context
  - Output: JSON tiles (status/headline/details_md) with strict schema
  - Data: derive from staged tool outputs (mock→real), CROSS excerpts, curated rationales
  - Metrics: JSON compliance rate; hallucination rubric; citation presence; latency

- Task B: Change Ranking / Summarization
  - Input: structured deltas + tile diffs + prior snapshot
  - Output: ranked list with priority + user‑ready summaries
  - Data: heuristics as weak labels, human preference pairs for improvements
  - Metrics: ordering accuracy vs. heuristic baseline; preference win‑rate; ROUGE on summaries

Implementation path:

- SFT with Unsloth (QLoRA) on 7–9B base (Llama 3.1 8B / Qwen2.5 7B / Mistral 7B)
- Enforce JSON outputs via constrained decoding / rejection sampling in serving
- DPO/ORPO with preference pairs on digest drafts to improve prioritization and clarity
- Evaluation gates: must beat baseline on JSON compliance, summary fidelity, and latency
- Serving: vLLM/TGI with adapters; routing by task; keep current LLMs as fallback

Release cadence:

- Weekly: retrain adapters on new ingested data; shadow in pipeline; log results
- Monthly: promote best adapter versions after eval gate to production pulse runs

---

## 9) Scheduling & Operations

- Scheduler
  - ZenML schedule or system cron/K8s CronJob to call pipeline with `period_days=1|7`
- Observability
  - Log step timings and counts; write an `ingestion_log`-like row for each pulse run
- Resilience
  - Circuit breaker for external APIs; fallback to last known snapshot when tools fail
- Secrets
  - Use `.env` and provider‑specific secret stores (future: ZenML secrets manager)

---

## 10) File Checklist (Ready/Needs Work)

Ready now:

- `src/exim_agent/application/zenml_pipelines/weekly_pulse.py` (MVP pipeline)
- `src/exim_agent/application/compliance_service/service.py` (graph entry)
- `src/exim_agent/application/compliance_service/compliance_graph.py` (LangGraph nodes)
- `src/exim_agent/infrastructure/db/supabase_client.py` (pulse storage)
- `src/exim_agent/infrastructure/db/compliance_collections.py` (Chroma)
- `src/exim_agent/application/memory_service/mem0_client.py` (optional)
- `src/exim_agent/infrastructure/llm_providers/openai_provider.py`

Needs wiring to real data (replace mocks):

- `src/exim_agent/domain/tools/hts_tool.py`
- `src/exim_agent/domain/tools/sanctions_tool.py`
- `src/exim_agent/domain/tools/refusals_tool.py`
- `src/exim_agent/domain/tools/rulings_tool.py`

Optional additions:

- New `src/exim_agent/domain/tools/ofac_tool.py` (downloads/diff)
- Notifier integration (Slack/email) for weekly digests

---

## 11) Quickstart Commands

- Run API (dev): `uv run fastapi dev src/exim_agent/infrastructure/api/main.py`
- Run weekly pulse (ad‑hoc):
  - `uv run python -c "from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline; print(weekly_pulse_pipeline(client_id='demo', period_days=7))"`
- Run daily pulse (ad‑hoc):
  - `uv run python -c "from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline; print(weekly_pulse_pipeline(client_id='demo', period_days=1))"`

---

## 12) Next Actions (MVP hardening)

- [ ] Confirm Supabase table + indexes exist and RLS policy for tenants
- [ ] Parameterize client portfolio loader to DB (replace sample list)
- [ ] Replace mock tools (CSL/OFAC/USITC/CBP/FDA/FSIS)
- [ ] Implement tile‑level diffing and change taxonomies
- [ ] Add JSON schema validation for tiles/digest
- [ ] Add daily API route and optional notifications
- [ ] Set up Unsloth training repo and eval harnesses targeting Pulse tasks

---

Contact: Compliance Platform Engineering
