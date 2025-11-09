# Compliance Agent MVP Simplification Review

This document captures the implementation work that stripped the Crawl4AI/ZenML stack, replaced it with on-demand digests, and trimmed storage/services down to the MVP core. It now serves as the summary of what changed plus any remaining follow-ups.

## Executive Summary

- ZenML pipelines, crawl routes, and all Crawl4AI-powered crawlers were deleted. The only compliance data acquisition now goes through the existing lightweight tools (HTS, sanctions, rulings, refusals).
- Weekly/daily/latest digests are handled by `application/compliance_service/digest_service.py`, which wraps snapshot generation, delta computation, and Supabase persistence with a single `generate_digest_for_period()` call.
- `/compliance/pulse/*` endpoints invoke the new service, optionally persist to Supabase, and fall back to stored digests when available. No ZenML runner or Supabase-only pathway remains.
- `supabase_client.py` was reduced to the helpers actually used by the MVP (compliance data cache, digest storage, client portfolio lookup). Crawl/change-detection/versioning logic was removed.

## Final Architecture Snapshot

### Digests

- `src/exim_agent/application/compliance_service/digest_service.py` encapsulates SKU/lane loading, snapshot generation, change detection, ranking, digest assembly, and (optional) Supabase persistence.
- API routes:
  - `GET /compliance/pulse/{client_id}/weekly|daily` call `generate_digest_for_period()` with `period_days=7|1`, default to on-demand output, and can opt into persistence via query flag.
  - `GET /compliance/pulse/{client_id}/latest` prefers the most recent stored digest, falling back to a new weekly digest if none exist.
- Supabase digest storage is optional; when the client is not configured, routes return computed digests without error.

### Compliance Graph & Tools

- LangGraph state machine (`compliance_graph.py`) and the HTS/sanctions/refusals/rulings tools remain the only source of compliance data. No Crawl4AI hooks remain in the repo.
- Snapshot API continues to call `ComplianceService.snapshot()`, which internally invokes the same tools.

### Infrastructure

- `supabase_client.py` now exposes `store_compliance_data`, digest helpers, and `get_client_portfolio` plus a simple `is_configured` flag. All change-detection/crawl metadata helpers were removed.
- `compliance_collections.initialize()` lazily initializes the shared Chroma client when needed so tests can run without pre-starting Chroma.
- `pyproject.toml` no longer lists `zenml`, `mlflow`, or `crawl4ai` dependencies; docs and scripts referencing them were removed alongside the make target.

## Removed Surface Area

- Crawl4AI client, domain crawlers, and crawl service/routes
- All ZenML pipeline modules (`application/zenml_pipelines/*`), admin pipeline endpoints, and crawl/admin pipeline tests
- Crawl-focused migrations/docs (`docs/crawl4ai.md`, `docs/WEEKLY_PULSE_IMPLEMENTATION.md`, etc.)
- `tests/test_compliance_pipelines.py`, `tests/test_admin_api.py`, and other suites that only targeted the deleted endpoints

## Follow-ups / Nice-to-haves

1. Optional WebSearch/Fetch tools for the LangGraph agent when dynamic discovery becomes necessary (not yet implemented).
2. Regenerate `uv.lock` to drop the removed dependencies.
3. Provide a local testing profile (env vars + cached tiktoken assets) so CI can run `pytest` offline without hitting OpenAI.

With these changes, the repo now reflects the lean MVP: LangGraph + domain tools feed on-demand digests, Supabase is purely optional persistence, and there is no parallel crawling/pipeline system to maintain.

## What To Keep vs Remove (MVP)

Keep (essential)

- LangGraph compliance graph: `src/exim_agent/application/compliance_service/compliance_graph.py:1`
- Compliance service wrapper: `src/exim_agent/application/compliance_service/service.py:1`
- Domain tools (simple, direct):
  - `src/exim_agent/domain/tools/hts_tool.py:1`
  - `src/exim_agent/domain/tools/sanctions_tool.py:1`
  - `src/exim_agent/domain/tools/rulings_tool.py:1`
  - `src/exim_agent/domain/tools/refusals_tool.py:1`
