"""Sanctions screening tool for OFAC/CSL integration."""

from typing import Dict, Any, List
from loguru import logger

from .base_tool import ComplianceTool


class SanctionsTool(ComplianceTool):
    """Tool for screening parties against OFAC Consolidated Screening List."""
    
    def __init__(self, base_url: str = "https://api.trade.gov/consolidated_screening_list/search", 
                 cache_ttl_seconds: int = 86400):
        """
        Initialize sanctions tool.
        
        Args:
            base_url: Base URL for Trade.gov CSL API
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        super().__init__(cache_ttl_seconds)
        self.base_url = base_url
        self.name = "screen_parties"
        self.description = "Screen party names against OFAC/CSL sanctions lists"
    
    def _run_impl(self, party_name: str, lane_id: str = None, threshold: float = 0.85) -> Dict[str, Any]:
        """
        Screen a party name against sanctions lists.
        
        Args:
            party_name: Name of party to screen (company or individual)
            lane_id: Optional lane identifier for context
            threshold: Fuzzy match threshold (0-1, default: 0.85)
        
        Returns:
            Dict containing screening results
        """
        logger.info(f"Screening party: {party_name} (lane: {lane_id})")
        
        if not party_name or len(party_name) < 2:
            raise ValueError(f"Invalid party name: {party_name}")
        
        try:
            # In production, query the actual CSL API:
            # response = self.client.get(f"{self.base_url}?name={party_name}")
            # response.raise_for_status()
            # data = response.json()
            
            # Mock screening logic
            matches = self._screen_against_mock_list(party_name, threshold)
            
            return {
                "party_name": party_name,
                "matches_found": len(matches) > 0,
                "match_count": len(matches),
                "matches": matches,
                "threshold": threshold,
                "last_updated": "2025-01-20",
                "source_url": self.base_url,
                "lane_id": lane_id,
                "risk_level": "critical" if matches else "clear"
            }
        
        except Exception as e:
            logger.error(f"Error screening party {party_name}: {e}")
            raise
    
    def _screen_against_mock_list(self, party_name: str, threshold: float) -> List[Dict[str, Any]]:
        """
        Screen against mock sanctions list.
        
        In production, this would query the actual OFAC/CSL API.
        """
        # Mock sanctioned entities database
        sanctioned_entities = [
            {
                "name": "Shanghai Telecom Co., Ltd.",
                "list": "Entity List",
                "country": "CN",
                "reason": "Foreign policy concerns",
                "date_added": "2025-01-15"
            },
            {
                "name": "Acme Trading LLC",
                "list": "SDN List",
                "country": "RU",
                "reason": "Sanctions evasion",
                "date_added": "2024-12-01"
            },
            {
                "name": "Global Imports International",
                "list": "Unverified List",
                "country": "CN",
                "reason": "Failed verification",
                "date_added": "2024-11-15"
            }
        ]
        
        matches = []
        party_name_lower = party_name.lower()
        
        for entity in sanctioned_entities:
            entity_name_lower = entity["name"].lower()
            
            # Simple fuzzy matching (in production, use proper fuzzy matching library)
            if (party_name_lower in entity_name_lower or 
                entity_name_lower in party_name_lower or
                self._calculate_similarity(party_name_lower, entity_name_lower) >= threshold):
                
                matches.append({
                    "matched_name": entity["name"],
                    "list_name": entity["list"],
                    "country": entity["country"],
                    "reason": entity["reason"],
                    "date_added": entity["date_added"],
                    "confidence": 0.95,  # Mock confidence score
                    "recommendation": "Review supplier - potential sanctions risk"
                })
        
        return matches
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate simple similarity score between two strings.
        
        In production, use proper fuzzy matching (e.g., fuzzywuzzy, rapidfuzz).
        """
        # Simple token-based similarity
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def batch_screen(self, party_names: List[str], lane_id: str = None) -> List[Dict[str, Any]]:
        """
        Screen multiple parties at once.
        
        Args:
            party_names: List of party names to screen
            lane_id: Optional lane identifier
        
        Returns:
            List of screening results
        """
        logger.info(f"Batch screening {len(party_names)} parties")
        
        results = []
        for party_name in party_names:
            try:
                result = self.run(party_name=party_name, lane_id=lane_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error screening {party_name}: {e}")
                results.append({
                    "success": False,
                    "party_name": party_name,
                    "error": str(e)
                })
        
        return results
