"""Main reranking service."""

from typing import List, Optional
from langchain_core.documents import Document
from loguru import logger

from exim_agent.config import config
from .rerankers.base_reranker import BaseReranker
from .rerankers.cross_encoder_reranker import CrossEncoderReranker


class RerankingService:
    """Service for reranking retrieved documents."""
    
    def __init__(self):
        """Initialize reranking service."""
        self.reranker: Optional[BaseReranker] = None
        logger.info("RerankingService initialized")
    
    def initialize(self):
        """Initialize the reranker based on configuration."""
        if not config.enable_reranking:
            logger.info("Reranking disabled by configuration")
            self.reranker = None
            return
        
        try:
            logger.info(f"Initializing CrossEncoderReranker with model: {config.cross_encoder_model}")
            self.reranker = CrossEncoderReranker(model_name=config.cross_encoder_model)
            logger.info(f"Reranker initialized: {self.reranker.get_reranker_name()}")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            self.reranker = None
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        Rerank documents for a query.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top documents to return (defaults to config.rerank_top_k)
            
        Returns:
            List of reranked documents (without scores)
        """
        if not self.reranker:
            # If reranker not initialized, return original documents
            return documents[:top_k] if top_k else documents
        
        if not documents:
            return []
        
        top_k = top_k or config.rerank_top_k
        
        try:
            reranked_with_scores = self.reranker.rerank(query, documents, top_k)
            # Return just the documents (without scores)
            return [doc for doc, score in reranked_with_scores]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Fallback to original order
            return documents[:top_k]
    
    def is_enabled(self) -> bool:
        """Check if reranking is enabled and initialized."""
        return self.reranker is not None


# Global singleton instance
reranking_service = RerankingService()
