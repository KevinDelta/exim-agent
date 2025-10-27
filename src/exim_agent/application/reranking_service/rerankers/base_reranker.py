"""Base reranker interface."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document


class BaseReranker(ABC):
    """Abstract base class for reranking implementations."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents based on relevance to query.
        
        Args:
            query: The search query
            documents: List of documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            List of tuples (document, relevance_score) sorted by score descending
        """
        pass
    
    @abstractmethod
    def get_reranker_name(self) -> str:
        """Get the name of the reranker."""
        pass
    
    def validate_inputs(self, query: str, documents: List[Document]) -> bool:
        """Validate reranking inputs."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not documents:
            raise ValueError("Documents list cannot be empty")
        return True
