"""Intent classifier for memory-aware retrieval."""

from typing import Dict, Any
from datetime import timedelta
from functools import lru_cache
from loguru import logger

from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """Intent classification result schema."""
    intent: str = Field(description="The detected intent: quote_request, compliance_query, shipment_tracking, or general")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")


class IntentClassifier:
    """
    Classifies user queries into intents for memory retrieval.
    
    Supported intents:
    - quote_request: User asking for shipping quotes
    - compliance_query: Questions about regulations, PVOC, customs, documentation requirements
    - shipment_tracking: Tracking shipment status
    - general: Other queries
    """
    
    def __init__(self):
        self.llm = get_llm()
        
        # Define classification prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at classifying user queries for a supply chain/logistics system.

Classify the query into ONE of these intents:
- quote_request: User wants shipping quotes, pricing, cost estimates
- compliance_query: Questions about regulations, PVOC, customs, documentation requirements
- shipment_tracking: Tracking shipment status, delivery updates, where is my shipment
- general: Other queries (greetings, clarifications, general questions)

Respond with JSON:
{{
  "intent": "quote_request|compliance_query|shipment_tracking|general",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""),
            ("user", "Query: {query}\n\nClassification:")
        ])
        
        self.parser = JsonOutputParser(pydantic_object=IntentClassification)
        self.chain = self.prompt | self.llm | self.parser
        
        logger.info("IntentClassifier initialized")
    
    @lru_cache(maxsize=256)
    def _classify_cached(self, query: str) -> str:
        """
        Cached classification call (LRU cache for automatic eviction).
        Returns JSON string to be hashable for caching.
        """
        try:
            logger.info(f"Classifying intent for query: {query[:50]}")
            
            # Invoke LLM chain
            result = self.chain.invoke({"query": query})
            
            # Validate result
            if not isinstance(result, dict):
                result = {"intent": "general", "confidence": 0.5, "reasoning": "Failed to parse"}
            
            # Ensure required fields
            classification = {
                "intent": result.get("intent", "general"),
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", "")
            }
            
            # Validate intent value
            valid_intents = ["quote_request", "compliance_query", "shipment_tracking", "general"]
            if classification["intent"] not in valid_intents:
                logger.warning(f"Invalid intent: {classification['intent']}, defaulting to 'general'")
                classification["intent"] = "general"
            
            logger.info(
                f"Intent classified: {classification['intent']} "
                f"(confidence: {classification['confidence']:.2f})"
            )
            
            # Return as JSON string for caching
            import json
            return json.dumps(classification)
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            import json
            return json.dumps({
                "intent": "general",
                "confidence": 0.5,
                "reasoning": f"Error: {str(e)}"
            })
    
    def classify(self, query: str) -> Dict[str, Any]:
        """
        Classify the user query into an intent.
        Uses LRU cache for automatic performance optimization.
        
        Args:
            query: User query text
            
        Returns:
            Dict with intent, confidence, and reasoning
        """
        import json
        result_json = self._classify_cached(query)
        return json.loads(result_json)
    
    def clear_cache(self):
        """Clear the classification cache."""
        self._classify_cached.cache_clear()
        logger.info("Intent classification cache cleared")


# Global singleton instance
intent_classifier = IntentClassifier()
