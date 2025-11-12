"""Simplified LangGraph state machine with Mem0 integration and compliance routing."""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from loguru import logger

from exim_agent.config import config
from exim_agent.application.memory_service.mem0_client import mem0_client
from exim_agent.infrastructure.db.chroma_client import chroma_client
from exim_agent.application.reranking_service.service import reranking_service
from exim_agent.infrastructure.llm_providers.langchain_provider import get_llm
from exim_agent.application.compliance_service.compliance_graph import compliance_graph


class MemoryState(TypedDict):
    """Simplified state schema for Mem0-powered chat."""
    # Input
    query: str
    user_id: str
    session_id: str
    # Optional domain routing hints
    client_id: str | None
    sku_id: str | None
    lane_id: str | None
    
    # Mem0 memories (replaces WM + EM + intent/entity extraction)
    relevant_memories: List[Dict[str, Any]]
    
    # RAG context (document retrieval)
    rag_context: List[Dict[str, Any]]
    
    # Combined & reranked context
    final_context: List[Dict[str, Any]]
    
    # Response
    response: str
    citations: List[str]
    # Optional: latest compliance snapshot
    snapshot: Dict[str, Any] | None


def _looks_like_compliance_question(text: str) -> bool:
    """Heuristic to detect compliance-related questions."""
    if not text:
        return False
    keywords = [
        "hts", "sanctions", "refusal", "ruling", "classification",
        "duty", "tariff", "cbp", "export", "compliance",
    ]
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def route_node(state: MemoryState) -> MemoryState:
    """No-op; routing handled via conditional edges."""
    return state


def delegate_to_compliance(state: MemoryState) -> MemoryState:
    """Delegate handling to the compliance graph and adapt response to chat state."""
    logger.info("Routing to compliance graph")

    client_id = state.get("client_id")
    sku_id = state.get("sku_id")
    lane_id = state.get("lane_id")
    question = state.get("query") or ""

    # Decide between snapshot vs Q&A: if explicit snapshot intent keywords, skip question
    snapshot_intents = ["snapshot", "run compliance", "generate snapshot"]
    if any(tok in question.lower() for tok in snapshot_intents):
        comp_question: str | None = None
    else:
        comp_question = question

    comp_input: Dict[str, Any] = {
        "client_id": client_id or "default-client",
        "sku_id": sku_id or "default-sku",
        "lane_id": lane_id or "default-lane",
    }
    if comp_question:
        comp_input["question"] = comp_question

    try:
        comp_result = compliance_graph.invoke(comp_input)

        # Prefer Q&A answer if present, else surface a brief snapshot summary
        answer = comp_result.get("answer")
        snapshot = comp_result.get("snapshot")
        state["snapshot"] = snapshot

        if answer:
            state["response"] = answer
        elif snapshot:
            tiles = snapshot.get("tiles", {}) if isinstance(snapshot, dict) else {}
            statuses = {k: (v.get("status") if isinstance(v, dict) else None) for k, v in tiles.items()}
            summary = f"Compliance snapshot generated. Tile statuses: {statuses}"
            state["response"] = summary
        else:
            state["response"] = "Compliance workflow completed."

        # Extract simple citations list if present
        citations: List[str] = []
        raw_citations = comp_result.get("citations") or []
        for c in raw_citations:
            if isinstance(c, dict):
                src = c.get("source")
                if src and src not in citations:
                    citations.append(src)
            else:
                s = str(c)
                if s and s not in citations:
                    citations.append(s)
        state["citations"] = citations[:5]

    except Exception as e:
        logger.error(f"Compliance delegation failed: {e}")
        state["response"] = "I encountered an error running the compliance workflow."
        state["citations"] = []

    return state


