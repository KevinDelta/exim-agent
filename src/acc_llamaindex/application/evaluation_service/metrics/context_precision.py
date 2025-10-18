"""Context precision - measures if retrieved docs are relevant."""

from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from .base_metric import BaseMetric


class ContextPrecisionMetric(BaseMetric):
    """
    Measures precision of retrieved context.
    
    Score: 0.0 (no relevant docs) to 1.0 (all docs relevant)
    """
    
    def __init__(self):
        """Initialize context precision metric."""
        self.llm = get_llm()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "Determine if the context is relevant to answering the question. Answer only 'YES' or 'NO'."),
            ("user", "Question: {question}\n\nContext: {context}\n\nIs this context relevant? (YES/NO):")
        ])
        
        logger.info("ContextPrecisionMetric initialized")
    
    async def compute(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute context precision score."""
        self.validate_inputs(query, response, contexts)
        
        try:
            chain = self.prompt | self.llm
            
            relevant_contexts = []
            for context in contexts:
                # Truncate very long contexts to avoid token limits
                context_snippet = context[:1000] if len(context) > 1000 else context
                
                relevance_response = await chain.ainvoke({
                    "question": query,
                    "context": context_snippet
                })
                
                is_relevant = "yes" in relevance_response.content.lower()
                relevant_contexts.append(is_relevant)
            
            # Calculate precision
            score = sum(relevant_contexts) / len(contexts) if contexts else 0.0
            
            return {
                "score": score,
                "reason": f"{sum(relevant_contexts)}/{len(contexts)} contexts relevant to question",
                "details": {
                    "total_contexts": len(contexts),
                    "relevant_contexts": sum(relevant_contexts),
                    "relevance_per_context": relevant_contexts
                }
            }
            
        except Exception as e:
            logger.error(f"Context precision computation failed: {e}")
            return {"score": 0.0, "reason": f"Error: {str(e)}", "details": {}}
    
    def get_metric_name(self) -> str:
        """Get metric name."""
        return "context_precision"
