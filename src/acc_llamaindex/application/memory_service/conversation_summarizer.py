"""Conversation summarizer for distilling facts into episodic memory."""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class DistilledFact(BaseModel):
    """Single distilled fact from conversation."""
    fact: str = Field(description="Atomic factual statement with entities clearly identified")
    entities: List[str] = Field(description="List of entities mentioned (e.g., 'port:durban', 'regulation:pvoc')")
    importance: float = Field(description="Importance score 0-1")


class DistilledFacts(BaseModel):
    """Collection of distilled facts."""
    facts: List[DistilledFact] = Field(description="List of 3-5 atomic facts from the conversation")


class ConversationSummarizer:
    """
    Distills conversations into atomic facts for episodic memory.
    
    Process:
    1. Takes recent conversation turns
    2. Extracts 3-5 atomic facts
    3. Identifies entities in each fact
    4. Assigns importance scores
    5. Writes to episodic memory with metadata
    """
    
    def __init__(self):
        self.llm = get_llm()
        
        # Distillation prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at distilling conversations into atomic facts for a supply chain/logistics system.

Extract 3-5 key facts from the conversation. Each fact should be:
- Atomic (one statement per fact)
- Specific and factual
- Include entities with canonical IDs in parentheses
- Self-contained (can be understood without conversation context)

Entity format: entity_type:canonical_id
Examples: (Port: DUR), (Regulation: KE-PVOC), (Incoterm: DDP), (Shipper: SHIP-123)

For each fact, provide:
- fact: The atomic statement
- entities: List of canonical entity IDs (e.g., ["port:durban", "regulation:ke-pvoc"])
- importance: 0-1 score (how important is this fact?)

Respond with JSON:
{{
  "facts": [
    {{
      "fact": "User requesting quote for electronics shipment to Durban (Port: DUR) under DDP incoterm",
      "entities": ["port:durban", "incoterm:ddp"],
      "importance": 0.8
    }},
    {{
      "fact": "PVOC compliance documentation required for Kenya imports (Regulation: KE-PVOC)",
      "entities": ["regulation:ke-pvoc", "country:kenya"],
      "importance": 0.9
    }}
  ]
}}

Focus on: shipment details, regulatory requirements, pricing discussions, preferences, problems mentioned."""),
            ("user", "Conversation:\n{conversation}\n\nDistilled facts:")
        ])
        
        self.parser = JsonOutputParser(pydantic_object=DistilledFacts)
        self.chain = self.prompt | self.llm | self.parser
        
        logger.info("ConversationSummarizer initialized")
    
    def distill(
        self,
        session_id: str,
        turns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Distill conversation turns into atomic facts.
        
        Args:
            session_id: Session identifier
            turns: List of conversation turns (user/assistant messages)
            
        Returns:
            Dict with facts, metadata, and write status
        """
        if not turns:
            logger.warning("No turns to distill")
            return {"facts_created": 0, "facts": []}
        
        logger.info(f"Distilling {len(turns)} turns for session {session_id}")
        
        # Format conversation for LLM
        conversation_text = self._format_conversation(turns)
        
        try:
            # Invoke distillation chain
            result = self.chain.invoke({"conversation": conversation_text})
            
            if not isinstance(result, dict) or "facts" not in result:
                logger.error("Invalid distillation result format")
                return {"facts_created": 0, "facts": []}
            
            facts = result.get("facts", [])
            logger.info(f"Distilled {len(facts)} facts from conversation")
            
            # Write facts to episodic memory
            written_count = self._write_to_episodic(session_id, facts, turns)
            
            return {
                "facts_created": written_count,
                "facts": facts,
                "session_id": session_id,
                "source_turns": [t.get("turn_number") for t in turns if "turn_number" in t]
            }
            
        except Exception as e:
            logger.error(f"Failed to distill conversation: {e}")
            return {"facts_created": 0, "facts": [], "error": str(e)}
    
    def _format_conversation(self, turns: List[Dict[str, Any]]) -> str:
        """Format conversation turns for LLM."""
        lines = []
        for turn in turns:
            user_msg = turn.get("user_message", "")
            assistant_msg = turn.get("assistant_message", "")
            
            if user_msg:
                lines.append(f"User: {user_msg}")
            if assistant_msg:
                lines.append(f"Assistant: {assistant_msg}")
        
        return "\n".join(lines)
    
    def _write_to_episodic(
        self,
        session_id: str,
        facts: List[Dict[str, Any]],
        source_turns: List[Dict[str, Any]]
    ) -> int:
        """
        Write distilled facts to episodic memory.
        
        Args:
            session_id: Session identifier
            facts: List of distilled facts
            source_turns: Source conversation turns
            
        Returns:
            Number of facts successfully written
        """
        if not facts:
            return 0
        
        try:
            texts = []
            metadatas = []
            
            # Calculate TTL date
            ttl_date = (datetime.now() + timedelta(days=config.em_ttl_days)).isoformat()
            
            # Get source turn numbers
            turn_numbers = [t.get("turn_number") for t in source_turns if "turn_number" in t]
            
            for fact_data in facts:
                fact_text = fact_data.get("fact", "")
                if not fact_text:
                    continue
                
                # Initial salience based on importance score
                importance = fact_data.get("importance", 0.5)
                initial_salience = max(0.5, importance)  # Minimum 0.5
                
                # Extract entity tags
                entity_tags = fact_data.get("entities", [])
                
                # Build metadata
                metadata = {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "salience": initial_salience,
                    "ttl_date": ttl_date,
                    "entity_tags": entity_tags,
                    "source_turns": turn_numbers,
                    "fact_type": "distilled",
                    "citation_count": 0,
                    "verified": False  # Distilled facts start unverified
                }
                
                texts.append(fact_text)
                metadatas.append(metadata)
            
            # Write to episodic memory
            chroma_client.write_episodic(texts, metadatas)
            
            logger.info(f"Wrote {len(texts)} distilled facts to episodic memory")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Failed to write facts to episodic memory: {e}")
            return 0


# Global singleton instance
conversation_summarizer = ConversationSummarizer()
