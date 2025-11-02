"""FDA/FSIS import refusals tool with real API integration."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from loguru import logger

from .base_tool import ComplianceTool
from src.exim_agent.config import config
from src.exim_agent.infrastructure.db.supabase_client import supabase_client


class RefusalsTool(ComplianceTool):
    """Tool for querying FDA import refusal data from real API."""
    
    def __init__(self):
        """Initialize FDA refusals tool."""
        super().__init__()
        self.name = "fetch_refusals"
        self.description = "Fetch FDA import refusal data with pagination support"
        self.base_url = "https://api.fda.gov/food/enforcement.json"
        self.timeout = 30.0
    
    def _run_impl(self, country: str = None, product_type: str = None, hts_code: str = None) -> Dict[str, Any]:
        """
        Query FDA Import Refusals API with pagination support.
        
        Args:
            country: Country code to filter by (e.g., "CN", "MX")
            product_type: Product type to filter by
            hts_code: HTS code for filtering (used for source_id)
        
        Returns:
            Dict containing aggregated refusal data
        """
        logger.info(f"Fetching FDA refusals - Country: {country}, Product: {product_type}, HTS: {hts_code}")
        
        # Fetch data from FDA API (retry logic handled by base class)
        refusals_data = self._fetch_fda_data(country, product_type)
        
        # Process and aggregate the data
        processed_data = self._process_refusals_data(refusals_data, country, product_type)
        
        # Store in Supabase
        source_id = hts_code or country or "all_refusals"
        self._store_in_supabase(source_id, refusals_data)
        
        return processed_data
    
    def _fetch_fda_data(self, country: str = None, product_type: str = None) -> List[Dict[str, Any]]:
        """
        Fetch data from FDA API with pagination support.
        
        Args:
            country: Country to filter by
            product_type: Product type to filter by
            
        Returns:
            List of refusal records
        """
        all_results = []
        skip = 0
        limit = 100  # FDA API limit per request
        max_records = 5000  # Maximum records as per requirements
        
        while len(all_results) < max_records:
            params = {
                "limit": min(limit, max_records - len(all_results)),
                "skip": skip
            }
            
            # Build search query
            search_terms = []
            if country:
                search_terms.append(f"country:{country}")
            if product_type:
                search_terms.append(f"product_description:{product_type}")
            
            if search_terms:
                params["search"] = " AND ".join(search_terms)
            
            headers = {}
            if config.fda_api_key:
                headers["Authorization"] = f"Bearer {config.fda_api_key}"
            
            logger.debug(f"Fetching FDA data: skip={skip}, limit={params['limit']}")
            response = self.client.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                logger.info("No FDA refusal data found for query")
                break
                
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.info("No more results from FDA API")
                break
            
            all_results.extend(results)
            skip += len(results)
            
            # Check if we got fewer results than requested (end of data)
            if len(results) < params["limit"]:
                break
        
        logger.info(f"Fetched {len(all_results)} FDA refusal records")
        return all_results
    
    def _process_refusals_data(self, refusals_data: List[Dict[str, Any]], country: str = None, product_type: str = None) -> Dict[str, Any]:
        """
        Process and aggregate FDA refusals data.
        
        Args:
            refusals_data: Raw FDA API response data
            country: Country filter used
            product_type: Product type filter used
            
        Returns:
            Processed refusal data
        """
        total_refusals = len(refusals_data)
        
        # Aggregate by reason/classification
        reasons = {}
        countries = {}
        firms = {}
        
        for refusal in refusals_data:
            # Count reasons
            reason = refusal.get("reason_for_recall", "Unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
            
            # Count countries
            refusal_country = refusal.get("country", "Unknown")
            countries[refusal_country] = countries.get(refusal_country, 0) + 1
            
            # Count firms
            firm = refusal.get("recalling_firm", "Unknown")
            firms[firm] = firms.get(firm, 0) + 1
        
        # Calculate risk level based on total refusals
        if total_refusals >= 10:
            risk_level = "high"
            risk_score = 80
        elif total_refusals >= 3:
            risk_level = "medium"
            risk_score = 50
        else:
            risk_level = "low"
            risk_score = 20
        
        # Get top issues
        top_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]
        key_findings = [f"{reason} ({count} cases)" for reason, count in top_reasons]
        
        return {
            "total_refusals": total_refusals,
            "refusals_by_agency": {
                "FDA": total_refusals,  # All data from FDA API
                "FSIS": 0,  # FSIS data would come from separate source
                "APHIS": 0
            },
            "risk_analysis": {
                "risk_level": risk_level,
                "risk_score": risk_score
            },
            "insights": {
                "key_findings": key_findings,
                "top_countries": dict(list(sorted(countries.items(), key=lambda x: x[1], reverse=True))[:5]),
                "top_firms": dict(list(sorted(firms.items(), key=lambda x: x[1], reverse=True))[:5])
            },
            "query_date": datetime.utcnow().isoformat() + "Z",
            "query_params": {
                "country": country,
                "product_type": product_type
            }
        }
    
    def _store_in_supabase(self, source_id: str, raw_data: List[Dict[str, Any]]) -> None:
        """
        Store refusals data in Supabase.
        
        Args:
            source_id: Identifier for the data (country, HTS code, etc.)
            raw_data: Raw FDA API response data
        """
        try:
            supabase_client.store_compliance_data(
                source_type="refusals",
                source_id=source_id,
                data={
                    "raw_results": raw_data,
                    "total_count": len(raw_data),
                    "fetch_timestamp": datetime.utcnow().isoformat(),
                    "source": "FDA_API"
                }
            )
            logger.info(f"Stored FDA refusals data in Supabase for {source_id}")
        except Exception as e:
            logger.error(f"Failed to store FDA refusals data in Supabase: {e}")
    
    def _get_fallback_data(self, country: str = None, product_type: str = None, hts_code: str = None, **kwargs) -> Dict[str, Any]:
        """
        Fallback mock data when API is unavailable (requirement 7.1).
        
        Args:
            country: Country filter
            product_type: Product type filter
            hts_code: HTS code filter
            **kwargs: Additional arguments
            
        Returns:
            Mock refusal data
        """
        logger.info(f"Using fallback mock data for FDA refusals - Country: {country}, Product: {product_type}")
        
        # Simple mock refusals data for fallback
        mock_refusals = {
            "CN": {"total": 5, "risk": "medium", "issues": ["Salmonella", "Pesticide residue"]},
            "MX": {"total": 2, "risk": "low", "issues": ["Labeling"]},
            "IN": {"total": 8, "risk": "high", "issues": ["Filth", "Salmonella", "Pesticide residue"]},
        }
        
        # Use country-specific data if available
        if country and country in mock_refusals:
            data = mock_refusals[country]
        else:
            data = {"total": 1, "risk": "low", "issues": ["Documentation"]}
        
        return {
            "total_refusals": data["total"],
            "refusals_by_agency": {
                "FDA": data["total"],
                "FSIS": 0,
                "APHIS": 0
            },
            "risk_analysis": {
                "risk_level": data["risk"],
                "risk_score": 70 if data["risk"] == "high" else 40 if data["risk"] == "medium" else 15
            },
            "insights": {
                "key_findings": data["issues"]
            },
            "query_date": datetime.utcnow().isoformat() + "Z",
            "query_params": {
                "country": country,
                "product_type": product_type
            },
            "fallback_data": True
        }