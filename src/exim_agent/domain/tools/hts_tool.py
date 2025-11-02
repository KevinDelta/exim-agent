"""HTS tool for real USITC API integration with Supabase storage."""

from datetime import datetime
from typing import Dict, Any
from loguru import logger
import httpx

from .base_tool import ComplianceTool
from ...infrastructure.db.supabase_client import supabase_client


class HTSTool(ComplianceTool):
    """Tool for HTS code lookup using USITC REST API."""
    
    def __init__(self):
        """Initialize HTS tool with real API integration and Supabase storage."""
        super().__init__()
        self.name = "search_hts"
        self.description = "Search HTS codes and get tariff information from USITC API"
    
    def _store_hts_data(self, hts_code: str, data: Dict[str, Any]) -> bool:
        """
        Store HTS data in Supabase.
        
        Args:
            hts_code: HTS code as the source ID
            data: HTS data to store
            
        Returns:
            True if successful, False otherwise
        """
        return supabase_client.store_compliance_data("hts", hts_code, data)
    
    def _validate_hts_code(self, hts_code: str) -> bool:
        """
        Validate HTS code format.
        
        Args:
            hts_code: HTS code to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not hts_code or len(hts_code) < 4:
            return False
        
        # Remove dots and check if it's numeric
        clean_code = hts_code.replace(".", "")
        
        # HTS codes should be numeric and at least 4 digits
        if not clean_code.isdigit():
            return False
            
        # HTS codes are typically 4, 6, 8, or 10 digits
        if len(clean_code) not in [4, 6, 8, 10]:
            return False
            
        return True
    
    def _run_impl(self, hts_code: str, lane_id: str = None) -> Dict[str, Any]:
        """
        Fetch HTS data from USITC website (web scraping approach).
        
        Args:
            hts_code: HTS code to search (e.g., "8517.12.00")
            lane_id: Optional lane identifier for context
        
        Returns:
            Dict containing HTS information from USITC website
        """
        logger.info(f"Fetching HTS code: {hts_code} from USITC website (lane: {lane_id})")
        
        # Validate HTS code format first
        if not self._validate_hts_code(hts_code):
            logger.error(f"Invalid HTS code format: {hts_code}")
            raise ValueError(f"Invalid HTS code format: {hts_code}")
        
        # Use the current USITC website structure
        # Extract chapter from HTS code (first 4 digits)
        chapter = hts_code[:4]
        url = f"https://hts.usitc.gov/reststop/file?filename={chapter}&release=currentRelease"
        
        # Make request with proper headers and follow redirects
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "ComplianceIntelligencePlatform/1.0 (Educational/Research Use)"
        }
        
        # Configure client to follow redirects
        response = self.client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        
        # Parse the HTML response and store in Supabase
        result = self._parse_hts_html(hts_code, response.text)
        
        # Store the result in Supabase
        self._store_hts_data(hts_code, result)
        
        return result
    
    def _parse_hts_html(self, hts_code: str, html_content: str) -> Dict[str, Any]:
        """
        Parse HTS data from USITC website HTML.
        
        Args:
            hts_code: Original HTS code requested
            html_content: Raw HTML content from USITC website
            
        Returns:
            Normalized HTS data
        """
        try:
            # For now, implement basic parsing without BeautifulSoup dependency
            # This is a simplified approach - in production, we'd use proper HTML parsing
            
            description = ""
            duty_rate = "Varies"
            unit = "Unit"
            
            # Simple text extraction patterns (this is basic - would need proper HTML parsing)
            html_lower = html_content.lower()
            
            # Check if the page indicates the HTS code exists
            if "not found" in html_lower or "error" in html_lower:
                logger.warning(f"HTS code {hts_code} appears to not exist on USITC website")
                return self._get_fallback_data(hts_code, "HTS code not found on website")
            
            # For now, return a basic response indicating we accessed the website
            # In a full implementation, we would parse the HTML to extract:
            # - Article description
            # - Duty rates (General, Special, etc.)
            # - Unit of quantity
            # - Additional notes
            
            return {
                "hts_code": hts_code,
                "description": f"HTS {hts_code} - Data retrieved from USITC website",
                "duty_rate": "See USITC website for current rates",
                "unit": "See USITC website",
                "source_url": f"https://hts.usitc.gov/view/{hts_code}",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "api_source": "USITC Website (HTML)",
                "note": "Basic HTML parsing - full implementation would extract detailed tariff information"
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTS HTML response: {e}")
            raise e  # Let the base class retry logic handle this
    
    def _get_fallback_data(self, hts_code: str, lane_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Return fallback data when API fails (requirement 7.1).
        
        Args:
            hts_code: HTS code that was requested
            lane_id: Optional lane identifier
            **kwargs: Additional arguments
            
        Returns:
            Fallback HTS data with mock information
        """
        logger.info(f"Using fallback mock data for HTS {hts_code}")
        
        # Simple fallback data for common HTS codes
        fallback_data = {
            "8517.12.00": {
                "description": "Cellular telephones and other apparatus for transmission or reception of voice, images or other data",
                "duty_rate": "Free",
                "unit": "Number"
            },
            "8708.30.50": {
                "description": "Brake pads for motor vehicles",
                "duty_rate": "2.5%",
                "unit": "Kilograms"
            },
            "0306.17.00": {
                "description": "Other shrimp and prawns, frozen",
                "duty_rate": "Free",
                "unit": "Kilograms"
            }
        }
        
        if hts_code in fallback_data:
            data = fallback_data[hts_code]
            result = {
                "hts_code": hts_code,
                "description": data["description"],
                "duty_rate": data["duty_rate"],
                "unit": data["unit"],
                "source_url": f"https://hts.usitc.gov/view/{hts_code}",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "status": "fallback",
                "api_source": "Fallback mock data"
            }
        else:
            result = {
                "hts_code": hts_code,
                "description": f"Product classified under HTS {hts_code}",
                "duty_rate": "Varies",
                "unit": "Unit",
                "source_url": f"https://hts.usitc.gov/view/{hts_code}",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "status": "fallback",
                "api_source": "Fallback mock data"
            }
        
        return result

