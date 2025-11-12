# Production MVP Architecture

This document describes a clean, production‑oriented MVP flow for the compliance agent. It focuses on a small set of
well‑bounded responsibilities, predictable control flow, and safe fallbacks. The goal is to keep behavior reliable in
real deployments while leaving clear seams for future upgrades.

## Objectives

- Single conversational entrypoint that can handle general questions and compliance tasks.
- Deterministic, tool‑driven compliance workflow for snapshots and domain Q&A.
- Conservative routing: never fabricate identifiers or context; ask for missing slots.
- Minimal dependencies at runtime; graceful degradation when providers or stores are unavailable.
- Clear state contracts and simple nodes that are easy to test.

## High‑Level Flow

1. User sends a message to the Chat Assistant.
2. Chat Graph decides whether to handle the request with general RAG or delegate to the Compliance Workflow.
3. If delegating, the Compliance Graph runs tools/RAG, builds a snapshot or answers a domain question, and returns a
   structured result.
4. Chat Graph assembles a user‑friendly response and updates Mem0 (if enabled).

## Components

### Chat Assistant (Chat Graph)

- File: `src/exim_agent/application/chat_service/graph.py`
- Responsibilities:
  - Serve as the top‑level orchestrator for all user requests.
  - Maintain conversational memory with Mem0 (optional; never blocking).
  - Perform light RAG over enterprise documents for general questions.
  - Route to compliance when the request is explicitly compliance‑related and has required identifiers.
- State (MVP):
  - Inputs: `query`, `user_id`, `session_id`, optional `client_id`, `sku_id`, `lane_id`.
  - Memory/RAG: `relevant_memories`, `rag_context`, `final_context`.
  - Outputs: `response`, `citations`, optional `snapshot` (if compliance delegated).
- Nodes (MVP):
  - `route`: Pure decision point. No side effects.
  - `load_memories`: Read from Mem0 (skip safely if disabled/unavailable).
  - `query_documents`: Retrieve RAG context from Chroma (fail‑soft to empty list on errors).
  - `rerank_and_fuse` (optional): Only if enabled and multiple docs; fall back to truncation on failure.
  - `generate_response`: Prompt LLM with fused context for general answers.
  - `delegate_to_compliance`: Call the compliance graph and map its result to chat state.
  - `update_memories`: Persist the turn to Mem0 (ignore errors).

### Routing Policy (First Principles)

- Never synthesize placeholder IDs. Delegating to compliance without real routing metadata will produce misleading
  results. The chat graph must gate compliance delegation on valid identifiers or explicitly gathered slots.
- MVP gating rule:
  - Delegate to compliance only if all of the following are true:
    - The intent is compliance‑related (simple keyword heuristic is fine for MVP), and
    - At least `sku_id` and `lane_id` are present, and
    - If a `client_id` concept exists in your data model, include it when available.
  - Otherwise:
    - If the question is generic (e.g., "What duty applies to HTS 9403?"), answer with general RAG in the chat path or
      ask a clarifying question to collect missing slots (slot‑filling) before delegating.
    - The chat path should never fabricate `client_id`/`sku_id`/`lane_id`.

Slot‑filling MVP:
- If compliance intent detected but required slots are missing, respond with a short, targeted question:
  - Example: "To run a compliance check, please provide: sku_id and lane_id."
- Keep this logic in the chat graph’s `route` decision: do not call the compliance graph until the required slots are
  present.

### Compliance Workflow (Compliance Graph)

- File: `src/exim_agent/application/compliance_service/compliance_graph.py`
- Responsibilities:
  - Deterministic, auditable pipeline for snapshot generation and domain Q&A.
  - Execute domain tools and assemble a structured `snapshot` with citations.
  - Provide Q&A when a `question` is present and can be answered from the tool outputs and RAG context.
- Required Inputs (MVP): `client_id`, `sku_id`, `lane_id`.
  - If any required field is missing, return a structured error or a small prompt asking for the missing fields.
- Nodes (MVP):
  - `execute_tools`: Sequential, fail‑soft calls to `HTSTool`, `SanctionsTool`, `RefusalsTool`, `RulingsTool`.
  - `retrieve_context`: Query Chroma for a small set of relevant docs based on known attributes (e.g., HTS code).
  - Route: Q&A if `question` present, else snapshot.
  - `generate_snapshot`: Produce normalized tiles with summarized statuses and citations.
  - `answer_question`: Answer with explicit references to tool outputs and retrieved context.

