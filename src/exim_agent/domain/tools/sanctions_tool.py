"""Sanctions screening tool with ITA CSL API integration."""

import time
from datetime import datetime
from typing import Dict, Any
import httpx
from loguru import logger

from .base_tool import ComplianceTool
from src.exim_agent.config import config
from src.exim_agent.infrastructure.db.supabase_client import supabase_client


class SanctionsTool(ComplianceTool):
    """Tool for sanctions screening using ITA Consolidated Screening List API."""
    
    def __init__(self):
        """Initialize sanctions screening tool."""
        super().__init__()
        self.name = "screen_parties"
        self.description = "Screen party names against ITA Consolidated Screening List"
        self.api_base_url = "https://api.trade.gov/consolidated_screening_list/v1/search"
    
    def _run_impl(self, party_name: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Screen party against ITA CSL API.
        
        Args:
            party_name: Name of party to screen
            lane_id: Optional lane identifier for context
        
        Returns:
            Dict containing screening results
        """
        logger.info(f"Screening party against CSL API - Party: {party_name}")
        
        if not party_name or len(party_name.strip()) < 2:
            raise ValueError(f"Invalid party name: {party_name}")
        
        # Fetch data from CSL API (retry logic handled by base class)
        api_data = self._fetch_csl_data(party_name)
        
        # Store in Supabase
        supabase_client.store_compliance_data(
            source_type='sanctions',
            source_id=party_name,
            data=api_data
        )
        
        # Process API response
        return self._process_csl_response(party_name, api_data)
    
    def _fetch_csl_data(self, party_name: str) -> Dict[str, Any]:
        """
        Fetch data from ITA CSL API with retry logic.
        
        Args:
            party_name: Name to search for
            
        Returns:
            API response data
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "ExIM-Agent/1.0 Compliance Tool"
        }
        
        # Add API key if configured
        if config.csl_api_key:
            headers["apikey"] = config.csl_api_key
        
        params = {
            "name": party_name,
            "fuzzy_name": "true",
            "size": 50  # Limit results
        }
        
        # Make the API request (retry logic handled by base class)
        response = self.client.get(
            self.api_base_url,
            params=params,
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    
    def _process_csl_response(self, party_name: str, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process CSL API response into standardized format.
        
        Args:
            party_name: Original party name searched
            api_data: Raw API response
            
        Returns:
            Standardized screening result
        """
        results = api_data.get("results", [])
        total_results = api_data.get("total", 0)
        
        matches_found = total_results > 0
        
        # Determine risk level based on matches
        risk_level = "clear"
        risk_description = "No sanctions matches found"
        sources_checked = ["ITA Consolidated Screening List"]
        
        if matches_found:
            # Analyze match types for risk assessment
            high_risk_sources = ["SDN", "FSE", "NS-ISA", "CAPTA"]
            medium_risk_sources = ["EL", "DTC", "UNITA", "ISN"]
            
            has_high_risk = any(
                result.get("source", "").upper() in high_risk_sources 
                for result in results
            )
            has_medium_risk = any(
                result.get("source", "").upper() in medium_risk_sources 
                for result in results
            )
            
            if has_high_risk:
                risk_level = "high"
                risk_description = "High risk sanctions match found"
            elif has_medium_risk:
                risk_level = "medium" 
                risk_description = "Medium risk sanctions match found"
            else:
                risk_level = "low"
                risk_description = "Low risk sanctions match found"
        
        return {
            "party_name": party_name,
            "matches_found": matches_found,
            "match_count": total_results,
            "matches": results[:5],  # Include first 5 matches for details
            "risk_assessment": {
                "level": risk_level,
                "description": risk_description
            },
            "screening_date": datetime.utcnow().isoformat() + "Z",
            "sources_checked": sources_checked,
            "api_response_summary": {
                "total_results": total_results,
                "sources_found": list(set(result.get("source", "") for result in results))
            }
        }
    
    def _get_fallback_data(self, party_name: str, lane_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Fallback to mock screening when API is unavailable (requirement 7.1).
        
        Args:
            party_name: Name of party to screen
            lane_id: Optional lane identifier
            **kwargs: Additional arguments
            
        Returns:
            Mock screening result
        """
        logger.info(f"Using fallback mock screening for: {party_name}")
        
        # Simple mock screening for fallback
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
                        "description": f"{data['risk_level'].title()} risk sanctions match (mock data)"
                    },
                    "screening_date": datetime.utcnow().isoformat() + "Z",
                    "sources_checked": ["Mock Sanctions List (API Unavailable)"]
                }
        
        # No matches found
        return {
            "party_name": party_name,
            "matches_found": False,
            "match_count": 0,
            "risk_assessment": {
                "level": "clear",
                "description": "No sanctions matches found (mock data)"
            },
            "screening_date": datetime.utcnow().isoformat() + "Z",
            "sources_checked": ["Mock Sanctions List (API Unavailable)"]
        }