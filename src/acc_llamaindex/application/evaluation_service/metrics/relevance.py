"""Answer relevance metric - measures if answer addresses the question."""

from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from .base_metric import BaseMetric


class AnswerRelevanceMetric(BaseMetric):
    """
    Measures if the generated answer is relevant to the question.
    
    Score: 0.0 (not relevant) to 1.0 (highly relevant)
    """
    
    def __init__(self):
        """Initialize answer relevance metric."""
        self.llm = get_llm()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Rate how well the answer addresses the question on a scale of 1-10.

1-2: Completely irrelevant or off-topic
3-4: Partially addresses question but misses key points
5-6: Addresses question but missing important aspects
7-8: Good answer that addresses most aspects
9-10: Excellent answer that fully addresses the question

Provide only the numeric rating (1-10)."""),
            ("user", "Question: {question}\n\nAnswer: {answer}\n\nRating (1-10):")
        ])
        
        logger.info("AnswerRelevanceMetric initialized")
    
    async def compute(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute answer relevance score."""
        self.validate_inputs(query, response, contexts)
        
        try:
            chain = self.prompt | self.llm
            rating_response = await chain.ainvoke({
                "question": query,
                "answer": response
            })
            
            # Parse rating
            rating_text = rating_response.content.strip()
            
            # Extract first number from response
            import re
            numbers = re.findall(r'\d+', rating_text)
            
            if numbers:
                rating = float(numbers[0])
                rating = max(1.0, min(10.0, rating))  # Clamp to 1-10
            else:
                logger.warning(f"Failed to parse rating from: {rating_text}")
                rating = 5.0  # Default to middle
            
            # Normalize to 0-1 scale
            score = (rating - 1) / 9.0
            
            return {
                "score": score,
                "reason": f"Relevance rating: {rating}/10",
                "details": {
                    "raw_rating": rating,
                    "normalized_score": score
                }
            }
            
        except Exception as e:
            logger.error(f"Answer relevance computation failed: {e}")
            return {"score": 0.0, "reason": f"Error: {str(e)}", "details": {}}
    
    def get_metric_name(self) -> str:
        """Get metric name."""
        return "answer_relevance"