- Digest computation logic in `weekly_pulse.py` (as plain functions), and API endpoints in `compliance_routes.py`.
- Chroma collections (for RAG) and the minimal ingestion endpoint if you actually need RAG content during MVP demos.

Remove (defer until scale)

- Crawl4AI + per-domain crawlers:
  - `src/exim_agent/infrastructure/crawl4ai/*`
  - `src/exim_agent/domain/crawlers/*`
  - `src/exim_agent/application/crawl_service/*`
  - `src/exim_agent/infrastructure/api/routes/crawl_routes.py:1`
- ZenML ingestion/analytics pipelines and wrappers (keep weekly/daily digest as direct function calls):
  - `src/exim_agent/application/zenml_pipelines/compliance_ingestion.py:1`
  - `src/exim_agent/application/zenml_pipelines/ingestion_pipeline.py:1`
  - `src/exim_agent/application/zenml_pipelines/memory_analytics_pipeline.py:1`
  - `src/exim_agent/application/zenml_pipelines/runner.py:1` (or keep as a no‑op shim)
- Supabase crawling/versioning bloat: remove change detection, content hashing, content version tables from MVP path in `src/exim_agent/infrastructure/db/supabase_client.py:1` (retain only digest store/retrieve if persistence is required now).
- Optional Chroma indexing of digests inside `save_digest` (keep it out until you actually need semantic search over digests).

Refactor (slim down)

- `weekly_pulse.py:1` → convert to a simple service function `digest_for_period(client_id, period_days)` callable from API; keep steps minimal (load sku_lanes → generate current snapshots → compute basic deltas → rank → generate JSON). Make Supabase persistence optional via a flag.
- `compliance_routes.py:1` →
  - GET `/pulse/{client_id}/weekly|daily` should call `digest_for_period` on‑demand by default, with `persist=true` if you want to save.
  - If `SUPABASE_URL` not configured, return on‑the‑fly digest and skip persistence.

## Replace Crawl4AI With Agent Tools (MVP)

Introduce two generic tools for the LangGraph agent (only when needed):

- WebSearchTool: wraps your preferred provider (Tavily, Serper, Brave) with simple `query -> urls` behavior.
- FetchURLTool: minimal `httpx` GET with content cleanup (plus optional readability extraction). No headless browser or JS orchestration unless strictly needed.

Wire them into the graph when discovery is required (e.g., to find recent refusals pages or rulings URLs). Given your domain tools already scrape known endpoints, WebSearchTool can be deferred until you actually need dynamic discovery.

Benefits

- Removes AsyncWebCrawler orchestration, LLM extraction schemas, and per‑domain crawling code paths.
- Zero duplication: the agent either calls existing domain tools, or searches and fetches when the destination isn’t yet encoded.
- Reduces maintenance and security surface area (no extra browser runtime in API).

## Proposed Minimal Digest Flow (MVP)

API calls into a thin service, no ZenML required:

1) Load SKU+lane list
   - MVP: hardcoded fixtures or `supabase_client.get_client_portfolio` only when Supabase is configured.
2) For each SKU+lane, call `ComplianceService.snapshot()` (already wraps LangGraph + tools).
3) Compute basic deltas vs. previous snapshot if available.
   - MVP: if no previous snapshot, treat as “new_monitoring”.
4) Rank: simple priority ordering by `high > medium > low`.
5) Return digest JSON. Optionally `persist=true` to call `store_weekly_pulse_digest`.

Files involved

- `src/exim_agent/application/compliance_service/service.py:24` (snapshot entrypoint)
- `src/exim_agent/application/zenml_pipelines/weekly_pulse.py:1` (rehome core logic to a plain service function)
- `src/exim_agent/infrastructure/api/routes/compliance_routes.py:1` (call the service directly)
- `src/exim_agent/infrastructure/db/supabase_client.py:1` (keep only minimal digest methods for MVP)

## De‑Bloat Plan (Concrete Tasks)

