"""LangGraph state machine for memory-aware chat."""

from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from loguru import logger
import operator

from acc_llamaindex.config import config
from acc_llamaindex.application.chat_service.session_manager import session_manager
from acc_llamaindex.application.memory_service.intent_classifier import intent_classifier
from acc_llamaindex.application.memory_service.entity_extractor import entity_extractor
from acc_llamaindex.application.memory_service.service import memory_service
from acc_llamaindex.application.memory_service.salience_tracker import salience_tracker
from acc_llamaindex.application.memory_service.conversation_summarizer import conversation_summarizer
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm


def _keep_last(left: Any, right: Any) -> Any:
    """Reducer that keeps the last (rightmost) value."""
    return right if right is not None else left


class MemoryState(TypedDict):
    """State schema for memory-aware chat flow."""
    # Input - keep last value from parallel updates
    user_query: Annotated[str, _keep_last]
    session_id: Annotated[str, _keep_last]
    
    # Working Memory
    wm_context: Annotated[List[Dict[str, Any]], _keep_last]  # Last N conversation turns
    
    # Intent & Entity Detection
    intent: Annotated[str, _keep_last]
    confidence: Annotated[float, _keep_last]
    entities: Annotated[List[Dict[str, Any]], _keep_last]
    
    # Memory Retrieval - allow parallel updates to accumulate
    em_results: Annotated[List[Dict[str, Any]], _keep_last]  # Episodic memory results
    sm_results: Annotated[List[Dict[str, Any]], _keep_last]  # Semantic memory results
    reranked_context: Annotated[List[Dict[str, Any]], _keep_last]  # Combined + reranked
    
    # Generation
    response: Annotated[str, _keep_last]
    citations: Annotated[List[Dict[str, Any]], _keep_last] # citations from memory
    
    # Metadata
    should_distill: Annotated[bool, _keep_last]
    retrieval_ms: Annotated[float, _keep_last]
    generation_ms: Annotated[float, _keep_last]


def load_working_memory(state: MemoryState) -> MemoryState:
    """
    Load last N conversation turns from session.
    
    Fast, in-memory retrieval of recent context.
    """
    logger.info(f"Loading working memory for session: {state['session_id']}")
    
    # Load recent turns from session manager
    turns = session_manager.get_recent_turns(
        state["session_id"],
        n=config.wm_max_turns
    )
    
    state["wm_context"] = turns
    logger.debug(f"Loaded {len(turns)} turns from working memory")
    
    return state


def classify_intent(state: MemoryState) -> MemoryState:
    """
    Detect user intent and extract entities.
    
    Uses LLM-based classification for:
    - quote_request
    - compliance_query
    - shipment_tracking
    - general
    """
    logger.info(f"Classifying intent for query: {state['user_query'][:50]}...")
    
    # Classify intent
    if config.enable_intent_classification:
        classification = intent_classifier.classify(state["user_query"])
        state["intent"] = classification["intent"]
        state["confidence"] = classification["confidence"]
    else:
        state["intent"] = "general"
        state["confidence"] = 1.0
    
    # Extract entities
    entities = entity_extractor.extract(state["user_query"])
    state["entities"] = entities
    
    logger.info(
        f"Intent: {state['intent']} (confidence: {state['confidence']:.2f}), "
        f"Entities: {len(entities)}"
    )
    
    return state


def query_episodic_memory(state: MemoryState) -> Dict[str, Any]:
    """
    Query EM collection filtered by session + salience.
    
    Retrieves recent conversation facts from this session.
    
    Returns:
        Dict with only 'em_results' key to avoid parallel update conflicts
    """
    if not config.enable_memory_system:
        return {"em_results": []}
    
    logger.info(f"Querying episodic memory for session: {state['session_id']}")
    
    # Query via memory service (handles EM retrieval)
    recall_result = memory_service.recall(
        query=state["user_query"],
        session_id=state["session_id"],
        intent=state["intent"],
        entities=state["entities"],
        k_em=config.em_k_default,
        k_sm=0  # Only EM in this node
    )
    
    em_results = recall_result["em_results"]
    logger.info(f"Retrieved {len(em_results)} EM results")
    
    return {"em_results": em_results}


def query_semantic_memory(state: MemoryState) -> Dict[str, Any]:
    """
    Query SM collection filtered by entities + intent.
    
    Retrieves long-term knowledge from documents.
    
    Returns:
        Dict with only 'sm_results' key to avoid parallel update conflicts
    """
    logger.info(f"Querying semantic memory with intent: {state['intent']}")
    
    # Query via memory service (handles SM retrieval)
    recall_result = memory_service.recall(
        query=state["user_query"],
        session_id=state["session_id"],
        intent=state["intent"],
        entities=state["entities"],
        k_em=0,  # Only SM in this node
        k_sm=config.sm_k_default
    )
    
    sm_results = recall_result["sm_results"]
    logger.info(f"Retrieved {len(sm_results)} SM results")
    
    return {"sm_results": sm_results}


