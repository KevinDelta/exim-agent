# Africa–US Trade Compliance Data Sources and Model Strategy

Last updated: 2025-11-06

Scope: Technical, implementation-focused guidance to (1) identify and ingest the most authoritative, up-to-date compliance and risk sources for Africa↔US trade (HTS classification, sanctions, export controls, import safety, rules of origin, and trade-lane risk signals), and (2) outline a concrete plan to transition our agents to fine‑tuned open models using Hugging Face and Unsloth.

This complements: `compliance_pulse_ingestion_runbook.md`, `docs/COMPLIANCE_INTEGRATION.md`, and `crawl4ai.md`.

---

## 1) Authoritative Sources — API First, Crawl When Needed

Below are prioritized sources with preferred extraction method, expected cadence, key fields, and integration notes. When a stable API exists, use it; otherwise, schedule polite crawls of official sites and version the results.

### 1.1 Classification & Tariffs (HTS/HS, Rulings)

- USITC HTS (United States)
  - Method: JSON endpoints driving `hts.usitc.gov` UI (API-like) + periodic bulk snapshots; crawl chapters/notes where needed.
  - Cadence: Nightly indexing + on-change snapshots.
  - Key fields: `hts_code(10)`, `desc`, `units`, `general/special rates`, `chapter notes`, `effective_from/to`.
  - Notes: USITC is the legal authority for US tariff schedule. Keep weekly full snapshots to detect structural changes and duty deltas.
  - Use: HTS classification context; duty computation; change detection in Weekly Pulse.

- CBP CROSS Rulings (classification/origin/valuation)
  - Method: Polite HTML crawl (search → detail), extract ruling metadata + full text, convert to Markdown.
  - Cadence: Daily crawl of new/updated rulings by HTS and relevant keywords.
  - Key fields: `ruling_number`, `date_issued`, `title`, `hts_refs[]`, `summary_md`, `full_text_md`.
  - Notes: Crucial training/eval corpus for HTS classification and rules-of-origin reasoning.

- Schedule B (US export stats classification)
  - Method: Crawl Schedule B search portal; keep a periodic exported copy if available.
  - Cadence: Monthly snapshot; diff vs prior.
  - Key fields: `schedule_b_code`, `hts_correlations`, `desc`.
  - Notes: Useful for export side mapping and cross-checks with HTS 10.

- HS 6-digit (WCO)
  - Method: Reference only. The WCO HS and Explanatory Notes are licensed; avoid mirroring proprietary content. Use publicly available USITC text as legal basis for US.
  - Notes: When training models, do not include WCO-proprietary text.

### 1.2 Rules of Origin & Preferential Programs (Africa focus)

- AGOA (African Growth and Opportunity Act)
  - Method: Crawl official US government and program portals (program eligibility lists, product coverage, country status changes, and ROO summaries).
  - Cadence: Monitor updates; snapshot monthly.
  - Key fields: `country`, `eligibility_status`, `effective_from/to`, `program_notes`.
  - Notes: Pair with HTS lines to compute potential preferential duty eligibility.

- AfCFTA (African Continental Free Trade Area)
  - Method: Crawl official AfCFTA/AU publications (schedules, guidance, ROO annexes). Many releases are PDFs/Excels.
  - Cadence: Quarterly snapshot; alert on new annexes/schedules.
  - Key fields: `party`, `tariff_schedule`, `roo_rulesets`, `phase`, `effective_date`.
  - Notes: Treat AfCFTA as source-of-truth for intra-Africa rules; not directly applicable to US duty but relevant to Africa-side export origin processing.

- Regional CET and ROO libraries (Africa)
  - EAC CET (East African Community), ECOWAS CET, SADC, COMESA
  - Method: Crawl official union portals (PDF/XLS tariff books; ROO annexes).
  - Cadence: Semiannual snapshot.
  - Key fields: `hs6/hs8/hs10`, `rate`, `measure`, `roo`, `footnotes`.
  - Notes: For Africa→US lanes, CETs inform origin processing and local duty/tax exposure; use for bidirectional risk summaries.

### 1.3 Sanctions & Watchlists (Global, applied to Africa–US lanes)

