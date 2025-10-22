# Memory-First LLM Punch List (LangChain/LangGraph + Chroma + Neo4j)

A practical, testable, **anthropomorphic memory** implementation plan. Each principle below includes: **build tasks**, **LangGraph/LangChain wiring**, **store design**, **algos/APIs**, and **provable metrics** with “done-when” checks.

---

## 0) Repo & Runtime Skeleton (one-time setup)

Folders

```bash
/apps
  /broker      # Memory Broker FastAPI
  /service     # LangGraph app
/evals         # golden set + harness
/infra         # docker-compose, neo4j, chroma
/shared        # schemas, clients, utils
```

Key deps

- `langchain`, `langgraph`, `langchain-openai` (or your chosen LLM/embedding client)
- `chromadb` (or `lancedb` if preferred), `neo4j`
- `pydantic`, `fastapi`, `uvicorn`
- `pandas` (evals), `scikit-learn` (metrics), `rank_bm25`
- Optional reranker: `sentence-transformers` (bge-reranker) or API (Cohere Rerank)

Env

```bash
OPENAI_API_KEY=...
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASS=...
CHROMA_HOST=chroma
CHROMA_PORT=8000
```

Docker-compose (infra/compose.yml)

```yaml
services:
  neo4j:
    image: neo4j:5
    ports: ["7474:7474","7687:7687"]
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASS}
  chroma:
    image: chromadb/chroma:latest
    ports: ["8000:8000"]
  broker:
    build: ./apps/broker
    environment: [...]
  service:
    build: ./apps/service
    environment: [...]
```

---

## 1) Locality & Hierarchical Caching  
Goal: “Right memory, right tier, right now.”

### Build
- Pinned context: Create a small, versioned file `/shared/pinned/system_prompts.yml` for policy, persona, tool schemas (≤1k tokens).
- Session prefix cache: Keep last N distilled bullets per session in a lightweight store (Redis or a Chroma collection `episodic_sessions` with `ttl`).
- Two-stage recall: BM25 (fast filter) → Vector (semantic) → optional rerank → final K (8–15).
- Graph-guided seed: If entities detected (Shipper=A, Port=Durban), expand 1-hop in Neo4j and add those IDs as filters to vector search.

### LangGraph wiring
```python
# service/graph.py
from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict, Any

class MemoryState(TypedDict):
    user_msg: str
    intent: str
    wm_notes: List[str]
    em_digest: List[str]
    evidence: List[Dict[str, Any]]  # [{text, source, entity_ids}]
    entities: List[Dict[str, Any]]
    answer: str
    citations: List[Dict[str, Any]]

g = StateGraph(MemoryState)

def classify_intent(state): ...
def entity_link(state): ...
def fast_filter_bm25(state): ...
def vector_search(state): ...
def graph_expand(state): ...
def rerank_and_trim(state): ...
def compose_prompt(state): ...
def llm_answer(state): ...

g.add_node("classify_intent", classify_intent)
g.add_node("entity_link", entity_link)
g.add_node("fast_filter_bm25", fast_filter_bm25)
g.add_node("vector_search", vector_search)
g.add_node("graph_expand", graph_expand)
g.add_node("rerank_and_trim", rerank_and_trim)
g.add_node("compose_prompt", compose_prompt)
g.add_node("llm_answer", llm_answer)

g.add_edge("classify_intent","entity_link")
g.add_edge("entity_link","fast_filter_bm25")
g.add_edge("fast_filter_bm25","vector_search")
g.add_edge("vector_search","graph_expand")
g.add_edge("graph_expand","rerank_and_trim")
g.add_edge("rerank_and_trim","compose_prompt")
g.add_edge("compose_prompt","llm_answer")
```

### Stores & APIs
- Chroma collections: `docs_sm`, `episodic_sessions`.
- Neo4j: `(:Entity {id,type,name})`, relationships `(:Entity)-[:RELATES_TO]->(:Entity)`.
- Broker endpoints: `POST /recall` accepts `{query, tags[], entity_ids[]}` and performs 2-stage + optional graph expansion.

