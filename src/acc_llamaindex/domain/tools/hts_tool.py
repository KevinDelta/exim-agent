"""HTS (Harmonized Tariff Schedule) tool for USITC API integration."""

from typing import Dict, Any, List
from loguru import logger

from .base_tool import ComplianceTool


class HTSTool(ComplianceTool):
    """Tool for searching HTS codes and tariff information."""
    
    def __init__(self, base_url: str = "https://hts.usitc.gov/api", cache_ttl_seconds: int = 86400):
        """
        Initialize HTS tool.
        
        Args:
            base_url: Base URL for USITC HTS API
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        super().__init__(cache_ttl_seconds)
        self.base_url = base_url
        self.name = "search_hts"
        self.description = "Search HTS codes and retrieve tariff information"
    
    def _run_impl(self, hts_code: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Search HTS code and get tariff details.
        
        Args:
            hts_code: HTS code to search (e.g., "8517.12.00")
            lane_id: Optional lane identifier for context
        
        Returns:
            Dict containing HTS information
        """
        logger.info(f"Searching HTS code: {hts_code} (lane: {lane_id})")
        
        # Validate HTS code format
        if not hts_code or len(hts_code) < 4:
            raise ValueError(f"Invalid HTS code format: {hts_code}")
        
        # Normalize HTS code
        hts_code = hts_code.upper().strip()
        
        # Extract chapter and heading from HTS code
        chapter = hts_code[:2]
        heading = hts_code[:4] if len(hts_code) >= 4 else chapter
        
        try:
            # In production, this would make actual API calls to USITC
            # For now, using mock data with realistic structure
            
            # Simulate API call with proper error handling
            # response = self.client.get(
            #     f"{self.base_url}/search",
            #     params={"code": hts_code, "format": "json"}
            # )
            # response.raise_for_status()
            # api_data = response.json()
            
            # Mock response based on common HTS codes
            mock_data = self._get_mock_hts_data(hts_code, chapter, heading)
            
            result = {
                "hts_code": hts_code,
                "chapter": chapter,
                "heading": heading,
                "description": mock_data["description"],
                "duty_rate": mock_data["duty_rate"],
                "unit_of_quantity": mock_data["unit"],
                "notes": mock_data["notes"],
                "special_requirements": mock_data.get("special_requirements", []),
                "last_updated": "2025-01-20T00:00:00Z",
                "source_url": f"{self.base_url}/view/{hts_code}",
                "lane_id": lane_id,
                "data_quality": "high"  # Indicate data reliability
            }
            
            # Validate response schema
            if not self.validate_response_schema(result):
                raise ValueError("Invalid response schema from HTS API")
            
            return result
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying HTS API for {hts_code}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Validation error for HTS {hts_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying HTS API for {hts_code}: {e}")
            raise
    
    def validate_response_schema(self, data: Dict[str, Any]) -> bool:
        """Validate HTS response schema."""
        required_fields = ["hts_code", "description", "duty_rate", "unit_of_quantity"]
        return all(field in data for field in required_fields)
    
    def _get_mock_hts_data(self, hts_code: str, chapter: str, heading: str) -> Dict[str, Any]:
        """
        Get mock HTS data for testing.
        
        In production, this would be replaced with actual API calls.
        """
        # Common HTS codes for testing with enhanced data
        mock_database = {
            "8517.12.00": {
                "description": "Cellular telephones and smartphones",
                "duty_rate": "Free",
                "unit": "Number",
                "notes": ["Subject to FCC equipment authorization requirements"],
                "special_requirements": ["FCC_ID", "Section_301_China"]
            },
            "8708.30.50": {
                "description": "Brake pads for motor vehicles",
                "duty_rate": "2.5%",
                "unit": "Kilograms",
                "notes": ["Check country-specific origin rules for duty rates"],
                "special_requirements": ["Country_of_Origin_Marking", "USMCA_Eligible"]
            },
            "6203.42.40": {
                "description": "Men's or boys' trousers and breeches of cotton",
                "duty_rate": "16.6%",
                "unit": "Dozen",
                "notes": ["Textile category 347/348", "Subject to textile visa requirements from certain countries"],
                "special_requirements": ["Textile_Visa", "Cotton_Category", "Section_301_China"]
            },
            "0306.17.00": {
                "description": "Frozen shrimp and prawns",
                "duty_rate": "Free",
                "unit": "Kilograms",
                "notes": ["Subject to FDA inspection", "HACCP requirements apply"],
                "special_requirements": ["FDA_Registration", "HACCP_Plan"]
            },
            "0201.30.02": {
                "description": "Fresh or chilled beef, boneless",
                "duty_rate": "4.4¢/kg",
                "unit": "Kilograms",
                "notes": ["Subject to FSIS inspection", "Establishment must be on eligible list"],
                "special_requirements": ["FSIS_Eligible_Establishment", "Health_Certificate"]
            }
        }
        
        if hts_code in mock_database:
            return mock_database[hts_code]
        else:
            # Default generic response based on chapter
            chapter_descriptions = {
                "01": "Live animals",
                "02": "Meat and edible meat offal",
                "03": "Fish and crustaceans",
                "62": "Articles of apparel and clothing accessories, not knitted",
                "85": "Electrical machinery and equipment",
                "87": "Vehicles other than railway or tramway"
            }
            
            return {
                "description": f"HTS {hts_code} - {chapter_descriptions.get(chapter, f'Chapter {chapter}')}",
                "duty_rate": "Varies by country",
                "unit": "Unit",
                "notes": [f"Consult HTS for detailed information on chapter {chapter}"],
                "special_requirements": []
            }
    
    def search_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search HTS codes by keyword.
        
        Args:
            keyword: Search keyword (e.g., "phone", "automobile parts")
            limit: Maximum number of results
        
        Returns:
            List of matching HTS entries
        """
        logger.info(f"Searching HTS by keyword: {keyword}")
        
        # In production, this would query the USITC API
        # For now, returning mock results
        
        keyword_lower = keyword.lower()
        results = []
        
        if "phone" in keyword_lower or "cellular" in keyword_lower:
            results.append({
                "hts_code": "8517.12.00",
                "description": "Cellular telephones and smartphones",
                "duty_rate": "Free"
            })
        
        if "brake" in keyword_lower or "auto" in keyword_lower:
            results.append({
                "hts_code": "8708.30.50",
                "description": "Brake pads for motor vehicles",
                "duty_rate": "2.5%"
            })
        
        if "clothing" in keyword_lower or "trouser" in keyword_lower:
            results.append({
                "hts_code": "6203.42.40",
                "description": "Men's trousers of cotton",
                "duty_rate": "16.6%"
            })
        
        return results[:limit]