- ITA Consolidated Screening List (CSL)
  - Method: REST API (`api.trade.gov/consolidated_screening_list/v1/search`).
  - Cadence: Daily or on-demand screening; weekly full refresh.
  - Key fields: `name`, `source`, `programs`, `ids`, `addresses`, `last_updated`.
  - Notes: Good aggregator spanning OFAC, BIS, DDTC, and more. Keep raw responses and normalize to `party_screen`. Use an `apikey` header and `name=...` query (not `q`) to avoid redirects; confirm the current gateway path in `developer.trade.gov` docs.

- OFAC Sanctions Data
  - Method: Official data files (CSV/XML/JSON) for SDN and non-SDN lists; also use the official search API when available.
  - Cadence: Daily check; store and diff new files.
  - Key fields: `name`, `alt_names`, `program`, `country`, `ids`, `addresses`, `vessels`.
  - Notes: Use OFAC direct data as the authoritative baseline; compare with CSL to detect aggregator lags. Known working CSV export host as of 2025‑11‑06: `sanctionslistservice.ofac.treas.gov` (e.g., `/api/publicationpreview/exports/sdn.csv`).

- United Nations Consolidated List
  - Method: Official XML feed (Security Council consolidated list).
  - Cadence: Daily or weekly.
  - Key fields: `name`, `aka`, `listings`, `references`.
  - Notes: Independent baseline for multilateral alignment checks. Endpoint format has changed recently; re‑confirm the current XML/JSON URLs before wiring.

- EU Consolidated Sanctions List
  - Method: Official XML/CSV exports via EU data portal; tokenized file endpoints exist but the data.europa.eu dataset provides stable access.
  - Cadence: Daily/weekly.
  - Notes: Use for parity checks and deeper program metadata.

- UK HMT OFSI Consolidated List
  - Method: Public CSV download.
  - Cadence: Daily/weekly.
  - Notes: Additional baseline; contains program-specific notes and identifiers. Hosting path changes periodically (Azure blob → GOV.UK assets); confirm current CSV endpoint during integration.

- BIS Lists (Entity, DPL, MEU, UVL)
  - Method: Prefer CSL aggregator for operational screening. For higher-fidelity attributes, parse BIS-provided CSV/PDF postings and normalize.
  - Cadence: Weekly full; alert on change postings.
  - Notes: Entity List and MEU are critical for export-side controls and procurement risk.

### 1.4 Export Controls (EAR/ITAR)

- EAR (BIS) — Commerce Control List (CCL), Country Chart (Supp. No. 1 to Part 738)
  - Method: Crawl/parse official HTML/PDF supplements to structure ECCN→controls mapping and Country Chart matrix.
  - Cadence: Monitor BIS rule changes; snapshot with each final rule.
  - Key fields: `eccn`, `control_reasons`, `license_requirement_by_country`, `notes`.
  - Notes: Build normalized matrices for rule evaluation; version by Federal Register citation/date.

- ITAR (DDTC) — US Munitions List (USML) + Debarred List
  - Method: Crawl official USML category texts; capture Debarred List from DDTC postings (CSV/PDF).
  - Cadence: Snapshot on rule changes; Debarred List weekly.
  - Notes: Separate controlled text (USML) from list data (Debarred).

### 1.5 Import Safety & Regulatory (US)

- FDA Import Alerts
  - Method: JSON/CSV from the Import Alerts data portal (endpoint naming changed; confirm current JSON/CSV paths during setup) and CSV/JSON archives when available.
  - Cadence: Weekly; daily delta for critical alerts.
  - Key fields: `alert_number`, `country`, `product`, `reason`, `status`, `dates`.
  - Notes: High signal for lane- and product-level risk.

- USDA FSIS Import Refusals (meat/poultry/egg)
  - Method: Monthly ZIP→CSV; parse lots, countries, establishments, reasons.
  - Cadence: Monthly.
  - Notes: Add to refusal trend analysis per HS cluster.

- CPSC Recalls
  - Method: Public recall API.
  - Cadence: Weekly; daily delta.
  - Notes: Product safety signal for consumer goods.

- EPA (TSCA/chemicals)
  - Method: EPA CompTox and other REST endpoints for chemical identifiers and TSCA status.
  - Cadence: Monthly snapshot; event-driven alerts when available.
  - Notes: Useful for chemical articles, formulations, and coatings.

### 1.6 Trade-Lane Risk Signals

- UN Comtrade (Trade flows and partners)
  - Method: Public REST API.
  - Cadence: As needed; annual/batch updates.
  - Notes: Use to weight lane exposure and detect anomalous shifts.

