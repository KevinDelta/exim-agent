"""Main memory service for orchestrating recall across memory tiers."""

from typing import List, Dict, Any, Optional
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.application.reranking_service import reranking_service


class MemoryService:
    """
    Orchestrates memory recall across WM, EM, and SM tiers.
    
    Responsibilities:
    - Coordinate retrieval from multiple memory tiers
    - Apply intent-based filtering
    - Deduplicate and merge results
    - Track salience scores
    """
    
    def __init__(self):
        logger.info("MemoryService initialized")
    
    def recall(
        self,
        query: str,
        session_id: str,
        intent: str = "general",
        entities: Optional[List[Dict[str, Any]]] = None,
        k_em: Optional[int] = None,
        k_sm: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Recall relevant memories from all tiers.
        
        Args:
            query: User query text
            session_id: Session identifier for EM filtering
            intent: Detected intent (quote_request, compliance_query, etc.)
            entities: Extracted entities with types and IDs
            k_em: Number of EM results (default: config.em_k_default)
            k_sm: Number of SM results (default: config.sm_k_default)
            
        Returns:
            Dict with em_results, sm_results, combined_results, and metadata
        """
        if not config.enable_memory_system:
            return {
                "em_results": [],
                "sm_results": [],
                "combined_results": [],
                "metadata": {"memory_system_enabled": False}
            }
        
        k_em = k_em or config.em_k_default
        k_sm = k_sm or config.sm_k_default
        entities = entities or []
        
        logger.info(
            f"Memory recall: query={query[:50]}, intent={intent}, "
            f"session={session_id}, entities={len(entities)}"
        )
        
        # Query episodic memory (session-specific)
        em_results = self._query_episodic(session_id, query, k_em)
        
        # Query semantic memory (entity + intent filtered)
        sm_results = self._query_semantic(query, intent, entities, k_sm)
        
        # Merge and deduplicate
        combined = self._merge_results(em_results, sm_results)
        
        # Rerank if enabled
        if config.enable_reranking and reranking_service.is_enabled():
            combined = self._rerank_results(query, combined)
        
        return {
            "em_results": em_results,
            "sm_results": sm_results,
            "combined_results": combined,
            "metadata": {
                "intent": intent,
                "entities": entities,
                "em_count": len(em_results),
                "sm_count": len(sm_results),
                "combined_count": len(combined)
            }
        }
    
    def _query_episodic(
        self,
        session_id: str,
        query: str,
        k: int
    ) -> List[Dict[str, Any]]:
        """Query episodic memory collection."""
        try:
            docs = chroma_client.query_episodic(session_id, query, k)
            
            results = []
            for doc in docs:
                results.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "source": "EM",
                    "salience": doc.metadata.get("salience", 0.5)
                })
            
            logger.debug(f"Retrieved {len(results)} EM results for session {session_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query episodic memory: {e}")
            return []
    
    def _query_semantic(
        self,
        query: str,
        intent: str,
        entities: List[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """Query semantic memory with intent and entity filters."""
        try:
            vector_store = chroma_client.get_vector_store()
            
            # Build metadata filter
            where_filter = {}
            
            # Filter by verified status for compliance queries
            if intent == "compliance_query" and config.sm_verified_only:
                where_filter["verified"] = True
            
            # Filter by entity tags if entities detected
            if entities:
                entity_ids = [e.get("canonical_id") for e in entities if e.get("canonical_id")]
                if entity_ids:
                    # ChromaDB $in operator for matching any entity
                    where_filter["entity_tags"] = {"$in": entity_ids}
            
            # Query with filters
            if where_filter:
                docs = vector_store.similarity_search(
                    query,
                    k=k,
                    filter=where_filter
                )
            else:
                # No filters, standard search
                docs = vector_store.similarity_search(query, k=k)
            
            results = []
            for doc in docs:
                results.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "source": "SM",
                    "salience": doc.metadata.get("salience", 0.0)
                })
            
            logger.debug(
                f"Retrieved {len(results)} SM results for intent={intent}, "
                f"entities={len(entities)}"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []
    
    def _merge_results(
        self,
        em_results: List[Dict[str, Any]],
        sm_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge EM and SM results, removing duplicates.
        
        Deduplication strategy:
        - Exact text match
        - Prefer EM over SM for duplicates (more recent/relevant)
        """
        seen_texts = set()
        merged = []
        
        # Add EM results first (priority)
        for result in em_results:
            text = result["text"]
            if text not in seen_texts:
                seen_texts.add(text)
                merged.append(result)
        
        # Add SM results (deduplicate)
        for result in sm_results:
            text = result["text"]
            if text not in seen_texts:
                seen_texts.add(text)
                merged.append(result)
        
        logger.debug(
            f"Merged results: {len(em_results)} EM + {len(sm_results)} SM "
            f"= {len(merged)} (deduped)"
        )
        
        return merged
    
    def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank combined results using reranking service."""
        try:
            # Convert to LangChain Document format for reranking
            from langchain_core.documents import Document
            
            docs = [
                Document(
                    page_content=r["text"],
                    metadata=r["metadata"]
                )
                for r in results
            ]
            
            # Rerank
            reranked_docs = reranking_service.rerank(
                query,
                docs,
                top_k=config.rerank_top_k
            )
            
            # Convert back using O(n) lookup dict instead of O(n²) nested loop
            text_to_result = {r["text"]: r for r in results}
            reranked_results = [
                text_to_result[doc.page_content]
                for doc in reranked_docs
                if doc.page_content in text_to_result
            ]
            
            logger.debug(f"Reranked {len(results)} results to top {len(reranked_results)}")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Failed to rerank results: {e}")
            return results[:config.rerank_top_k]  # Fallback: just truncate


# Global singleton instance
memory_service = MemoryService()