### Metrics
- Context tokens added (avg, p95)
- **Retrieval latency** (ms) split by stage (BM25/vector/rerank)
- **Hits@k / Precision@k** on eval set (see Section 9)
- **Done-when:** tokens cut ≥30% with equal or better Precision@k.

---

## 2) Compression & Distillation  
Goal: “Remember less, mean more.”

### Build
- Episodic summarizer node that appends 3–6 bullet “facts learned” with stable IDs to `episodic_sessions`.
- Entity normalization: NER + canonicalization; write EAV facts to Neo4j `(:Fact)` with provenance.
- Atomic notes: store small, immutable facts instead of blobs.
- **Salience score** increments whenever an item is retrieved & cited.

### LangChain bits
- LLM chain `summarize_session(messages) -> bullets`
- NER via LLM function call or spaCy; canonicalization via synonym table or graph lookup.

### Metrics
- **Tokens per prompt** pre/post summarization
- **Duplicate-fact rate** (same EAV different surface forms)
- **Groundedness**: % answers with ≥2 distinct citations
- **Done-when:** ≥50% context shrink with no drop in groundedness on evals.

---

## 3) Sparse / Conditional Recall  
Goal: Only fetch what the current intent needs.

### Build
- Intent → memory profile map in YAML:
```yaml
profiles:
  quote_request:
    k_fast: 200; k_vec: 24; k_final: 12
    filters: ["intent:quote"]
    graph_hops: 1
    reranker: cross_encoder_mini
  compliance_query:
    k_fast: 300; k_vec: 32; k_final: 15
    filters: ["intent:compliance"]
    graph_hops: 2
    reranker: cross_encoder_large
```
- **TTL by layer**: EM entries expire in X days; SM never expires but demotes if unused.
- **Conflict guard**: suspected contradictions spawn `verify_update` task (tool-assisted or human).

### Metrics

- **Over-fetch ratio** = tokens retrieved but never cited / tokens retrieved
- **Precision@k** by intent
- **Done-when:** over-fetch ↓ by ≥40% with same/better Precision@k.

---

## 4) Memory-Centric Architecture  
Goal: Memory as a first-class API with schemas, policies, and tests.

### Build

- Memory Broker (FastAPI)
  - `POST /write` `{layer: EM|SM, items: [...]}`
  - `POST /recall` `{query, profile, entity_ids[], tags[]}`
  - `POST /promote` `{id}`
  - `POST /decay` `{id}`
- **Schemas**

```json
// Vector item
{
  "id": "uuid",
  "text": "string",
  "embedding": [0.0],
  "entity_ids": ["E:123"],
  "tags": ["intent:quote","lane:durban"],
  "salience": 0.73,
  "ttl": "2025-12-31",
  "provenance": {"doc_id":"pvoc_v3","page":12,"url":"...","hash":"..."}
}
```
- **Policy:** write-through EM→SM only after (salience ≥ S AND verified).

### Metrics

- **API p95** latency per endpoint
- **Write→promote lead time** (days)
- **Audit completeness**: % items with provenance
- **Done-when:** 100% provenance on SM; broker p95 < 150 ms.

---

## 5) Streaming & Overlap

Goal: Retrieve while answering; splice evidence mid-stream.

### Build

- **Parallel nodes**: kick off retrieval, entity linking, rerank concurrently.
- **Progressive prompt**: reserved “Evidence” section appended during streaming; model instructed to consult when updated.
- **Pre-warm**: on intent detection, prefetch likely tags before LLM call.

### LangGraph tweak

```python
g.add_edge("classify_intent","vector_search")   # fire early
g.add_edge("classify_intent","fast_filter_bm25")
g.add_edge("classify_intent","graph_expand")
# Compose & answer can start with WM/EM; evidence may be appended via callbacks
```