def load_memories(state: MemoryState) -> MemoryState:
    """
    Load relevant memories from Mem0.
    """
    logger.info(f"Loading Mem0 memories for session: {state['session_id']}")
    
    query = state["query"]
    user_id = state["user_id"]
    session_id = state["session_id"]
    
    if not mem0_client.is_enabled():
        logger.warning("Mem0 not enabled, skipping memory load")
        state["relevant_memories"] = []
        return state
    
    # Mem0 automatically:
    # - Retrieves recent conversation context
    # - Classifies intent and extracts entities
    # - Searches episodic memories
    # - Ranks by relevance
    results = mem0_client.search(
        query=query,
        user_id=user_id,
        session_id=session_id,
        limit=config.mem0_history_limit
    )
    
    # Handle dict or list response from Mem0
    if isinstance(results, dict):
        memories = results.get('results', [])
    else:
        memories = results if isinstance(results, list) else []
    
    state["relevant_memories"] = memories
    logger.info(f"Loaded {len(memories)} relevant memories from Mem0")
    
    return state


def query_documents(state: MemoryState) -> MemoryState:
    """
    Query document store for RAG context (semantic memory).
    
    This is separate from Mem0 - it's your knowledge base documents.
    Mem0 handles conversational memory, this handles document RAG.
    """
    logger.info("Querying document store for RAG context")
    
    query = state["query"]
    
    try:
        # Query ChromaDB documents collection using LangChain vector store
        vector_store = chroma_client.get_vector_store()
        documents = vector_store.similarity_search(
            query,
            k=config.retrieval_k
        )
        
        # Normalize to simple dict format for downstream processing
        state["rag_context"] = [
            {
                "content": doc.page_content,
                "metadata": dict(doc.metadata or {})
            }
            for doc in documents
        ]
        logger.info(f"Retrieved {len(documents)} RAG documents")
        
    except Exception as e:
        logger.error(f"Failed to query documents: {e}")
        state["rag_context"] = []
    
    return state


def rerank_and_fuse(state: MemoryState) -> MemoryState:
    """
    Combine memories + RAG results and rerank with cross-encoder.
    
    Fuses:
    - Mem0 memories (conversational context)
    - RAG documents (knowledge base)
    
    Then reranks for relevance.
    """
    logger.info("Reranking and fusing memory + RAG context")
    
    query = state["query"]
    memories = state["relevant_memories"]
    rag_docs = state["rag_context"]
    
    # Convert memories to document format
    memory_docs = []
    for mem in memories:
        if isinstance(mem, dict):
            content = mem.get("memory", str(mem))
            mem_id = mem.get("id", "unknown")
        else:
            content = str(mem)
            mem_id = "unknown"
        
        memory_docs.append({
            "content": content,
            "metadata": {
                "source": "mem0",
                "memory_id": mem_id,
                "type": "conversational_memory"
            }
        })
    
    # Combine both sources
    all_docs = memory_docs + rag_docs
    
    if not all_docs:
        logger.warning("No context available for generation")
        state["final_context"] = []
        return state
    
    # Rerank if enabled
    if config.enable_reranking and len(all_docs) > 1:
        try:
            # Convert dict documents to LangChain Documents for reranking
            from langchain_core.documents import Document
            lc_docs = [
                Document(page_content=doc["content"], metadata=doc.get("metadata", {}))
                for doc in all_docs
            ]
            
            # Initialize reranker if not already done
            if not reranking_service.is_enabled():
                reranking_service.initialize()
            
            # Rerank
            reranked_docs = reranking_service.rerank(
                query=query,
                documents=lc_docs,
                top_k=config.rerank_top_k
            )
            
            # Convert back to dict format
            state["final_context"] = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in reranked_docs
            ]
            logger.info(f"Reranked to {len(reranked_docs)} documents")
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            state["final_context"] = all_docs[:config.rerank_top_k]
    else:
        state["final_context"] = all_docs[:config.rerank_top_k]
    
    return state