### Tools

- Files: `src/exim_agent/domain/tools` and dependencies.
- Principles:
  - Pure, deterministic interfaces with clear inputs/outputs; no hidden state.
  - Timeouts and error capture return `{success: False, error: ...}` instead of raising.
  - Cache/short‑circuit where possible to keep latency predictable.
  - Mock external calls in tests; provide fixtures under `tests/fixtures/`.

### RAG Layer

- Vector store: Chroma via `src/exim_agent/infrastructure/db/chroma_client.py`.
- Guidance:
  - Keep top‑K small for MVP. Prefer recall over breadth; rely on prompt grounding.
  - Reranking is optional; if enabled, wrap with try/catch and fall back to simple truncation.
  - Use domain tags/metadata (e.g., `source`, `hts_code`) to bias retrieval when available.

### Memory (Mem0)

- File: `src/exim_agent/application/memory_service/mem0_client.py` (referenced via `mem0_client`).
- Always optional in MVP. If disabled or unavailable, the chat graph continues without memory reads/writes.
- Store only the final assistant response and the user message; exclude sensitive details where possible.

### LLM Provider Facade

- File: `src/exim_agent/infrastructure/llm_providers/langchain_provider.py`
- MVP Recommendations:
  - Default to one provider (OpenAI) to reduce complexity; keep provider switches behind config.
  - Standardize on a single response shape at the boundary (e.g., always return an object with `.content`). Wrap or
    normalize provider outputs so application code doesn’t need provider‑specific checks.

## API Contracts (MVP)

- Chat entrypoint (conversational):
  - Input: `{ query, user_id, session_id, client_id?, sku_id?, lane_id? }`
  - Behavior:
    - If compliance intent and required slots present → delegate to compliance graph.
    - If compliance intent but missing slots → ask for the specific missing fields.
    - Else → general chat RAG path.
  - Output: `{ response, citations?, snapshot? }`

- Compliance snapshot (direct, non‑chat):
  - Input: `{ client_id, sku_id, lane_id }`
  - Output: `{ snapshot }`

- Compliance Q&A (direct, non‑chat):
  - Input: `{ client_id, sku_id, lane_id, question }`
  - Output: `{ answer, citations? }`

## What We’re Getting Right

- Graph separation: distinct chat vs compliance graphs makes responsibilities clear.
- Tool‑first compliance: deterministic stages for HTS, sanctions, refusals, rulings are easy to audit and test.
- Optional Mem0: memory improves experience but does not block functionality.
- Provider abstraction: centralizes model initialization and configuration.

## What’s Too Complex for MVP (and How to Simplify)

- Aggressive routing heuristics: Don’t delegate to compliance without required identifiers. Favor explicit slot‑filling.
- Reranking everywhere: Keep it optional, behind a single config flag, and wrap with graceful fallback.
- Multi‑provider surface: Default to one provider (OpenAI) and revisit others post‑MVP.
- Over‑wide state: Keep the state minimal; avoid transient or duplicate fields that aren’t used downstream.

## Error Handling & Resilience

- Tool failures: capture exceptions, return `{success: False, error}` in state, proceed to build partial snapshot.
- Data store issues: if Chroma is unavailable, continue with empty RAG context; the response should acknowledge limited
  context.
- Provider failures: return a clear user message and log details internally; do not crash the graph.

## Testing Strategy (MVP)

- Unit tests for:
  - Chat routing decisions: intent detection, slot gating, and slot‑filling prompts.
  - Compliance graph nodes: each node returns expected shapes and handles failure paths.
  - Snapshot normalization: tile keys and statuses match frontend expectations.
- Avoid network in tests: mock LLM and external tools; allow disabling Mem0 and Chroma.

## Migration Path (Post‑MVP)

- Replace keyword heuristics with a small classifier or structured parser to extract `sku_id`, `lane_id`, etc.
- Expand document RAG with better indexing, per‑client domains, and embeddings tuning.
- Add streaming responses and tool progress events to improve UX.
- Introduce background workers for higher‑latency enrichment tasks that update snapshots asynchronously.

---

This MVP keeps the system predictable: the chat assistant routes only with sufficient context, the compliance workflow
remains deterministic and auditable, and the overall flow degrades gracefully in real production settings.

