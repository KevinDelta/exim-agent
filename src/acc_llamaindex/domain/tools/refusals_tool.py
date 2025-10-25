"""FDA/FSIS import refusals tool."""

from typing import Dict, Any, List
from loguru import logger

from .base_tool import ComplianceTool


class RefusalsTool(ComplianceTool):
    """Tool for querying FDA and FSIS import refusal data."""
    
    def __init__(self, 
                 fda_url: str = "https://www.accessdata.fda.gov/scripts/importrefusals/",
                 fsis_url: str = "https://www.fsis.usda.gov/inspection/import-export",
                 cache_ttl_seconds: int = 86400):
        """
        Initialize refusals tool.
        
        Args:
            fda_url: Base URL for FDA import refusals
            fsis_url: Base URL for FSIS refusal reports
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        super().__init__(cache_ttl_seconds)
        self.fda_url = fda_url
        self.fsis_url = fsis_url
        self.name = "fetch_refusals"
        self.description = "Fetch FDA and FSIS import refusal data"
    
    def _run_impl(self, hts_code: str = None, product_keyword: str = None, 
                  country: str = None, lane_id: str = None, days: int = 90) -> Dict[str, Any]:
        """
        Query import refusals by HTS code, keyword, or country.
        
        Args:
            hts_code: HTS code to filter by
            product_keyword: Product description keyword
            country: Country of origin (ISO 2-letter code)
            lane_id: Optional lane identifier
            days: Number of days to look back (default: 90)
        
        Returns:
            Dict containing refusal data
        """
        logger.info(f"Querying refusals - HTS: {hts_code}, keyword: {product_keyword}, country: {country}")
        
        if not any([hts_code, product_keyword, country]):
            raise ValueError("Must provide at least one search criterion")
        
        try:
            # In production, query actual FDA/FSIS APIs or scrape data
            # For now, returning mock refusal data
            
            fda_refusals = self._get_mock_fda_refusals(hts_code, product_keyword, country, days)
            fsis_refusals = self._get_mock_fsis_refusals(hts_code, product_keyword, country, days)
            
            all_refusals = fda_refusals + fsis_refusals
            
            return {
                "total_refusals": len(all_refusals),
                "fda_refusals": len(fda_refusals),
                "fsis_refusals": len(fsis_refusals),
                "refusals": all_refusals,
                "search_criteria": {
                    "hts_code": hts_code,
                    "product_keyword": product_keyword,
                    "country": country,
                    "days": days,
                    "lane_id": lane_id
                },
                "risk_level": "warn" if all_refusals else "clear",
                "last_updated": "2025-01-20",
                "sources": [
                    {"name": "FDA Import Refusals", "url": self.fda_url},
                    {"name": "FSIS Import Refusals", "url": self.fsis_url}
                ]
            }
        
        except Exception as e:
            logger.error(f"Error querying refusals: {e}")
            raise
    
    def _get_mock_fda_refusals(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Get mock FDA refusal data.
        
        In production, this would query actual FDA API or scrape their database.
        """
        # Mock FDA refusal database
        mock_refusals = [
            {
                "source": "FDA",
                "date": "2025-01-10",
                "product": "Seafood - frozen shrimp",
                "country": "CN",
                "refusal_reason": "Salmonella",
                "hts_code": "0306.17.00",
                "fda_sample_analysis": "Positive for Salmonella"
            },
            {
                "source": "FDA",
                "date": "2024-12-20",
                "product": "Dried mushrooms",
                "country": "CN",
                "refusal_reason": "Pesticide residue",
                "hts_code": "0712.39.00",
                "fda_sample_analysis": "Pesticide residue exceeds tolerance"
            }
        ]
        
        # Filter based on criteria
        filtered = []
        for refusal in mock_refusals:
            matches = True
            
            if hts_code and refusal["hts_code"] != hts_code:
                matches = False
            
            if keyword and keyword.lower() not in refusal["product"].lower():
                matches = False
            
            if country and refusal["country"] != country:
                matches = False
            
            if matches:
                filtered.append(refusal)
        
        return filtered
    
    def _get_mock_fsis_refusals(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Get mock FSIS refusal data.
        
        In production, this would parse FSIS CSV reports.
        """
        # Mock FSIS refusal database
        mock_refusals = [
            {
                "source": "FSIS",
                "date": "2025-01-05",
                "product": "Fresh beef",
                "country": "BR",
                "refusal_reason": "Lack of equivalency documentation",
                "hts_code": "0201.30.00",
                "fsis_note": "Establishment not on eligible establishments list"
            }
        ]
        
        # Filter based on criteria
        filtered = []
        for refusal in mock_refusals:
            matches = True
            
            if hts_code and refusal["hts_code"] != hts_code:
                matches = False
            
            if keyword and keyword.lower() not in refusal["product"].lower():
                matches = False
            
            if country and refusal["country"] != country:
                matches = False
            
            if matches:
                filtered.append(refusal)
        
        return filtered
    
    def get_refusal_trends(self, country: str, days: int = 180) -> Dict[str, Any]:
        """
        Get refusal trends for a country over time.
        
        Args:
            country: Country code (e.g., "CN", "MX")
            days: Number of days to analyze
        
        Returns:
            Dict with trend analysis
        """
        logger.info(f"Analyzing refusal trends for {country}")
        
        # Mock trend data
        return {
            "country": country,
            "period_days": days,
            "total_refusals": 15,
            "trend": "increasing",  # "increasing", "stable", "decreasing"
            "top_reasons": [
                {"reason": "Salmonella", "count": 6},
                {"reason": "Pesticide residue", "count": 4},
                {"reason": "Filth", "count": 3},
                {"reason": "Lack of documentation", "count": 2}
            ],
            "top_products": [
                {"product": "Seafood", "count": 7},
                {"product": "Dried fruits", "count": 5},
                {"product": "Spices", "count": 3}
            ]
        }