### Metrics

- **First token latency** (ms)
- **Retrieval-arrived-too-late** count
- **p95 total latency** vs non-streaming baseline
- **Done-when:** first-token ↓ ≥20% with unchanged answer quality.

---

## 6) Offload & Swapping (Hot/Warm/Cold)  

Goal: Keep only hot memories close; demote the rest.

### Buildd

- **Tiers**
  - **Hot (WM/EM):** session digest bullets; Redis/Chroma with TTL
  - **Warm (SM-vector):** stable facts + summaries
  - **Cold (Graph + object store):** full docs, logs
- **Promotion rule**: EM item referenced ≥X times in 7 days → promote to SM (after verify).
- **Snapshot/restore**: serialize `MemoryState` for session continuity.

### Metrics

- **Hot hit-rate** (% recalls served from EM)
- **Memory growth slope** (items/week) vs usage
- **Restore fidelity** (same answer on replay)
- **Done-when:** hot hit-rate ≥60% on repeat users; growth sublinear.

---

## 7) Algorithm–Application Co-Design  

Goal: Prompts, chunking, tools that respect memory limits and truth.

### Builds

- **Task-specific prompts**: tight, schema-aware; enforce “use cited evidence only.”
- **Chunking**: semantic chunker with section-aware overlap; chunk metadata includes `{section, lane, regulation, hs_code}`.
- **Rerankers > bigger windows**: add cross-encoder rerank step before stuffing context.
- **Tool schemas**: tool outputs are JSON, tiny, and summary-ready (feed EM).

### LangChain snippets

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
chunks = splitter.split_text(doc_text)
# attach domain metadata before embedding -> higher precision filters
```

### Metric

- **Tokens/response** (avg, p95)
- **Hallucination rate** on evals (manual/heuristic)
- **Citation density** (# evidence per answer)
- **Done-when:** tokens ↓ ≥25% and hallucinations ↓ on evals.

---

## 8) Scalable Interconnects (Vector + Graph + SQL)  
Goal: Federate memories without turning them into soup.

### Build

- **Broker fan-out**: vector → graph neighbors → optional SQL verify (e.g., rate tables, KPIs).
- **Global IDs**: stable `entity_id` used across all stores; vector chunks carry `entity_ids[]`.
- **Join patterns**:
  1) Vector top-k → get `entity_ids[]`
  2) Graph expand 1–2 hops
  3) SQL verify a small set of facts (e.g., “PVOC required?”)

### Metrics

- **End-to-end recall latency** (ms)
- **Cross-store consistency rate** (vector→graph→SQL alignment)
- **Done-when:** p95 < 500 ms for federated recall; consistency ≥ 95%.

---

## 9) Evals & KPIs (provable wins)

Golden set format (`/evals/gold.jsonl`)

```json
{"qid":"q001","intent":"quote_request","query":"Quote to ship electronics to Durban under DDP","answers":["..."],"must_cite":["pvoc_v3#p12"]}
```

Harness (pseudo)

```python
for q in golden:
    out = service.answer(q["query"])
    record({
      "qid": q["qid"],
      "latency_ms": out.ms,
      "tokens_in": out.tokens_in,
      "tokens_ctx": out.tokens_ctx,
      "citations": out.citations,
      "correct": judge(out.text, q["answers"]),
      "must_cited": all(cid in out.citations for cid in q["must_cite"])
    })
