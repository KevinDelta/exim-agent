# LangGraph Orchestration Overview

This note captures how the current LangGraph flows stitch tools together inside the chat and compliance services. Use it as a reference when adjusting routing or adding new capabilities.

## Chat Graph (`src/exim_agent/application/chat_service/graph.py`)

| Stage | Node | Purpose |
| --- | --- | --- |
| Entry | `route` + `route_decision` | Inspect lowercase query + optional `sku_id`/`lane_id` to pick `general_rag`, `delegate_compliance`, or `slot_filling`. Compliance intent without required slots sets `_missing_slots` before routing. |
| Slot filling branch | `slot_filling` | Asks for the precise identifiers still missing, sets `routing_path="slot_filling"`, and jumps straight to the shared memory update node. Prevents tool execution when inputs are incomplete. |
| General RAG branch | `load_memories` → `query_documents` → `rerank_and_fuse` → `generate_response` | Sequential tools that (1) retrieve conversational context from Mem0, (2) pull Chroma docs, (3) fuse/rerank with the cross-encoder, and (4) call the LLM with a context window. Each node fail-softs so downstream steps still run with empty context. |
| Compliance branch | `delegate_to_compliance` | Packages chat state into `ComplianceState`, chooses snapshot vs. Q&A mode based on keywords, invokes the compiled compliance graph, and normalizes any returned `answer`, `snapshot`, and citations back onto the chat state before continuing. |
| Exit | `update_memories` → `END` | Stores the turn in Mem0 (if enabled) regardless of branch, so every conversation is retrievable, then terminates the workflow. |

### Key Ideas

- **Typed state (`ChatState`)**: Every node reads/writes explicit keys (query, routing flags, contexts, outputs). Adding new behavior means expanding the typing plus inserting another node/edge.
- **Edges define loops**: All three branches converge on `update_memories`, so “looping” is just routing back to the shared node until the guard condition (`END`) is hit.
- **Tool isolation**: Each capability (Mem0 search, Chroma retrieval, reranking) is wrapped in one node with logging + error handling, which keeps orchestration declarative and easy to trace.

## Compliance Graph (`src/exim_agent/application/compliance_service/compliance_graph.py`)

| Stage | Node | Purpose |
| --- | --- | --- |
| Entry | `validate_inputs` | Ensures `client_id`, `sku_id`, and `lane_id` exist. Missing fields trigger an error snapshot/answer and route straight to `END`. |
| Tool execution | `execute_tools` | Sequentially runs `HTSTool`, `SanctionsTool`, `RefusalsTool`, and `RulingsTool`, capturing each in a `{success, data, error}` envelope so later nodes can degrade gracefully. |
| Context retrieval | `retrieve_context` | Lazily initializes the compliance collections client and pulls lightweight HTS notes from Chroma to augment answers/snapshots. |
| Mode routing | Conditional edge | If `question` exists, the graph heads to `answer_question`; otherwise it goes to `generate_snapshot`. |
| Snapshot mode | `generate_snapshot` | Builds tiles for every tool (successful or not), normalizes statuses for the frontend, counts alerts, and surfaces citations only from successful sources. |
| Q&A mode | `answer_question` | Assembles a prompt from successful tool outputs + retrieved docs, explicitly notes which sources failed, and invokes the shared LLM with fail-soft handling. |

### Key Ideas

- **Explicit mode split**: Snapshot vs. Q&A is determined purely by whether `question` was passed from the chat graph, so additional modes can slot in as new conditional targets.
- **Fail-soft everywhere**: Each node guards external integrations, meaning partial data still becomes tiles or answer text with clear caveats instead of aborting the flow.
- **Reusable subgraph**: Because the compliance logic is compiled separately, any service (today: `delegate_to_compliance`) can invoke it as a black box without duplicating tool orchestration.

## Taking Action

- To add another chat capability, define a new node, register it in `build_memory_graph`, and extend `ChatState`/routing as needed.
- To plug a new compliance signal, add fields to `ComplianceState`, drop the tool into `execute_tools`, and update snapshot/Q&A nodes to consume the new result.

