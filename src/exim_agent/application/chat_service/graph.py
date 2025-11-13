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


class ChatState(TypedDict):
    """Minimal state schema for chat graph with clear field purposes."""
    # Required inputs
    query: str
    user_id: str
    session_id: str
    
    # Optional routing metadata (for compliance delegation)
    client_id: str | None
    sku_id: str | None
    lane_id: str | None
    
    # Processing context
    relevant_memories: List[Dict[str, Any]]  # Mem0 conversational memories
    rag_context: List[Dict[str, Any]]  # ChromaDB document retrieval
    final_context: List[Dict[str, Any]]  # Combined & reranked context
    
    # Outputs
    response: str
    citations: List[str]
    snapshot: Dict[str, Any] | None  # Optional compliance snapshot
    routing_path: str | None  # Which path was taken: general_rag, slot_filling, or delegate_compliance
    
    # Internal routing flags (not exposed to API)
    _needs_slot_filling: bool
    _missing_slots: List[str]


def route_decision(state: ChatState) -> str:
    """
    routing with explicit slot validation.
    
    Returns:
        - "slot_filling": Compliance intent but missing required slots
        - "delegate_compliance": Compliance intent with all required slots
        - "general_rag": General question or ambiguous intent
    """
    query = state["query"].lower()
    
    # Simple keyword-based compliance detection
    compliance_keywords = [
        "hts", "sanctions", "refusal", "ruling", "classification",
        "duty", "tariff", "cbp", "compliance", "snapshot"
    ]
    
    is_compliance = any(kw in query for kw in compliance_keywords)
    
    if not is_compliance:
        return "general_rag"
    
    # Check for required slots
    has_sku = bool(state.get("sku_id"))
    has_lane = bool(state.get("lane_id"))
    
    if has_sku and has_lane:
        return "delegate_compliance"
    
    # Compliance intent but missing slots
    missing = []
    if not has_sku:
        missing.append("sku_id")
    if not has_lane:
        missing.append("lane_id")
    
    state["_needs_slot_filling"] = True
    state["_missing_slots"] = missing
    return "slot_filling"


def route_node(state: ChatState) -> ChatState:
    """No-op; routing handled via conditional edges."""
    return state


def slot_filling_node(state: ChatState) -> ChatState:
    """
    Ask user for missing required slots.
    Never fabricate or assume values.
    Routes directly to memory update and end (doesn't proceed to compliance).
    """
    missing = state.get("_missing_slots", [])
    
    if not missing:
        state["response"] = "I need more information to proceed with the compliance check."
        state["citations"] = []
        state["snapshot"] = None
        state["routing_path"] = "slot_filling"
        return state
    
    # Generate targeted prompt for missing slots
    slots_str = " and ".join(missing)
    state["response"] = (
        f"To run a compliance check, I need the following information: {slots_str}. "
        f"Please provide these identifiers."
    )
    state["citations"] = []
    state["snapshot"] = None
    state["routing_path"] = "slot_filling"
    
    logger.info(f"Slot filling requested for: {missing}")
    
    return state


def delegate_to_compliance(state: ChatState) -> ChatState:
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
        state["routing_path"] = "delegate_compliance"

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
        state["routing_path"] = "delegate_compliance"

    return state


def load_memories_safe(state: ChatState) -> ChatState:
    """
    Load relevant memories from Mem0 with complete fail-soft behavior.
    Memory failures never block response generation.
    """
    logger.info(f"Loading Mem0 memories for session: {state['session_id']}")
    
    if not mem0_client.is_enabled():
        logger.debug("Mem0 disabled, skipping memory load")
        state["relevant_memories"] = []
        return state
    
    try:
        query = state["query"]
        user_id = state["user_id"]
        session_id = state["session_id"]
        
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
        elif isinstance(results, list):
            memories = results
        else:
            memories = []
        
        state["relevant_memories"] = memories
        logger.info(f"Loaded {len(memories)} relevant memories from Mem0")
        
    except Exception as e:
        logger.warning(f"Memory load failed (continuing with empty context): {e}")
        state["relevant_memories"] = []
    
    return state