- FATF Lists (High-Risk and Other Monitored Jurisdictions)
  - Method: Crawl official FATF notices (PDF/HTML) to extract current designations.
  - Cadence: With each plenary/release.
  - Notes: Country compliance risk input for screening thresholds and enhanced due diligence triggers.

- Forced Labor Enforcement (CBP Section 307 / UFLPA Entity List)
  - Method: Crawl official CBP/DHS postings; parse entity names and supply-chain descriptors.
  - Cadence: On update.
  - Notes: Flag SKUs and suppliers with elevated forced labor risk.

---

## 2) Extraction and Normalization Architecture

Principles: API-first; store raw responses; deterministic IDs; versioned snapshots; explicit effective dates; minimal scraping on official sources only; robust diff detection.

### 2.1 Ingestion Types

- JSON REST (preferred): CSL, FDA, UN Comtrade, some OFAC/EPA endpoints
- CSV/XML downloads: OFAC, EU/UK lists, FSIS
- HTML (crawl): USITC HTS pages/notes, CBP CROSS, AGOA/AfCFTA/CET/ROO portals, BIS/ITAR rule texts

### 2.2 Pipelines (ZenML)

Use/extend the existing `compliance_ingestion_pipeline` defined in `compliance_pulse_ingestion_runbook.md`:

1) `fetch_hts` → (USITC) query/search endpoints; weekly full snapshot; store raw
2) `fetch_csl` → (ITA CSL) API; store raw; normalize to `party_screen`
3) `fetch_ofac` → download SDN/NS-PLC files; compute hash-diff; normalize
4) `fetch_fda_refusals` → FDA API; paginate; normalize `fda_refusals`
5) `fetch_cbp_rulings` → crawl search + detail; parse; normalize `cbp_rulings`
6) `embed_all_changed` → upsert into Chroma collections
7) `commit_metrics` → write `ingestion_log`

Add Africa-focused steps:

8) `fetch_agoa_status` → crawl eligibility/program updates; normalize `pref_programs`
9) `fetch_afcfta_roo` → crawl annexes/schedules; parse ROO rulesets; normalize `roo_rules`
10) `fetch_regional_cet` → EAC/ECOWAS/SADC/COMESA tariff tables; normalize `regional_tariffs`

### 2.3 Normalized Schemas (Postgres)

Add to (or align with) schemas in `compliance_pulse_ingestion_runbook.md`:

- `party_screen(id, name, list, program, ids_json, addresses_json, last_updated, source, source_url)`
- `hts_articles(hts_code, description, duty_rate_json, units, notes_refs[], effective_from, effective_to, last_seen_at, source_url)`
- `cbp_rulings(ruling_id, date_issued, title, hts_refs[], summary_md, full_text_md, source_url, last_seen_at)`
- `fda_refusals(id, refusal_date, product_desc, firm_name, country_code, reason, port, source_url)`
- `pref_programs(program, country, eligibility, effective_from, effective_to, notes_md, source_url)`
- `roo_rules(program, hs_level, rule_text_md, rule_type, references[], effective_from, effective_to, source_url)`
- `regional_tariffs(region, country, hs_code, rate, measure, note, effective_from, effective_to, source_url)`
- `ingestion_log(run_id, source, status, row_count, started_at, finished_at, error)`

Deterministic keys:

- HTS: `hts_code` (10), scope by `effective_from/to`
- Rulings: `ruling_number`
- Parties: hash of `name+source+program`
- Pref/ROO: `program+country+hs_level+rule_hash`

### 2.4 Crawling Standards

- Only crawl official government/regulatory portals. Respect robots.txt; set `User-Agent: CompliancePulseBot/1.0 (contact: ops@… )`.
- Throttle: max 1 rps/domain; exponential backoff; retries with jitter.
- Store raw HTML/PDF/CSV and a SHA-256 content hash alongside parsed JSON.
- Normalize all dates to UTC ISO-8601; track `effective_from/to` semantics where present.
- Compute row-level diffs for alerts; persist prior snapshots for auditability.

---

## 3) Africa–US Focus: Practical Source Map (Starter Set)

This is a pragmatic starting inventory to operationalize Africa↔US lanes. Most items below are either APIs or stable official publications suitable for crawling and parsing.