Phase 1 — Remove Crawl4AI stack

- Delete: `src/exim_agent/infrastructure/crawl4ai/*` and `docs/crawl4ai.md:1`.
- Delete: `src/exim_agent/domain/crawlers/*`.
- Delete: `src/exim_agent/application/crawl_service/*` and `src/exim_agent/infrastructure/api/routes/crawl_routes.py:1`.
- Scrub references:
  - `src/exim_agent/application/zenml_pipelines/compliance_ingestion.py:1` (remove Crawl4AI usage or remove the whole file as part of Phase 2).
  - `src/exim_agent/infrastructure/__init__.py:3` (remove Crawl4AI exports).

Phase 2 — Simplify digests to on‑demand service

- Refactor `weekly_pulse.py:1` into `application/compliance_service/digest_service.py` with a single function `digest_for_period(client_id, period_days, persist=False)` using existing step logic (no ZenML annotations). Keep the code paths and signatures minimal.
- Update API in `compliance_routes.py:1` to call this function directly for weekly/daily. Add a query flag `persist` (default false). If Supabase isn’t configured, skip writes.
- keep as thin shims:
  - `src/exim_agent/application/zenml_pipelines/runner.py:1`
  - ZenML decorators in digest code.

Phase 3 — Trim Supabase client to essentials

- Keep only: `store_weekly_pulse_digest`, `get_weekly_pulse_digests`, `get_latest_digest`, `get_client_portfolio`.
- Remove: crawling/change‑detection/versioning helpers, content hashing, and logging tables from the MVP path (they can live on a branch).

Phase 4 — Add generic WebSearch tool

- Add two simple tools and wire to graph only as needed:
  - `WebSearchTool` (Tavily provider behind env flag; no provider → disabled).
  - `FetchURLTool` (thin `httpx` wrapper with 10–15 line cleanup).

## Risk/Impact Notes

- Tests that exercise ZenML endpoints or crawl routes will need to be removed/updated. The API tests for snapshot and pulse should continue to work if we keep endpoints but switch their internals to on‑demand computation.
- If you rely on Supabase dashboards for pulse history today, keep persistence enabled; otherwise, you can run entirely stateless digests initially.

## Quick Wins (1–2 days)

- Remove Crawl4AI folders and crawl routes; CI gets lighter immediately.
- Inline weekly/daily digest computation into an `application` service and call from API.
- Strip Supabase client to digest‑only methods to avoid config/credential friction during local dev.

## Suggested File Changes (Summary)

Delete

- `src/exim_agent/infrastructure/crawl4ai/*`
- `src/exim_agent/domain/crawlers/*`
- `src/exim_agent/application/crawl_service/*`
- `src/exim_agent/infrastructure/api/routes/crawl_routes.py`
- `src/exim_agent/application/zenml_pipelines/compliance_ingestion.py`
- `src/exim_agent/application/zenml_pipelines/memory_analytics_pipeline.py`

Refactor

- Move `weekly_pulse.py` core logic to `application/compliance_service/digest_service.py` and remove ZenML decorators.
- Update `compliance_routes.py` to compute digests on demand and (optionally) persist via Supabase if configured.
- Trim `supabase_client.py` to digest helpers only.

Add (optional, behind env flags)

- `domain/tools/web_search_tool.py` (simple provider-backed search)
- `domain/tools/fetch_url_tool.py` (thin `httpx` fetcher)

## FAQ

- Why remove Crawl4AI now?
  - It duplicates capability the domain tools already provide, adds a headless browser runtime and LLM extraction layers, and complicates API + ingestion without near-term ROI for MVP.

- Do we still get weekly/daily digests?
  - Yes. The same step logic runs as a small service callable by API. Persistence is optional.

- What about scaling later?
  - The plan preserves LangGraph + tool boundaries so you can reintroduce batch orchestration, scheduled pipelines, and richer storage when you have usage pressure.

---

If you want, I can implement Phase 1–2 now in a focused PR: remove Crawl4AI, convert weekly/daily to on‑demand, and trim Supabase client to digest helpers only.
