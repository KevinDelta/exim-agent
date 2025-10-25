"""CBP CROSS rulings tool."""

from typing import Dict, Any, List
from loguru import logger

from .base_tool import ComplianceTool


class RulingsTool(ComplianceTool):
    """Tool for searching CBP CROSS (Customs Rulings Online Search System)."""
    
    def __init__(self, base_url: str = "https://rulings.cbp.gov", cache_ttl_seconds: int = 86400):
        super().__init__(cache_ttl_seconds)
        self.base_url = base_url
        self.name = "find_rulings"
        self.description = "Search CBP classification rulings"
    
    def _run_impl(self, hts_code: str = None, keyword: str = None, 
                  ruling_number: str = None, lane_id: str = None) -> Dict[str, Any]:
        """Search for CBP rulings."""
        logger.info(f"Searching rulings - HTS: {hts_code}, keyword: {keyword}")
        
        if not any([hts_code, keyword, ruling_number]):
            raise ValueError("Must provide at least one search criterion")
        
        rulings = self._get_mock_rulings(hts_code, keyword, ruling_number)
        
        return {
            "total_rulings": len(rulings),
            "rulings": rulings,
            "search_criteria": {"hts_code": hts_code, "keyword": keyword, "ruling_number": ruling_number, "lane_id": lane_id},
            "last_updated": "2025-01-20",
            "source_url": f"{self.base_url}/search"
        }
    
    def _get_mock_rulings(self, hts_code: str, keyword: str, ruling_number: str) -> List[Dict[str, Any]]:
        """Mock rulings data."""
        mock_rulings = [
            {
                "ruling_number": "N312345",
                "date": "2024-12-15",
                "hts_code": "8517.12.00",
                "description": "Cellular phones with dual SIM",
                "classification": "HTS 8517.12.00 - Free of duty",
                "ruling_url": f"{self.base_url}/ruling/N312345"
            },
            {
                "ruling_number": "N312346",
                "date": "2024-11-20",
                "hts_code": "8708.30.50",
                "description": "Brake pads for passenger vehicles",
                "classification": "HTS 8708.30.50 - 2.5% duty",
                "ruling_url": f"{self.base_url}/ruling/N312346"
            }
        ]
        
        # Filter based on criteria
        filtered = []
        for ruling in mock_rulings:
            matches = True
            if hts_code and not ruling["hts_code"].startswith(hts_code[:4]):
                matches = False
            if keyword and keyword.lower() not in ruling["description"].lower():
                matches = False
            if ruling_number and ruling["ruling_number"] != ruling_number:
                matches = False
            if matches:
                filtered.append(ruling)
        
        return filtered
