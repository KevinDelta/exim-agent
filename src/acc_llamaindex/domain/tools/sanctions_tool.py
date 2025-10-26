"""Simple sanctions screening tool for MVP compliance monitoring."""

from typing import Dict, Any
from loguru import logger

from .base_tool import ComplianceTool


class SanctionsTool(ComplianceTool):
    """Simple tool for basic sanctions screening."""
    
    def __init__(self):
        """Initialize simple sanctions tool."""
        super().__init__()
        self.name = "screen_parties"
        self.description = "Screen party names against sanctions lists"
    
    def _run_impl(self, party_name: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Simple sanctions screening.
        
        Args:
            party_name: Name of party to screen
            lane_id: Optional lane identifier for context
        
        Returns:
            Dict containing basic screening results
        """
        logger.info(f"Enhanced screening - Party: {party_name}, Address: None, Country: None")
        
        if not party_name or len(party_name.strip()) < 2:
            raise ValueError(f"Invalid party name: {party_name}")
        
        # Simple mock screening for MVP
        mock_sanctions = {
            "ACME TRADING LLC": {
                "matches_found": True,
                "match_count": 1,
                "risk_level": "high"
            },
            "SHANGHAI TELECOM": {
                "matches_found": True,
                "match_count": 1,
                "risk_level": "medium"
            }
        }
        
        # Check for matches (case insensitive)
        party_upper = party_name.upper()
        for sanctioned_name, data in mock_sanctions.items():
            if sanctioned_name in party_upper or party_upper in sanctioned_name:
                return {
                    "party_name": party_name,
                    "matches_found": data["matches_found"],
                    "match_count": data["match_count"],
                    "risk_assessment": {
                        "level": data["risk_level"],
                        "description": f"{data['risk_level'].title()} risk sanctions match"
                    },
                    "screening_date": "2025-01-20T00:00:00Z",
                    "sources_checked": ["Mock Sanctions List"]
                }
        
        # No matches found
        return {
            "party_name": party_name,
            "matches_found": False,
            "match_count": 0,
            "risk_assessment": {
                "level": "clear",
                "description": "No sanctions matches found"
            },
            "screening_date": "2025-01-20T00:00:00Z",
            "sources_checked": ["Mock Sanctions List"]
        }