def rerank_results(state: MemoryState) -> MemoryState:
    """
    Combine and rerank EM + SM results.
    
    Uses existing reranking service via memory service.
    """
    em_count = len(state["em_results"])
    sm_count = len(state["sm_results"])
    logger.info(f"Reranking {em_count} EM + {sm_count} SM results")
    
    # Use memory service to merge and rerank
    recall_result = memory_service.recall(
        query=state["user_query"],
        session_id=state["session_id"],
        intent=state["intent"],
        entities=state["entities"],
        k_em=config.em_k_default,
        k_sm=config.sm_k_default
    )
    
    state["reranked_context"] = recall_result["combined_results"]
    logger.info(f"Reranked to {len(state['reranked_context'])} results")
    
    return state


def generate_response(state: MemoryState) -> MemoryState:
    """
    Generate answer with citations.
    
    Uses LLM with structured context from memory tiers.
    """
    logger.info("Generating response with memory context")
    
    # Format context from memory
    context_parts = []
    for i, result in enumerate(state["reranked_context"]):
        source = result["source"]
        text = result["text"]
        context_parts.append(f"[{source}-{i+1}] {text}")
    
    context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
    
    # Format working memory (recent conversation)
    wm_text = ""
    if state["wm_context"]:
        wm_parts = []
        for turn in state["wm_context"][-3:]:  # Last 3 turns
            wm_parts.append(f"User: {turn['user_message']}")
            wm_parts.append(f"Assistant: {turn['assistant_message']}")
        wm_text = "\n".join(wm_parts)
    
    # Build prompt (from retrieved context and retrieved memory)
    prompt = f"""Answer the user's question using the provided context.

Recent Conversation:
{wm_text if wm_text else "(No previous conversation)"}

Relevant Context:
{context_text}

User Question: {state['user_query']}

Provide a helpful answer based on the context. If you cite information, reference the source [EM-1], [SM-2], etc."""
    
    # Generate with LLM
    llm = get_llm()
    response = llm.invoke(prompt)
    
    # Extract text from response
    if hasattr(response, 'content'):
        state["response"] = response.content
    else:
        state["response"] = str(response)
    
    # Parse citations (simple regex)
    import re
    citations = []
    citation_pattern = r"\[(EM|SM)-(\d+)\]"
    for match in re.finditer(citation_pattern, state["response"]):
        source_type = match.group(1)
        index = int(match.group(2)) - 1
        if index < len(state["reranked_context"]):
            citations.append(state["reranked_context"][index])
    
    state["citations"] = citations
    
    # Track salience for cited items
    if citations:
        salience_tracker.track_citations(citations)
    
    logger.info(f"Generated response with {len(citations)} citations")
    
    return state


def update_working_memory(state: MemoryState) -> MemoryState:
    """
    Update WM and check if distillation needed.
    
    Updates session state and schedules distillation if threshold reached.
    """
    logger.info(f"Updating working memory for session: {state['session_id']}")
    
    # Add this turn to session
    session_manager.add_turn(
        session_id=state["session_id"],
        user_message=state["user_query"],
        assistant_message=state["response"],
        metadata={
            "intent": state["intent"],
            "entities": state["entities"],
            "citations": state["citations"]
        }
    )
    
    # Check if we should trigger distillation
    session = session_manager.get_session(state["session_id"])
    turn_count = session["turn_count"] if session else 0
    
    state["should_distill"] = (
        config.enable_em_distillation and 
        turn_count > 0 and
        turn_count % config.em_distill_every_n_turns == 0
    )
    
    if state["should_distill"]:
        logger.info(f"Distillation triggered after {turn_count} turns")
        
        # Get recent turns for distillation
        recent_turns = session_manager.get_recent_turns(
            state["session_id"],
            n=config.em_distill_every_n_turns
        )
        
        # Distill conversation into facts
        if recent_turns:
            distill_result = conversation_summarizer.distill(
                session_id=state["session_id"],
                turns=recent_turns
            )
            
            logger.info(
                f"Distillation complete: {distill_result.get('facts_created', 0)} facts created"
            )
    
    return state


def create_memory_graph() -> StateGraph:
    """
    Build the LangGraph state machine for memory-aware chat.
    
    Returns:
        Compiled graph ready for execution
    """
    graph = StateGraph(MemoryState)
    
    # Add nodes
    graph.add_node("load_wm", load_working_memory)
    graph.add_node("classify", classify_intent)
    graph.add_node("query_em", query_episodic_memory)
    graph.add_node("query_sm", query_semantic_memory)
    graph.add_node("rerank", rerank_results)
    graph.add_node("generate", generate_response)
    graph.add_node("update_wm", update_working_memory)
    
    # Define edges (flow)
    graph.set_entry_point("load_wm")
    graph.add_edge("load_wm", "classify")
    
    # Parallel execution for EM and SM queries
    graph.add_edge("classify", "query_em")
    graph.add_edge("classify", "query_sm")
    
    # Both queries must complete before reranking
    graph.add_edge("query_em", "rerank")
    graph.add_edge("query_sm", "rerank")
    
    # Sequential flow for generation and WM update
    graph.add_edge("rerank", "generate")
    graph.add_edge("generate", "update_wm")
    
    # Finish after WM update
    graph.add_edge("update_wm", END)
    
    logger.info("Memory graph created successfully")
    return graph.compile()


# Global graph instance (lazy initialization)
_memory_graph = None


def get_memory_graph() -> StateGraph:
    """Get or create the compiled memory graph."""
    global _memory_graph
    if _memory_graph is None:
        _memory_graph = create_memory_graph()
    return _memory_graph