- United States
  - USITC HTS (classification/duty) — API-like + crawl for notes
  - CBP CROSS rulings — crawl
  - ITA CSL — API
  - OFAC SDN/non-SDN — CSV/XML download
  - FDA Import Alerts — JSON API
  - USDA FSIS import refusals — ZIP→CSV
  - CPSC Recalls — API
  - BIS EAR (CCL, Country Chart) — crawl rule texts
  - DDTC USML + Debarred List — crawl download

- Pan‑Africa / Regional
  - AfCFTA schedules/annexes — crawl
  - EAC CET and ROO — crawl
  - ECOWAS CET — crawl
  - SADC/COMESA tariff books and ROO — crawl

- Country exemplars (prioritize based on customer lanes)
  - South Africa (SARS tariff book) — crawl
  - Kenya (KRA; EAC CET application) — crawl
  - Nigeria (NCS; ECOWAS CET) — crawl
  - Ghana (GRA; tariff/ROO notices) — crawl
  - Ethiopia, Egypt, Morocco, Tanzania, Uganda — track local customs portals for tariff/ROO docs

---

## 4) Evaluation-Ready Datasets (What We Will Build)

We will curate internal, versioned datasets suitable for training and regression testing:

- HTS Classification Pairs
  - Inputs: product title + description + attributes; optional supplier/manufacturer
  - Labels: HTS 10, rationale snippet (from USITC text or CROSS excerpts)
  - Sources: CROSS rulings (public text), USITC HTS articles/notes (public text), customer-provided SKUs (non-public)

- Sanctions Entity Matching
  - Inputs: name + address + country + fuzzy variants
  - Labels: match/no-match + list/program + rationale
  - Sources: CSL + OFAC/EU/UN/UK direct lists; synthetic fuzzed variants for robustness

- Rules of Origin Eligibility (Program-specific)
  - Inputs: program (AGOA, regional ROO), HS level (6/8/10), product/process notes
  - Labels: determined by explicit rule text. Train only as assistant to deterministic rules.

- Risk Summarization
  - Inputs: tool outputs (tiles), change-diffs, refusals, alerts
  - Labels: target snapshot tiles with status/headline/details; preference pairs for style and factuality

All datasets: JSONL with explicit `source_ref`, `effective_date`, `license`, `split`.

---

## 5) Model Replacement Plan (Hugging Face + Unsloth)

Goal: Replace proprietary LLMs powering agents with specialized, fine‑tuned open models that excel at: (1) HTS suggestion with citations, (2) sanctions/entity risk adjudication, (3) compliance snapshot summarization with tool-awareness, and (4) ROO guidance assistance.

### 5.1 Base Model Selection

- Candidate 7–9B Instruct models (primary tier)
  - Llama 3.1 8B Instruct, Mistral 7B Instruct, Qwen2.5 7B Instruct
  - Pros: Fits 24GB GPUs with QLoRA; fast; sufficient for tool-aware summarization and entity adjudication with good RAG

- Candidate 12–70B (secondary tier for highest accuracy)
  - Mixtral 8x7B, Llama 3.1 70B Instruct (where permitted)
  - Pros: Higher reasoning; Cons: serving cost/latency; use for batch adjudication or high-stakes flows

Constraints: Respect model licenses; avoid weights that restrict commercial use if not acceptable.

### 5.2 Fine‑Tuning with Unsloth (QLoRA)

- Setup
  - Use Unsloth for memory‑efficient adapters (QLoRA, 4‑bit) and fast SFT/DPO loops
  - Store adapters and merged weights in private Hugging Face repos (git‑LFS)

- Supervised Fine‑Tuning (SFT)
  - Data: domain instruction data (classification pairs, sanctions adjudication, snapshot generation)
  - Config (typical for 7B): `lora_r=16`, `lora_alpha=32`, `lr=2e-4`, `seq_len=4096`, `bf16`, `grad_accum` tuned to GPU
  - Prompt templates: Align with our LangChain chat template; enforce JSON outputs for tool calls

- Preference Optimization (DPO/ORPO/SimPO)
  - Data: preference pairs for factuality and citation quality on compliance tiles
  - Use TRL integration via Unsloth wrappers

- Evaluation
  - HTS: top‑1/top‑3 accuracy at HS‑6/HTS‑10; rationale BLEU/ROUGE
  - Sanctions: P/R/F1 and AUC on match pairs; calibration analysis
  - Summarization: rubric scoring + rule‑based hallucination checks; exact JSON compliance rate
  - ROO Assist: unit tests against deterministic rule engines (no freeform answers where rules are strict)

