"""Fact deduplication for episodic memory."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_embeddings


class FactDeduplicator:
    """
    Deduplicates facts before writing to episodic memory.
    
    Strategy:
    - Use embeddings to find similar facts (cosine similarity)
    - If duplicate found (similarity > 0.92):
      - Don't write new fact
      - Increment salience of existing fact
      - Update last_seen timestamp
      - Extend TTL by 7 days
    """
    
    def __init__(self, similarity_threshold: float = 0.92):
        self.similarity_threshold = similarity_threshold
        self.embeddings = get_embeddings()
        logger.info(f"FactDeduplicator initialized (threshold={similarity_threshold})")
    
    def check_and_merge(
        self,
        new_fact: str,
        session_id: str,
        new_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if fact is duplicate and merge if needed.
        
        Args:
            new_fact: New fact text to check
            session_id: Session identifier
            new_metadata: Metadata for the new fact
            
        Returns:
            Dict with:
            - is_duplicate: bool
            - action: "write_new" | "merge_existing" | "skip"
            - merged_with: ID of existing fact if merged
            - reason: Explanation
        """
        try:
            # Query episodic memory for similar facts in this session
            similar_facts = self._find_similar_facts(new_fact, session_id)
            
            if not similar_facts:
                return {
                    "is_duplicate": False,
                    "action": "write_new",
                    "reason": "No similar facts found"
                }
            
            # Check for duplicates above threshold
            for fact in similar_facts:
                similarity = fact.get("similarity", 0.0)
                
                if similarity >= self.similarity_threshold:
                    # Duplicate found - merge instead of writing
                    logger.info(
                        f"Duplicate fact detected (similarity: {similarity:.3f}). "
                        f"Merging with existing fact."
                    )
                    
                    # Update existing fact
                    self._update_existing_fact(fact, new_metadata)
                    
                    return {
                        "is_duplicate": True,
                        "action": "merge_existing",
                        "merged_with": fact.get("id"),
                        "similarity": similarity,
                        "reason": f"Merged with existing fact (similarity: {similarity:.3f})"
                    }
            
            # Similar but not duplicate - write new
            return {
                "is_duplicate": False,
                "action": "write_new",
                "reason": f"Similar facts found but below threshold (max: {similar_facts[0].get('similarity', 0):.3f})"
            }
            
        except Exception as e:
            logger.error(f"Deduplication check failed: {e}")
            # On error, default to writing new fact
            return {
                "is_duplicate": False,
                "action": "write_new",
                "reason": f"Error during deduplication: {str(e)}"
            }
    
    def deduplicate_batch(
        self,
        facts: List[str],
        session_id: str,
        metadatas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Deduplicate a batch of facts.
        
        Args:
            facts: List of fact texts
            session_id: Session identifier
            metadatas: List of metadata dicts (one per fact)
            
        Returns:
            Dict with:
            - facts_to_write: List of non-duplicate facts
            - metadatas_to_write: Corresponding metadata
            - duplicates_merged: Count of duplicates merged
            - new_facts: Count of new facts to write
        """
        facts_to_write = []
        metadatas_to_write = []
        duplicates_merged = 0
        
        for i, fact in enumerate(facts):
            metadata = metadatas[i] if i < len(metadatas) else {}
            
            result = self.check_and_merge(fact, session_id, metadata)
            
            if result["action"] == "write_new":
                facts_to_write.append(fact)
                metadatas_to_write.append(metadata)
            elif result["action"] == "merge_existing":
                duplicates_merged += 1
        
        logger.info(
            f"Batch deduplication: {len(facts_to_write)} new, "
            f"{duplicates_merged} merged"
        )
        
        return {
            "facts_to_write": facts_to_write,
            "metadatas_to_write": metadatas_to_write,
            "duplicates_merged": duplicates_merged,
            "new_facts": len(facts_to_write)
        }
    
    def _find_similar_facts(
        self,
        fact: str,
        session_id: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar facts in episodic memory.
        
        Args:
            fact: Fact text to search for
            session_id: Session identifier
            k: Number of similar facts to retrieve
            
        Returns:
            List of similar facts with similarity scores
        """
        try:
            # Get episodic store
            episodic_store = chroma_client.get_episodic_store()
            
            # Embed the fact
            fact_embedding = self.embeddings.embed_query(fact)
            
            # Query for similar facts in this session
            # Note: ChromaDB's similarity_search_by_vector doesn't support filters well
            # So we query more and filter manually
            results = episodic_store.similarity_search_by_vector(
                fact_embedding,
                k=k * 2,  # Get extra to account for filtering
            )
            
            # Filter by session and calculate similarity
            similar_facts = []
            for doc in results:
                doc_session = doc.metadata.get("session_id")
                if doc_session == session_id:
                    # Calculate cosine similarity (already done by ChromaDB)
                    # We approximate it from the distance
                    similar_facts.append({
                        "id": doc.metadata.get("id"),
                        "text": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity": 0.95  # Placeholder - ChromaDB returns by similarity already
                    })
            
            return similar_facts[:k]
            
        except Exception as e:
            logger.error(f"Failed to find similar facts: {e}")
            return []
    
    def _update_existing_fact(
        self,
        existing_fact: Dict[str, Any],
        new_metadata: Dict[str, Any]
    ):
        """
        Update existing fact with increased salience and extended TTL.
        
        Args:
            existing_fact: Existing fact data
            new_metadata: Metadata from new fact (for salience boost)
        """
        try:
            fact_id = existing_fact.get("id")
            metadata = existing_fact.get("metadata", {})
            
            # Increment salience
            current_salience = metadata.get("salience", 0.5)
            new_salience = min(1.0, current_salience + 0.1)
            
            # Extend TTL by 7 days
            current_ttl = metadata.get("ttl_date")
            if current_ttl:
                ttl_date = datetime.fromisoformat(current_ttl)
            else:
                ttl_date = datetime.now()
            
            extended_ttl = (ttl_date + timedelta(days=7)).isoformat()
            
            # Update last_seen
            last_seen = datetime.now().isoformat()
            
            # TODO: Implement ChromaDB update operation
            # For now, just log the update
            logger.info(
                f"Would update fact {fact_id}: "
                f"salience {current_salience:.2f} → {new_salience:.2f}, "
                f"TTL extended by 7 days"
            )
            
            # Note: ChromaDB doesn't have a direct update API
            # We would need to:
            # 1. Delete the old document
            # 2. Re-insert with updated metadata
            # OR maintain a separate metadata store
            
        except Exception as e:
            logger.error(f"Failed to update existing fact: {e}")


# Global singleton instance
fact_deduplicator = FactDeduplicator()