```

Core KPIs

- Precision@k / MRR for retrieval
- Groundedness = % answers with ≥2 citations + must-cite satisfied
- Tokens in context (avg/p95)
- Latency (p50/p95), first-token
- Over-fetch ratio
- Hot hit-rate
- Drift/contradiction rate in SM writes

CI rule of thumb

- Fail PR if Precision@k drops >1.5% or Groundedness drops >2% or p95 latency increases >10% on the eval set.

---

## 10) Document Ingestion Pipeline (SM + Graph)

Steps

1) Parse & chunk docs with section metadata.  
2) Embed & upsert to `docs_sm` (Chroma) with `{entity_ids[], tags[], provenance}`.  
3) Entity & fact extract → `(:Entity)`, `(:Fact)` in Neo4j; link `SUPPORTED_BY` to `(:Doc)`.  
4) Doc digest (2–6 bullets) → seed EM for that domain.

**Done-when**: ingestion throughput meets SLA; re-ingest updates entities without dupes; evals show higher Precision@k after graph expansion.

---

## 11) Memory Broker (FastAPI) sketch

```python
# apps/broker/main.py
from fastapi import FastAPI
app = FastAPI()

@app.post("/recall")
def recall(req: RecallRequest):
    cands = bm25(req.query, req.filters, k=req.profile.k_fast)
    vec = vector_topk(req.query, cands, k=req.profile.k_vec)
    if req.profile.graph_hops>0:
        vec = graph_expand(vec, hops=req.profile.graph_hops)
    final = rerank(vec, k=req.profile.k_final, model=req.profile.reranker)
    return final

@app.post("/write")
def write(req: WriteRequest): ...
@app.post("/promote")
def promote(req: PromoteRequest): ...
@app.post("/decay")
def decay(req: DecayRequest): ...
```

Logs: every mutation (write/promote/decay) must record `{actor, time, provenance}` for audits.

---

## 12) Admin UI (thin, essential)

- Browse **EM/SM** items; promote/demote; view **provenance**.
- Contradiction queue: approve/deny **verify_update**.
- Metrics dashboard: KPIs in Section 9 with 7-day trend.

---

## 13) Security & Governance (non-negotiable)

- **PII redaction** on write; **encrypt at rest** for SM/EM.  
- **Provenance required** for SM writes.  
- **TTL & decay** enforced via scheduled jobs.  
- **Access control**: per-tenant collections, graph labels scoped by tenant.

**Done-when:** no SM item exists without provenance; per-tenant isolation verified by tests.

---

## 14) Sprints & “Definition of Done”

Sprint 1 – Broker + Basic Retrieval

- Two-stage recall + rerank, pinned prompts, session prefix cache.
- DoD: Precision@k ≥ baseline + 10%; p95 recall < 450 ms.

Sprint 2 – EM/SM Writes + Distillation

- Episodic summarizer, salience, promotion rules.
- DoD: tokens/ctx ↓ ≥30% with stable groundedness.

Sprint 3 – Graph Integration

- Entity normalization, 1–2 hop expansion, contradiction guard.
- DoD: Precision@k + 8% vs vector-only; conflict handler functional.

Sprint 4 – Streaming & Splice

- Parallel retrieval; progressive evidence section; pre-warm.
- DoD: first-token ↓ 20% with no quality loss.

Sprint 5 – Admin + Evals CI

- Admin UI, nightly evals, CI gates.
- DoD: CI blocks regressions; dashboard shows all KPIs.

---

## 15) Defaults & Good-Enough Choices (so you ship)

- **Embeddings:** `text-embedding-3-large` (or `bge-large-en-v1.5` if local).  
- **Reranker:** `bge-reranker-large` local or Cohere Rerank.  
- **Chunking:** 700–900 chars, 100–150 overlap, section-aware.  
- **K values:** fast=200, vec=24–32, final=10–15.  
- **EM TTL:** 7–14 days; **promote threshold:** 3 uses/week.  
- **Must-cite**: at least 2 distinct sources for compliance answers.

---

## 16) What to watch out for (hard truths)

- Vector stores drift into mush if you skip **entity normalization** and **provenance**.  
- Bigger windows are a trap; rerank + better filters beat token bloat.  
- Without eval gates, “improvements” regress silently; ship the harness early.

---

This is the spine of a **Memory-First RAG** platform you can implement and sell. Next natural step is a starter repo with the Broker, LangGraph graph, ingestion script, and the eval harness wired up so you can benchmark changes in hours, not weeks.