def query_documents_safe(state: ChatState) -> ChatState:
    """
    Query document store for RAG context with complete fail-soft behavior.
    RAG failures never block response generation.
    
    This is separate from Mem0 - it's your knowledge base documents.
    Mem0 handles conversational memory, this handles document RAG.
    """
    logger.info("Querying document store for RAG context")
    
    try:
        query = state["query"]
        
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
        logger.warning(f"Document retrieval failed (continuing with empty context): {e}")
        state["rag_context"] = []
    
    return state


def rerank_and_fuse_safe(state: ChatState) -> ChatState:
    """
    Combine memories + RAG results and rerank with cross-encoder.
    Falls back to truncation if reranking fails.
    
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
    
    # Try reranking if enabled
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
            logger.warning(f"Reranking failed, using truncation fallback: {e}")
            state["final_context"] = all_docs[:config.rerank_top_k]
    else:
        # Simple truncation fallback
        state["final_context"] = all_docs[:config.rerank_top_k]
    
    return state


def generate_response(state: ChatState) -> ChatState:
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
        state["routing_path"] = "general_rag"
        
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
        state["routing_path"] = "general_rag"
    
    return state


def update_memories_safe(state: ChatState) -> ChatState:
    """
    Store conversation turn in Mem0 with complete fail-soft behavior.
    Memory failures never block response generation.
    
    Replaces:
    - update_working_memory (session management)
    - distillation (conversation summarization)
    - deduplication (duplicate detection)
    - promotion (EM → SM promotion)
    
    Mem0 handles all of this automatically.
    """
    logger.info("Updating Mem0 with conversation turn")
    
    if not mem0_client.is_enabled():
        logger.debug("Mem0 disabled, skipping memory update")
        return state
    
    try:
        query = state["query"]
        response = state["response"]
        user_id = state["user_id"]
        session_id = state["session_id"]
        
        # Mem0 automatically:
        # - Deduplicates similar memories
        # - Summarizes conversations
        # - Manages temporal decay
        # - Promotes important facts to long-term memory
        messages = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response}
        ]
        
        mem0_client.add(
            messages=messages,
            user_id=user_id,
            session_id=session_id
        )
        logger.debug("Conversation stored in Mem0 successfully")
        
    except Exception as e:
        logger.warning(f"Memory update failed (continuing): {e}")
    
    return state


def build_memory_graph() -> StateGraph:
    """
    Build the simplified LangGraph state machine with conservative routing.
    """
    logger.info("Building chat graph with conservative routing")
    
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("slot_filling", slot_filling_node)
    workflow.add_node("delegate_to_compliance", delegate_to_compliance)
    workflow.add_node("load_memories", load_memories_safe)
    workflow.add_node("query_documents", query_documents_safe)
    workflow.add_node("rerank_and_fuse", rerank_and_fuse_safe)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("update_memories", update_memories_safe)
    
    # Define edges with conservative routing logic
    def route_after_entry(state: ChatState) -> str:
        """Use new route_decision function for conservative routing."""
        return route_decision(state)

    workflow.set_entry_point("route")
    workflow.add_conditional_edges(
        "route",
        route_after_entry,
        {
            "slot_filling": "slot_filling",
            "delegate_compliance": "delegate_to_compliance",
            "general_rag": "load_memories",
        },
    )

    # Slot filling path goes directly to memory update
    workflow.add_edge("slot_filling", "update_memories")

    # General RAG path
    workflow.add_edge("load_memories", "query_documents")
    workflow.add_edge("query_documents", "rerank_and_fuse")
    workflow.add_edge("rerank_and_fuse", "generate_response")
    workflow.add_edge("generate_response", "update_memories")

    # Compliance delegation path
    workflow.add_edge("delegate_to_compliance", "update_memories")
    
    # All paths converge at update_memories and end
    workflow.add_edge("update_memories", END)
    
    logger.info("Chat graph with conservative routing compiled successfully")
    
    return workflow.compile()


# Global graph instance
memory_graph = build_memory_graph()
