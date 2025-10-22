"""ZenML pipeline for memory distillation."""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from zenml import pipeline, step

ZENML_AVAILABLE = True

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.application.memory_service.conversation_summarizer import conversation_summarizer


@step
def fetch_recent_turns(
    session_id: str,
    n_turns: int = 5
) -> List[Dict[str, Any]]:
    """
    Step 1: Fetch conversation history.
    
    Args:
        session_id: Session identifier
        n_turns: Number of recent turns to fetch
        
    Returns:
        List of conversation turns
    """
    logger.info(f"Fetching {n_turns} recent turns for session {session_id}")
    
    try:
        # Query working memory for recent turns
        # This would typically query from your session store
        # For now, this is a placeholder - you'd implement session retrieval
        #
        # TODO: Implement session retrieval
        
        from acc_llamaindex.application.chat_service.session_manager import session_manager
        
        session = session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return []
        
        # Get last N conversation turns
        turns = session.conversation_history[-n_turns:] if hasattr(session, 'conversation_history') else []
        
        logger.info(f"Fetched {len(turns)} turns")
        return turns
        
    except Exception as e:
        logger.error(f"Failed to fetch turns: {e}")
        return []


@step(enable_cache=False)  # Always fresh LLM calls
def summarize_conversation(
    turns: List[Dict[str, Any]],
    llm_model: str = "gpt-5-mini"
) -> str:
    """
    Step 2: LLM-based summarization.
    
    Track which LLM was used and log to experiment tracker.
    
    Args:
        turns: Conversation turns
        llm_model: LLM model identifier
        
    Returns:
        Conversation summary
    """
    if not turns:
        logger.warning("No turns to summarize")
        return ""
    
    logger.info(f"Summarizing {len(turns)} turns using {llm_model}")
    
    # Format conversation
    conversation_text = conversation_summarizer._format_conversation(turns)
    
    # Generate summary (this would use the LLM)
    summary = f"Summary of {len(turns)} turns: {conversation_text[:200]}..."
    
    logger.info("Generated conversation summary")
    return summary


@step
def extract_facts(
    summary: str,
    turns: List[Dict[str, Any]],
    llm_model: str = "gpt-5-mini"
) -> List[Dict[str, Any]]:
    """
    Step 3: Extract discrete facts from summary.
    
    Args:
        summary: Conversation summary
        turns: Original conversation turns
        llm_model: LLM model identifier
        
    Returns:
        List of extracted facts
    """
    if not turns:
        return []
    
    logger.info(f"Extracting facts using {llm_model}")
    
    try:
        # Use existing conversation summarizer's distillation chain
        result = conversation_summarizer.chain.invoke({
            "conversation": conversation_summarizer._format_conversation(turns)
        })
        
        facts = result.get("facts", []) if isinstance(result, dict) else []
        logger.info(f"Extracted {len(facts)} facts")
        
        return facts
        
    except Exception as e:
        logger.error(f"Failed to extract facts: {e}")
        return []


@step
def deduplicate_facts(
    new_facts: List[Dict[str, Any]],
    session_id: str
) -> List[Dict[str, Any]]:
    """
    Step 4: Remove duplicate facts.
    
    Query existing EM facts to avoid duplication.
    
    Args:
        new_facts: Newly extracted facts
        session_id: Session identifier
        
    Returns:
        Deduplicated facts
    """
    if not new_facts:
        return []
    
    logger.info(f"Deduplicating {len(new_facts)} facts for session {session_id}")
    
    # For now, return all facts
    # In production, you'd query ChromaDB for similar facts
    # and filter out duplicates based on semantic similarity
    
    try:
        # Placeholder for deduplication logic
        # You could use the deduplication service here
        from acc_llamaindex.application.memory_service.deduplication import deduplication_service
        
        # Simple approach: keep all for now
        unique_facts = new_facts
        
        logger.info(f"Kept {len(unique_facts)} unique facts")
        return unique_facts
        
    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        return new_facts


@step
def store_episodic_facts(
    facts: List[Dict[str, Any]],
    session_id: str,
    source_turns: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Step 5: Store facts in episodic memory collection.
    
    Args:
        facts: Facts to store
        session_id: Session identifier
        source_turns: Source conversation turns
        
    Returns:
        Storage statistics
    """
    if not facts:
        logger.warning("No facts to store")
        return {"facts_stored": 0, "status": "no_facts"}
    
    logger.info(f"Storing {len(facts)} facts in episodic memory")
    
    try:
        # Use existing conversation summarizer's write method
        written_count = conversation_summarizer._write_to_episodic(
            session_id=session_id,
            facts=facts,
            source_turns=source_turns
        )
        
        return {
            "facts_stored": written_count,
            "session_id": session_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to store facts: {e}")
        return {
            "facts_stored": 0,
            "error": str(e),
            "status": "error"
        }


@pipeline
def distillation_pipeline(
    session_id: str,
    n_turns: int = 5,
    llm_model: str = "gpt-4"
) -> Dict[str, Any]:
    """
    Distill conversation into episodic memory.
    
    Benefits:
    - Track which LLM generated which facts
    - Compare different summarization prompts
    - Measure fact extraction quality
    - Lineage: turns → summary → facts → storage
    
    Args:
        session_id: Session identifier
        n_turns: Number of recent turns to distill
        llm_model: LLM model to use
        
    Returns:
        Distillation statistics
    """
    # Step 1: Fetch recent turns
    turns = fetch_recent_turns(
        session_id=session_id,
        n_turns=n_turns
    )
    
    # Step 2: Summarize conversation
    summary = summarize_conversation(
        turns=turns,
        llm_model=llm_model
    )
    
    # Step 3: Extract facts
    facts = extract_facts(
        summary=summary,
        turns=turns,
        llm_model=llm_model
    )
    
    # Step 4: Deduplicate
    unique_facts = deduplicate_facts(
        new_facts=facts,
        session_id=session_id
    )
    
    # Step 5: Store in episodic memory
    result = store_episodic_facts(
        facts=unique_facts,
        session_id=session_id,
        source_turns=turns
    )
    
    return result


def run_distillation_pipeline(
    session_id: str,
    n_turns: int = 5,
    **kwargs
) -> Dict[str, Any]:
    """
    Run the distillation pipeline.
    
    Args:
        session_id: Session identifier
        n_turns: Number of turns to distill
        **kwargs: Additional pipeline parameters
        
    Returns:
        Pipeline execution results
    """
    if not ZENML_AVAILABLE:
        logger.error("ZenML is not available - falling back to regular conversation summarizer")
        # Fallback to existing service
        from acc_llamaindex.application.chat_service.session_manager import session_manager
        
        session = session_manager.get_session(session_id)
        if not session:
            return {"facts_created": 0, "status": "error", "error": "Session not found"}
        
        turns = session.conversation_history[-n_turns:] if hasattr(session, 'conversation_history') else []
        result = conversation_summarizer.distill(session_id, turns)
        
        return {
            "facts_stored": result.get("facts_created", 0),
            "status": "success" if result.get("facts_created", 0) > 0 else "no_facts"
        }
    
    return distillation_pipeline(
        session_id=session_id,
        n_turns=n_turns,
        **kwargs
    )