- Infrastructure
  - 7B SFT: 1× RTX 4090 (24GB) or A100 (40GB); 1–3 hours per epoch depending on corpus
  - 70B adapters: A100 80GB or multi‑GPU; batch offline only

### 5.3 Serving and Integration

- Engines: vLLM or TGI with LoRA adapter support; dynamic batching; token‑aware max concurrency
- Quantization: AWQ or GPTQ for merged weights; consider fp8 for server‑side if available
- Function calling: enforce JSON Schema for tile generation; reject‑sampling layer for strict formats
- RAG: continue to use ChromaDB; consider reranking for long contexts
- Rollout strategy: route by task → A/B shadow → canary → full; maintain fallback to current LLMs

### 5.4 Model Governance

- Registry: Hugging Face private org; signed artifacts; semantic versioning
- Cards: detailed model cards with datasets, licenses, and evals
- Telemetry: request/response metrics, error codes, JSON compliance rate
- Safety: blocklists for exfiltration; red‑team prompts around sanctions guidance

---

## 6) Implementation Checklists

### 6.1 Data Adapters (near‑term)

- [ ] Replace `sanctions_tool.py` mock with real CSL API calls (API key in `config.py`)
- [ ] Add OFAC tool for SDN/non‑SDN downloads (hash‑diff + normalize)
- [ ] Implement USITC HTS search + hydrator (API‑like endpoints; weekly snapshots)
- [ ] Build CBP CROSS crawler/parser with polite throttling and HTML→Markdown
- [ ] Add FDA Import Alerts adapter (JSON)
- [ ] Add FSIS import refusals (ZIP→CSV)
- [ ] Add AfCFTA/AGOA/Regional CET crawlers (+ ROO parser for annex PDFs)

### 6.2 Storage & Indexing

- [ ] Create Postgres tables listed above via Alembic migration
- [ ] Persist raw files under `data/raw/{source}/YYYYMMDD/…` with SHA‑256
- [ ] Upsert normalized docs into Chroma with deterministic IDs and metadata

### 6.3 Model Program

- [ ] Curate v1 HTS pairs from CROSS + USITC text
- [ ] Curate v1 sanctions match pairs from CSL + OFAC/EU/UN/UK
- [ ] Define JSON output schemas for all tile types; add format validators
- [ ] Train 7B SFT adapters (Unsloth) for three tasks: HTS, sanctions, snapshot
- [ ] Add eval harnesses and CI check on JSON compliance + task metrics
- [ ] Stand up vLLM/TGI service with adapter routing; wire into LangGraph

---

## 7) Verification Notes (to operationalize now)

For each source above, confirm current endpoints, formats, and rate limits before going live. Critical checks:

- ITA CSL API base path, query params, pagination
- OFAC data file URLs (CSV/XML) and any search API details
- UN consolidated XML availability
- UK HMT CSV stability
- FDA Import Alerts JSON structure
- USITC HTS UI JSON endpoints used by `hts.usitc.gov`
- CBP CROSS HTML layout/fields
- EU data portal dataset link for consolidated sanctions

Automate with a small script that performs HEAD/GET with retry and records status, `Content-Type`, and byte size. Store a `fetch_manifest_*.json` alongside raw data for each run.

---

## 8) Caveats & Compliance

- Do not ingest proprietary WCO HS Explanatory Notes or paid datasets.
- Sanctions guidance must not be treated as legal advice; summarize with citations and link to authoritative sources.
- Respect robots and site terms for all crawls; throttle appropriately and identify the bot.
- Maintain complete raw snapshots for auditability; compute deltas for user‑visible digests.

---

## 9) Pointers in This Repo

- Domain tools (stubs/mocks today): `src/exim_agent/domain/tools/*.py`
- Sanctions tool using CSL (replace mocks): `src/exim_agent/domain/tools/sanctions_tool.py`
- Ingestion runbook with schemas: `compliance_pulse_ingestion_runbook.md`
- Integration guide (LangGraph/Chroma/Mem0): `docs/COMPLIANCE_INTEGRATION.md`
- Crawling helper example: `crawl4ai.md`

---

Contact: Compliance Platform Engineering
