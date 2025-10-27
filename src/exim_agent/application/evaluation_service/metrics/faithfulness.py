"""Faithfulness metric - measures if answer is grounded in context."""

from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from exim_agent.infrastructure.llm_providers.langchain_provider import get_llm
from .base_metric import BaseMetric


class FaithfulnessMetric(BaseMetric):
    """
    Measures if the generated answer is faithful to the retrieved context.
    
    Score: 0.0 (not faithful) to 1.0 (fully faithful)
    
    Method:
    1. Extract claims from the answer
    2. Check if each claim is supported by context
    3. Score = (supported claims) / (total claims)
    """
    #TODO: Replace claims with something more relevant to supply chain workflows
    #TODO: optimize get_llm() to use a smaller model for evaluation
    def __init__(self):
        """Initialize faithfulness metric."""
        self.llm = get_llm()
         
        self.extract_claims_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract individual factual claims from the answer. List each claim on a new line. Only extract explicit claims, not implied ones."),
            ("user", "Answer: {answer}\n\nClaims:")
        ])
        
        self.verify_claim_prompt = ChatPromptTemplate.from_messages([
            ("system", "Determine if the claim is supported by the context. Answer only 'YES' or 'NO'."),
            ("user", "Context: {context}\n\nClaim: {claim}\n\nIs this claim supported? (YES/NO):")
        ])
        
        logger.info("FaithfulnessMetric initialized")
    
    async def compute(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute faithfulness score."""
        self.validate_inputs(query, response, contexts)
        
        try:
            # Extract claims from the answer
            claims_chain = self.extract_claims_prompt | self.llm
            claims_response = await claims_chain.ainvoke({"answer": response})
            
            # Parse claims (filter out empty lines and headers)
            claims = [
                c.strip() 
                for c in claims_response.content.split('\n') 
                if c.strip() and not c.strip().startswith('#') and not c.strip().startswith('-')
            ]
            
            # Remove numbering if present (e.g., "1. claim" -> "claim")
            claims = [c.split('. ', 1)[-1] if '. ' in c and c[0].isdigit() else c for c in claims]
            
            if not claims:
                return {
                    "score": 1.0,
                    "reason": "No factual claims to verify",
                    "details": {"claims": [], "supported": []}
                }
            
            # Verify each claim against context
            context_text = "\n\n".join(contexts)
            verify_chain = self.verify_claim_prompt | self.llm
            
            supported_claims = []
            for claim in claims:
                verification = await verify_chain.ainvoke({
                    "context": context_text,
                    "claim": claim
                })
                is_supported = "yes" in verification.content.lower()
                supported_claims.append(is_supported)
            
            # Calculate score
            score = sum(supported_claims) / len(claims) if claims else 1.0
            
            return {
                "score": score,
                "reason": f"{sum(supported_claims)}/{len(claims)} claims supported by context",
                "details": {
                    "claims": claims,
                    "supported": supported_claims,
                    "total_claims": len(claims),
                    "supported_claims": sum(supported_claims)
                }
            }
            
        except Exception as e:
            logger.error(f"Faithfulness computation failed: {e}")
            return {"score": 0.0, "reason": f"Error: {str(e)}", "details": {}}
    
    def get_metric_name(self) -> str:
        """Get metric name."""
        return "faithfulness"
