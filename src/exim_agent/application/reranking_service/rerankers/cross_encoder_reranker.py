"""Local cross-encoder reranker using sentence-transformers."""

from typing import List, Tuple
from langchain_core.documents import Document
from loguru import logger
from sentence_transformers import CrossEncoder

from .base_reranker import BaseReranker


class CrossEncoderReranker(BaseReranker):
    """Local cross-encoder model for reranking."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder reranker.
        
        Popular models:
        - cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, good)
        - cross-encoder/ms-marco-MiniLM-L-12-v2 (better, slower)
        - cross-encoder/ms-marco-electra-base (best, slowest)
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        logger.info(f"Loading CrossEncoder model: {model_name}")
        
        try:
            self.model = CrossEncoder(model_name, max_length=512)
            logger.info("CrossEncoder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder model: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Rerank documents using cross-encoder."""
        self.validate_inputs(query, documents)
        
        try:
            # Create query-document pairs
            pairs = [[query, doc.page_content] for doc in documents]
            
            # Get relevance scores
            scores = self.model.predict(pairs)
            
            # Combine documents with scores
            doc_score_pairs = list(zip(documents, scores))
            
            # Sort by score (descending)
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Take top k
            reranked = doc_score_pairs[:top_k]
            
            # Add metadata to documents
            for doc, score in reranked:
                doc.metadata["rerank_score"] = float(score)
                doc.metadata["rerank_model"] = self.model_name
            
            logger.info(f"Reranked {len(documents)} → {len(reranked)} docs")
            return reranked
            
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            # Fallback: return original order with decreasing scores
            return [(doc, 1.0 / (i + 1)) for i, doc in enumerate(documents[:top_k])]
    
    def get_reranker_name(self) -> str:
        """Get the reranker name."""
        return f"cross_encoder_{self.model_name.split('/')[-1]}"