def generate_response(state: MemoryState) -> MemoryState:
    """
    Generate response with LLM using final context.
    """
    logger.info("Generating response")
    
    query = state["query"]
    context = state["final_context"]
    
    llm = get_llm()
    
    # Build context string
    context_str = "\n\n".join([
        f"[{i+1}] {doc['content'][:500]}"  # Truncate long docs
        for i, doc in enumerate(context)
    ])
    
    # Create prompt
    prompt = f"""Answer the question using the following context. If the context doesn't contain relevant information, say so.

Context:
{context_str}

Question: {query}

Answer:"""
    
    try:
        result = llm.invoke(prompt)
        state["response"] = result.content
        
        # Extract citations
        citations = []
        for doc in context:
            source = doc.get("metadata", {}).get("source", "unknown")
            if source not in citations:
                citations.append(source)
        
        state["citations"] = citations[:5]  # Limit to top 5 sources
        
        logger.info("Response generated successfully")
        
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        state["response"] = "I apologize, but I encountered an error generating a response."
        state["citations"] = []
    
    return state


def update_memories(state: MemoryState) -> MemoryState:
    """
    Store conversation turn in Mem0.
    
    Replaces:
    - update_working_memory (session management)
    - distillation (conversation summarization)
    - deduplication (duplicate detection)
    - promotion (EM → SM promotion)
    
    Mem0 handles all of this automatically.
    """
    logger.info("Updating Mem0 with conversation turn")
    
    query = state["query"]
    response = state["response"]
    user_id = state["user_id"]
    session_id = state["session_id"]
    
    if not mem0_client.is_enabled():
        logger.warning("Mem0 not enabled, skipping memory update")
        return state
    
    # Mem0 automatically:
    # - Deduplicates similar memories
    # - Summarizes conversations
    # - Manages temporal decay
    # - Promotes important facts to long-term memory
    messages = [
        {"role": "user", "content": query},
        {"role": "assistant", "content": response}
    ]
    
    try:
        mem0_client.add(
            messages=messages,
            user_id=user_id,
            session_id=session_id
        )
        logger.info("Conversation stored in Mem0")
        
    except Exception as e:
        logger.error(f"Failed to update Mem0: {e}")
    
    return state


def build_memory_graph() -> StateGraph:
    """
    Build the simplified LangGraph state machine with Mem0 and domain routing.
    """
    logger.info("Building Mem0-powered LangGraph")
    
    workflow = StateGraph(MemoryState)
    
    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("delegate_to_compliance", delegate_to_compliance)
    workflow.add_node("load_memories", load_memories)
    workflow.add_node("query_documents", query_documents)
    workflow.add_node("rerank_and_fuse", rerank_and_fuse)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("update_memories", update_memories)
    
    # Define edges with conditional routing
    def route_after_entry(state: MemoryState) -> str:
        # Route to compliance if IDs exist, a prior snapshot exists, or query looks compliance-related
        has_ids = bool(state.get("client_id") or state.get("sku_id") or state.get("lane_id"))
        has_snapshot = bool(state.get("snapshot"))
        is_compliancey = _looks_like_compliance_question(state.get("query", ""))
        return "delegate_to_compliance" if (has_ids or has_snapshot or is_compliancey) else "general"

    workflow.set_entry_point("route")
    workflow.add_conditional_edges(
        "route",
        route_after_entry,
        {
            "delegate_to_compliance": "delegate_to_compliance",
            "general": "load_memories",
        },
    )

    # General chat path
    workflow.add_edge("load_memories", "query_documents")
    workflow.add_edge("query_documents", "rerank_and_fuse")
    workflow.add_edge("rerank_and_fuse", "generate_response")

    # Shared terminal update
    workflow.add_edge("generate_response", "update_memories")
    workflow.add_edge("delegate_to_compliance", "update_memories")
    workflow.add_edge("update_memories", END)
    
    logger.info("Mem0-powered LangGraph compiled successfully")
    
    return workflow.compile()


# Global graph instance
memory_graph = build_memory_graph()
