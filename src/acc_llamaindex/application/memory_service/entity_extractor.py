"""Entity extractor for identifying key entities in queries."""

import re
from typing import List, Dict, Any
from loguru import logger

from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Extracted entity schema."""
    text: str = Field(description="The entity text as it appears in the query")
    type: str = Field(description="Entity type: port, country, shipper, regulation, commodity, incoterm")
    canonical_id: str = Field(description="Canonical identifier for the entity")


class ExtractedEntities(BaseModel):
    """Collection of extracted entities."""
    entities: List[Entity] = Field(description="List of extracted entities")


class EntityExtractor:
    """
    Extracts entities from user queries using regex + LLM fallback.
    
    Entity types:
    - port: Port codes (DUR, LAG, JNB, etc.)
    - country: Country codes or names (KE, Kenya, China, etc.)
    - shipper: Shipper IDs or names
    - regulation: Regulations (PVOC, SONCAP, etc.)
    - commodity: Product types (electronics, textiles, etc.)
    - incoterm: Incoterms (FOB, CIF, DDP, etc.)
    """
    
    def __init__(self):
        self.llm = get_llm()
        
        # Regex patterns for common entities
        self.patterns = {
            "port": r"\b([A-Z]{3})\b",  # 3-letter port codes
            "country": r"\b(Kenya|Nigeria|China|USA|UK|South Africa)\b",
            "regulation": r"\b(PVOC|SONCAP|SASO|COC)\b",
            "incoterm": r"\b(FOB|CIF|DDP|DDU|EXW|FCA)\b",
            "shipper_id": r"\b(SHIP-\d+)\b"
        }
        
        # Known port codes with canonical IDs
        self.port_codes = {
            "DUR": "port:durban",
            "LAG": "port:lagos",
            "JNB": "port:johannesburg",
            "MBA": "port:mombasa",
            "SHA": "port:shanghai",
            "SHE": "port:shenzhen"
        }
        
        # Known regulations
        self.regulations = {
            "PVOC": "regulation:ke-pvoc",
            "SONCAP": "regulation:ng-soncap",
            "SASO": "regulation:sa-saso",
            "COC": "regulation:coc"
        }
        
        # Known incoterms
        self.incoterms = {
            "FOB": "incoterm:fob",
            "CIF": "incoterm:cif",
            "DDP": "incoterm:ddp",
            "DDU": "incoterm:ddu",
            "EXW": "incoterm:exw",
            "FCA": "incoterm:fca"
        }
        
        # LLM fallback prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract entities from the query for a supply chain/logistics system.

Entity types to extract:
- port: Port names or codes (e.g., Durban, DUR, Lagos)
- country: Country names or codes (e.g., Kenya, KE, China)
- shipper: Shipper names or IDs
- regulation: Regulations (e.g., PVOC, SONCAP)
- commodity: Product types (e.g., electronics, textiles)
- incoterm: Incoterms (e.g., FOB, CIF, DDP)

For each entity:
- text: exact text from query
- type: one of the types above
- canonical_id: normalized ID (e.g., "port:durban", "regulation:pvoc")

Respond with JSON:
{{
  "entities": [
    {{"text": "Durban", "type": "port", "canonical_id": "port:durban"}},
    {{"text": "PVOC", "type": "regulation", "canonical_id": "regulation:ke-pvoc"}}
  ]
}}

If no entities found, return empty list."""),
            ("user", "Query: {query}\n\nExtracted entities:")
        ])
        
        self.parser = JsonOutputParser(pydantic_object=ExtractedEntities)
        self.chain = self.prompt | self.llm | self.parser
        
        logger.info("EntityExtractor initialized")
    
    def extract(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract entities from query using regex + LLM fallback.
        
        Args:
            query: User query text
            
        Returns:
            List of entity dicts with text, type, canonical_id
        """
        entities = []
        
        # 1. Fast regex extraction for known patterns
        regex_entities = self._extract_with_regex(query)
        entities.extend(regex_entities)
        
        # 2. LLM fallback for complex entities
        # Only use LLM if regex didn't find much
        if len(entities) < 2:
            llm_entities = self._extract_with_llm(query)
            # Deduplicate
            for entity in llm_entities:
                if not any(e["canonical_id"] == entity["canonical_id"] for e in entities):
                    entities.append(entity)
        
        logger.info(f"Extracted {len(entities)} entities from query: {query[:50]}")
        for entity in entities:
            logger.debug(f"  - {entity['type']}: {entity['text']} ({entity['canonical_id']})")
        
        return entities
    
    def _extract_with_regex(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns."""
        entities = []
        
        # Port codes
        for match in re.finditer(self.patterns["port"], query):
            port_code = match.group(1)
            if port_code in self.port_codes:
                entities.append({
                    "text": port_code,
                    "type": "port",
                    "canonical_id": self.port_codes[port_code]
                })
        
        # Regulations
        for match in re.finditer(self.patterns["regulation"], query):
            reg = match.group(1)
            if reg in self.regulations:
                entities.append({
                    "text": reg,
                    "type": "regulation",
                    "canonical_id": self.regulations[reg]
                })
        
        # Incoterms
        for match in re.finditer(self.patterns["incoterm"], query):
            incoterm = match.group(1)
            if incoterm in self.incoterms:
                entities.append({
                    "text": incoterm,
                    "type": "incoterm",
                    "canonical_id": self.incoterms[incoterm]
                })
        
        # Shipper IDs
        for match in re.finditer(self.patterns["shipper_id"], query):
            shipper_id = match.group(1)
            entities.append({
                "text": shipper_id,
                "type": "shipper",
                "canonical_id": f"shipper:{shipper_id.lower()}"
            })
        
        return entities
    
    def _extract_with_llm(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities using LLM."""
        try:
            logger.debug(f"Using LLM fallback for entity extraction: {query[:50]}")
            
            result = self.chain.invoke({"query": query})
            
            if not isinstance(result, dict) or "entities" not in result:
                return []
            
            entities = []
            for entity_data in result.get("entities", []):
                # Validate entity structure
                if all(k in entity_data for k in ["text", "type", "canonical_id"]):
                    entities.append({
                        "text": entity_data["text"],
                        "type": entity_data["type"],
                        "canonical_id": entity_data["canonical_id"]
                    })
            
            return entities
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []


# Global singleton instance
entity_extractor = EntityExtractor()
