"""ZenML pipeline for memory promotion."""

from typing import List, Dict, Any
from datetime import datetime
from loguru import logger

from zenml import pipeline, step

ZENML_AVAILABLE = True

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.application.memory_service.promotion import memory_promoter


@step
def scan_episodic_memory(
    salience_threshold: float = 0.8,
    citation_threshold: int = 5,
    age_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 1: Scan episodic memory for promotion candidates.
    
    Args:
        salience_threshold: Minimum salience score
        citation_threshold: Minimum citation count
        age_days: Minimum age in days
        
    Returns:
        List of candidate facts
    """
    logger.info(
        f"Scanning EM for candidates: salience>={salience_threshold}, "
        f"citations>={citation_threshold}, age>={age_days}d"
    )
    
    try:
        episodic_store = chroma_client.get_episodic_store()
        
        # Query high-salience facts
        results = episodic_store.similarity_search(
            "high importance facts",
            k=100,
            filter={"salience": {"$gte": salience_threshold}}
        )
        
        candidates = []
        for doc in results:
            candidates.append({
                "id": doc.metadata.get("id"),
                "text": doc.page_content,
                "metadata": doc.metadata
            })
        
        logger.info(f"Found {len(candidates)} candidates")
        return candidates
        
    except Exception as e:
        logger.error(f"Failed to scan episodic memory: {e}")
        return []


@step
def filter_promotion_candidates(
    facts: List[Dict[str, Any]],
    salience_threshold: float,
    citation_threshold: int,
    age_days: int
) -> List[Dict[str, Any]]:
    """
    Step 2: Apply promotion criteria to filter candidates.
    
    Args:
        facts: Candidate facts from EM
        salience_threshold: Minimum salience score
        citation_threshold: Minimum citation count
        age_days: Minimum age in days
        
    Returns:
        Filtered facts meeting all criteria
    """
    logger.info(f"Filtering {len(facts)} candidates")
    
    promotable = []
    for fact in facts:
        if memory_promoter.should_promote(fact.get("metadata", {})):
            promotable.append(fact)
    
    logger.info(f"Filtered to {len(promotable)} promotable facts")
    return promotable


@step
def transform_for_semantic_memory(
    facts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Step 3: Transform metadata for semantic memory.
    
    Remove session-specific metadata and prepare for SM storage.
    
    Args:
        facts: Facts to transform
        
    Returns:
        Transformed facts
    """
    if not facts:
        return []
    
    logger.info(f"Transforming {len(facts)} facts for semantic memory")
    
    transformed = []
    for fact in facts:
        metadata = fact.get("metadata", {})
        
        # Prepare SM metadata
        sm_metadata = {
            "source": "promoted_from_em",
            "promoted_at": datetime.now().isoformat(),
            "original_session": metadata.get("session_id"),
            "entity_tags": metadata.get("entity_tags", []),
            "salience": metadata.get("salience", 0.8),
            "verified": True,
            "citation_count": metadata.get("citation_count", 0),
            "fact_type": "promoted",
            "provenance": {
                "source_type": "episodic_memory",
                "promoted_from_em": True,
                "original_timestamp": metadata.get("timestamp")
            }
        }
        
        transformed.append({
            "id": fact.get("id"),
            "text": fact.get("text", ""),
            "metadata": sm_metadata
        })
    
    logger.info(f"Transformed {len(transformed)} facts")
    return transformed


@step
def promote_to_semantic_memory(
    facts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Step 4: Copy facts to semantic memory collection.
    
    Args:
        facts: Facts to promote
        
    Returns:
        Promotion statistics
    """
    if not facts:
        logger.warning("No facts to promote")
        return {"promoted": 0, "status": "no_facts"}
    
    logger.info(f"Promoting {len(facts)} facts to semantic memory")
    
    try:
        vector_store = chroma_client.get_vector_store()
        
        # Extract texts and metadata
        texts = [f.get("text", "") for f in facts if f.get("text")]
        metadatas = [f.get("metadata", {}) for f in facts if f.get("text")]
        
        # Add to semantic memory
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        
        logger.info(f"Successfully promoted {len(texts)} facts")
        
        return {
            "promoted": len(texts),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to promote facts: {e}")
        return {
            "promoted": 0,
            "error": str(e),
            "status": "error"
        }


@step
def cleanup_promoted_facts(
    fact_ids: List[str]
) -> Dict[str, Any]:
    """
    Step 5: Remove promoted facts from episodic memory (optional).
    
    Note: Current implementation keeps EM facts for continuity.
    They will expire naturally via TTL.
    
    Args:
        fact_ids: IDs of facts to cleanup
        
    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleanup step for {len(fact_ids)} facts (keeping for TTL expiry)")
    
    # Current design: Keep promoted facts in EM until TTL expires
    # This maintains continuity and allows facts to remain session-specific
    # until they age out naturally
    
    return {
        "cleaned": 0,
        "kept_for_ttl": len(fact_ids),
        "status": "skipped"
    }


@pipeline
def promotion_pipeline(
    salience_threshold: float = 0.8,
    citation_threshold: int = 5,
    age_days: int = 7
) -> Dict[str, Any]:
    """
    Promote episodic facts to semantic memory.
    
    Benefits:
    - Experiment with different promotion thresholds
    - Track promotion rates over time
    - A/B test criteria changes
    - Rollback if promotion degrades quality
    
    Args:
        salience_threshold: Minimum salience score (0-1)
        citation_threshold: Minimum citation count
        age_days: Minimum fact age in days
        
    Returns:
        Promotion statistics
    """
    # Step 1: Scan episodic memory
    candidates = scan_episodic_memory(
        salience_threshold=salience_threshold,
        citation_threshold=citation_threshold,
        age_days=age_days
    )
    
    # Step 2: Filter by criteria
    filtered = filter_promotion_candidates(
        facts=candidates,
        salience_threshold=salience_threshold,
        citation_threshold=citation_threshold,
        age_days=age_days
    )
    
    # Step 3: Transform for SM
    transformed = transform_for_semantic_memory(filtered)
    
    # Step 4: Promote to SM
    result = promote_to_semantic_memory(transformed)
    
    # Step 5: Cleanup (optional)
    fact_ids = [f.get("id", "") for f in transformed if f.get("id")]
    cleanup = cleanup_promoted_facts(fact_ids)
    
    # Combine results
    result["found_candidates"] = len(candidates)
    result["filtered"] = len(filtered)
    result["cleanup"] = cleanup
    
    return result


def run_promotion_pipeline(
    salience_threshold: float | None = None,
    citation_threshold: int | None = None,
    age_days: int | None = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Run the promotion pipeline.
    
    Args:
        salience_threshold: Optional salience threshold (uses config default if None)
        citation_threshold: Optional citation threshold (uses config default if None)
        age_days: Optional age threshold (uses config default if None)
        **kwargs: Additional pipeline parameters
        
    Returns:
        Pipeline execution results
    """
    # Use config defaults if not provided
    salience_threshold = salience_threshold or config.promotion_salience_threshold
    citation_threshold = citation_threshold or config.promotion_citation_count
    age_days = age_days or config.promotion_age_days
    
    if not ZENML_AVAILABLE:
        logger.error("ZenML is not available - falling back to regular memory promoter")
        # Fallback to existing service
        result = memory_promoter.run_promotion_cycle()
        return result
    
    return promotion_pipeline(
        salience_threshold=salience_threshold,
        citation_threshold=citation_threshold,
        age_days=age_days,
        **kwargs
    )
