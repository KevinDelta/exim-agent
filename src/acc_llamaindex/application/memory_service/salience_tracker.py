"""Salience tracking for memory items."""

from typing import List, Dict, Any
from collections import defaultdict
import threading
from loguru import logger

from acc_llamaindex.infrastructure.db.chroma_client import chroma_client


class SalienceTracker:
    """
    Tracks salience scores for memory items.
    
    Salience increases when memories are:
    - Retrieved and included in context
    - Actually cited in the response
    
    Updates are batched for efficiency.
    """
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.pending_updates = defaultdict(float)  # {doc_id: salience_increment}
        self.lock = threading.Lock()
        logger.info(f"SalienceTracker initialized (batch_size={batch_size})")
    
    def track_usage(self, doc_id: str, increment: float = 0.1):
        """
        Track that a memory item was used.
        
        Args:
            doc_id: Document/fact ID
            increment: Amount to increase salience (default: 0.1)
        """
        with self.lock:
            # Cap salience at 1.0
            current = self.pending_updates[doc_id]
            self.pending_updates[doc_id] = min(1.0, current + increment)
            
            # Batch update if threshold reached
            if len(self.pending_updates) >= self.batch_size:
                self._flush_updates()
    
    def track_citations(self, citations: List[Dict[str, Any]]):
        """
        Track multiple citations from a response.
        
        Args:
            citations: List of citation dicts with 'doc_id' or 'id' field
        """
        for citation in citations:
            doc_id = citation.get("doc_id") or citation.get("id")
            if doc_id:
                # Higher increment for actual citations (0.15 vs 0.1)
                self.track_usage(doc_id, increment=0.15)
    
    def flush(self):
        """Manually flush pending updates to database."""
        with self.lock:
            if self.pending_updates:
                self._flush_updates()
    
    def _flush_updates(self):
        """Internal method to batch update ChromaDB."""
        if not self.pending_updates:
            return
        
        try:
            updates_count = len(self.pending_updates)
            logger.info(f"Flushing {updates_count} salience updates to ChromaDB")
            
            # Update metadata for each document
            # ChromaDB doesn't support batch metadata updates, so we update individually
            # but batch them in a single transaction context
            
            for doc_id, increment in self.pending_updates.items():
                try:
                    # Try updating in both EM and SM collections
                    self._update_document_salience(doc_id, increment)
                    logger.debug(f"  Salience updated: {doc_id} +{increment:.3f}")
                except Exception as e:
                    logger.warning(f"Failed to update salience for {doc_id}: {e}")
            
            # Clear pending updates after successful flush
            self.pending_updates.clear()
            
            logger.info(f"Salience updates flushed successfully")
            
        except Exception as e:
            logger.error(f"Failed to flush salience updates: {e}")
            # Don't clear pending_updates on error - will retry next time
    
    def _update_document_salience(self, doc_id: str, increment: float):
        """
        Update salience for a specific document in ChromaDB.
        
        ChromaDB limitations:
        - No direct metadata update API
        - Must fetch document, update metadata, re-upsert
        
        This is expensive, so we batch these operations.
        """
        
        # Try EM collection first
        try:
            em_store = chroma_client.get_episodic_store()
            collection = em_store._collection
            
            # Get existing document
            result = collection.get(ids=[doc_id], include=["metadatas"])
            
            if result and result["ids"]:
                metadata = result["metadatas"][0]
                current_salience = metadata.get("salience", 0.0)
                new_salience = min(1.0, current_salience + increment)
                
                # Update metadata
                metadata["salience"] = new_salience
                collection.update(ids=[doc_id], metadatas=[metadata])
                return
        except Exception as e:
            logger.debug(f"Not in EM collection: {e}")
        
        # Try SM collection
        try:
            sm_collection = chroma_client.get_collection()
            
            # Get existing document
            result = sm_collection.get(ids=[doc_id], include=["metadatas"])
            
            if result and result["ids"]:
                metadata = result["metadatas"][0]
                current_salience = metadata.get("salience", 0.0)
                new_salience = min(1.0, current_salience + increment)
                
                # Update metadata
                metadata["salience"] = new_salience
                sm_collection.update(ids=[doc_id], metadatas=[metadata])
                return
        except Exception as e:
            logger.debug(f"Not in SM collection: {e}")
        
        # Document not found in either collection
        logger.warning(f"Document {doc_id} not found in any collection")
    
    def decay_salience(self, decay_factor: float = 0.95):
        """
        Apply decay to all salience scores (weekly maintenance).
        
        Args:
            decay_factor: Multiplicative decay (default: 0.95 = 5% decay)
        """
        try:
            logger.info(f"Applying salience decay (factor={decay_factor})")
            
            # TODO: Implement salience decay across all collections
            # This requires:
            # 1. Query all items
            # 2. Update salience = salience * decay_factor
            # 3. Batch update back to ChromaDB
            
            # For now, just log
            logger.info("Salience decay completed (placeholder)")
            
        except Exception as e:
            logger.error(f"Failed to apply salience decay: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get salience tracking statistics."""
        with self.lock:
            return {
                "pending_updates": len(self.pending_updates),
                "batch_size": self.batch_size,
                "will_flush_next": len(self.pending_updates) >= self.batch_size
            }


# Global singleton instance
salience_tracker = SalienceTracker()
