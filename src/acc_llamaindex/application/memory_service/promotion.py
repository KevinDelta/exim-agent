"""EM to SM promotion for high-value facts."""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client


class MemoryPromoter:
    """
    Promotes high-value episodic memory facts to semantic memory.
    
    Promotion criteria:
    - Salience >= 0.8
    - Citation count >= 5
    - Age >= 7 days
    - Verified = True (optional)
    """
    
    def __init__(self):
        logger.info("MemoryPromoter initialized")
    
    def should_promote(self, fact_metadata: Dict[str, Any]) -> bool:
        """
        Check if a fact meets promotion criteria.
        
        Args:
            fact_metadata: Fact metadata from episodic memory
            
        Returns:
            True if fact should be promoted
        """
        salience = fact_metadata.get("salience", 0.0)
        citation_count = fact_metadata.get("citation_count", 0)
        timestamp_str = fact_metadata.get("timestamp")
        verified = fact_metadata.get("verified", False)
        
        # Calculate age
        age_days = 0
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                age_days = (datetime.now() - timestamp).days
            except Exception as e:
                logger.warning(f"Failed to parse timestamp: {e}")
        
        # Check criteria
        meets_salience = salience >= config.promotion_salience_threshold
        meets_citations = citation_count >= config.promotion_citation_count
        meets_age = age_days >= config.promotion_age_days
        
        # Verification is optional based on config
        # For now, we don't require verification
        
        should_promote = meets_salience and meets_citations and meets_age
        
        if should_promote:
            logger.info(
                f"Fact meets promotion criteria: "
                f"salience={salience:.2f}, citations={citation_count}, age={age_days}d"
            )
        
        return should_promote
    
    def find_promotable_facts(self) -> List[Dict[str, Any]]:
        """
        Find all facts in EM that meet promotion criteria.
        
        Returns:
            List of promotable fact dicts with id, text, metadata
        """
        try:
            episodic_store = chroma_client.get_episodic_store()
            
            # Get all facts from episodic memory
            # Note: This is inefficient for large collections
            # Better approach: Query with metadata filters
            
            # For now, query recent high-salience facts
            results = episodic_store.similarity_search(
                "high importance facts",  # Dummy query
                k=100,  # Get more facts
                filter={"salience": {"$gte": config.promotion_salience_threshold}}
            )
            
            promotable = []
            for doc in results:
                if self.should_promote(doc.metadata):
                    promotable.append({
                        "id": doc.metadata.get("id"),
                        "text": doc.page_content,
                        "metadata": doc.metadata
                    })
            
            logger.info(f"Found {len(promotable)} promotable facts")
            return promotable
            
        except Exception as e:
            logger.error(f"Failed to find promotable facts: {e}")
            return []
    
    def promote_fact(self, fact: Dict[str, Any]) -> bool:
        """
        Promote a single fact from EM to SM.
        
        Args:
            fact: Fact dict with text and metadata
            
        Returns:
            True if promotion succeeded
        """
        try:
            fact_text = fact.get("text", "")
            fact_metadata = fact.get("metadata", {})
            
            if not fact_text:
                logger.warning("Cannot promote empty fact")
                return False
            
            logger.info(f"Promoting fact to semantic memory: {fact_text[:100]}...")
            
            # Prepare metadata for SM
            sm_metadata = {
                "source": "promoted_from_em",
                "promoted_at": datetime.now().isoformat(),
                "original_session": fact_metadata.get("session_id"),
                "entity_tags": fact_metadata.get("entity_tags", []),
                "salience": fact_metadata.get("salience", 0.8),
                "verified": True,  # Promoted facts are considered verified
                "citation_count": fact_metadata.get("citation_count", 0),
                "fact_type": "promoted",
                "provenance": {
                    "source_type": "episodic_memory",
                    "promoted_from_em": True,
                    "original_timestamp": fact_metadata.get("timestamp")
                }
            }
            
            # Write to semantic memory (documents collection)
            vector_store = chroma_client.get_vector_store()
            vector_store.add_texts(
                texts=[fact_text],
                metadatas=[sm_metadata]
            )
            
            logger.info(f"Successfully promoted fact to semantic memory")
            
            # Note: We keep the EM version for continuity
            # It will eventually expire via TTL
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote fact: {e}")
            return False
    
    def promote_batch(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Promote a batch of facts from EM to SM.
        
        Args:
            facts: List of fact dicts
            
        Returns:
            Dict with promotion statistics
        """
        promoted_count = 0
        failed_count = 0
        
        for fact in facts:
            if self.promote_fact(fact):
                promoted_count += 1
            else:
                failed_count += 1
        
        logger.info(
            f"Batch promotion complete: {promoted_count} promoted, "
            f"{failed_count} failed"
        )
        
        return {
            "promoted": promoted_count,
            "failed": failed_count,
            "total": len(facts)
        }
    
    def run_promotion_cycle(self) -> Dict[str, Any]:
        """
        Run a complete promotion cycle.
        
        Finds promotable facts and promotes them.
        Should be called periodically (e.g., nightly).
        
        Returns:
            Promotion statistics
        """
        logger.info("Starting promotion cycle...")
        
        try:
            # Find promotable facts
            promotable = self.find_promotable_facts()
            
            if not promotable:
                logger.info("No facts to promote")
                return {
                    "promoted": 0,
                    "found": 0,
                    "status": "no_promotions"
                }
            
            # Promote them
            result = self.promote_batch(promotable)
            result["found"] = len(promotable)
            result["status"] = "success"
            
            return result
            
        except Exception as e:
            logger.error(f"Promotion cycle failed: {e}")
            return {
                "promoted": 0,
                "found": 0,
                "status": "error",
                "error": str(e)
            }
    
    def cleanup_expired_facts(self) -> int:
        """
        Remove facts from EM that have passed their TTL.
        
        Returns:
            Number of facts removed
        """
        try:
            logger.info("Cleaning up expired EM facts...")
            
            episodic_store = chroma_client.get_episodic_store()
            now = datetime.now().isoformat()
            
            # Query facts with expired TTL
            # Note: ChromaDB doesn't have great support for this
            # Ideally we'd query where ttl_date < now
            
            # TODO: Implement proper TTL-based deletion
            # For now, log placeholder
            logger.info("TTL cleanup completed (placeholder)")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired facts: {e}")
            return 0


# Global singleton instance
memory_promoter = MemoryPromoter()
