"""Enhanced sanctions screening tool for OFAC/CSL integration with fuzzy matching."""

import re
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from loguru import logger

import httpx
from .base_tool import ComplianceTool, RetryConfig


class SanctionsTool(ComplianceTool):
    """Enhanced tool for screening parties against multiple sanctions lists with fuzzy matching."""
    
    def __init__(self, 
                 csl_base_url: str = "https://api.trade.gov/consolidated_screening_list/search",
                 ofac_base_url: str = "https://sanctionslistservice.ofac.treas.gov/api/v1",
                 bis_base_url: str = "https://www.bis.doc.gov/api/v1",
                 api_key: Optional[str] = None,
                 cache_ttl_seconds: int = 86400):
        """
        Initialize enhanced sanctions tool.
        
        Args:
            csl_base_url: Base URL for Trade.gov Consolidated Screening List API
            ofac_base_url: Base URL for OFAC API
            bis_base_url: Base URL for BIS Entity List API
            api_key: Optional API key for authenticated requests
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        # Configure retry logic for external API calls
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=15.0,
            exponential_backoff=True,
            jitter=True
        )
        
        # Configure circuit breaker for API failures
        circuit_breaker_config = {
            "failure_threshold": 5,
            "recovery_timeout": 300,  # 5 minutes
        }
        
        super().__init__(
            cache_ttl_seconds=cache_ttl_seconds,
            retry_config=retry_config,
            circuit_breaker_config=circuit_breaker_config
        )
        
        self.csl_base_url = csl_base_url
        self.ofac_base_url = ofac_base_url
        self.bis_base_url = bis_base_url
        self.api_key = api_key
        self.name = "screen_parties"
        self.description = "Screen party names against multiple sanctions lists with fuzzy matching"
        
        # Update HTTP client headers for API authentication
        if self.api_key:
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})
        
        # Fuzzy matching configuration
        self.default_threshold = 0.85
        self.high_confidence_threshold = 0.95
        self.medium_confidence_threshold = 0.80
        
        # Sanctions list priorities (higher number = higher priority)
        self.list_priorities = {
            "SDN": 10,           # Specially Designated Nationals
            "Entity List": 9,    # BIS Entity List
            "DPL": 8,           # Denied Persons List
            "Unverified List": 6, # BIS Unverified List
            "Military End User": 7, # Military End User List
            "Sectoral Sanctions": 8, # OFAC Sectoral Sanctions
            "Non-SDN": 5,       # Non-SDN designations
            "Foreign Sanctions Evaders": 9
        }
        
        # Name normalization patterns
        self.normalization_patterns = [
            (r'\b(LLC|LTD|INC|CORP|CO|COMPANY|LIMITED|INCORPORATED)\b', ''),
            (r'\b(SA|SL|SARL|GMBH|AG|BV|NV|OY|AB|AS|SPA|SRL)\b', ''),
            (r'[^\w\s]', ' '),  # Remove special characters
            (r'\s+', ' ')       # Normalize whitespace
        ]
    
    def _run_impl(self, party_name: str, address: str = None, country: str = None, 
                  lane_id: str = None, threshold: float = None) -> Dict[str, Any]:
        """
        Screen a party name against multiple sanctions lists with enhanced fuzzy matching.
        
        Args:
            party_name: Name of party to screen (company or individual)
            address: Optional address for enhanced matching
            country: Optional country for geographic filtering
            lane_id: Optional lane identifier for context
            threshold: Fuzzy match threshold (0-1, default: 0.85)
        
        Returns:
            Dict containing comprehensive screening results
        """
        if threshold is None:
            threshold = self.default_threshold
            
        logger.info(f"Enhanced screening - Party: {party_name}, Address: {address}, Country: {country}")
        
        if not party_name or len(party_name.strip()) < 2:
            raise ValueError(f"Invalid party name: {party_name}")
        
        try:
            # Normalize party name for better matching
            normalized_name = self._normalize_party_name(party_name)
            
            # Screen against multiple lists
            all_matches = []
            
            # Screen against CSL (Consolidated Screening List)
            csl_matches = self._screen_csl_api(normalized_name, address, country, threshold)
            all_matches.extend(csl_matches)
            
            # Screen against OFAC SDN List
            ofac_matches = self._screen_ofac_api(normalized_name, address, country, threshold)
            all_matches.extend(ofac_matches)
            
            # Screen against BIS Entity List
            bis_matches = self._screen_bis_api(normalized_name, address, country, threshold)
            all_matches.extend(bis_matches)
            
            # Remove duplicates and rank by confidence
            unique_matches = self._deduplicate_and_rank_matches(all_matches)
            
            # Calculate overall risk assessment
            risk_assessment = self._calculate_risk_level(unique_matches)
            
            return {
                "party_name": party_name,
                "normalized_name": normalized_name,
                "address": address,
                "country": country,
                "matches_found": len(unique_matches) > 0,
                "match_count": len(unique_matches),
                "matches": unique_matches,
                "risk_assessment": risk_assessment,
                "threshold": threshold,
                "screening_date": "2025-01-20T00:00:00Z",
                "sources_checked": ["CSL", "OFAC", "BIS"],
                "lane_id": lane_id,
                "recommendations": self._generate_recommendations(unique_matches, risk_assessment)
            }
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error screening party {party_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error screening party {party_name}: {e}")
            raise
    
    def _normalize_party_name(self, party_name: str) -> str:
        """
        Normalize party name for better matching.
        
        Args:
            party_name: Raw party name
            
        Returns:
            Normalized party name
        """
        normalized = party_name.upper().strip()
        
        # Apply normalization patterns
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _screen_csl_api(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """
        Screen against Consolidated Screening List API.
        
        Args:
            party_name: Normalized party name
            address: Optional address
            country: Optional country
            threshold: Matching threshold
            
        Returns:
            List of matches from CSL
        """
        try:
            # In production, make actual API call
            # params = {"name": party_name, "countries": country} if country else {"name": party_name}
            # response = self.client.get(f"{self.csl_base_url}", params=params)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_mock_csl_matches(party_name, address, country, threshold)
            
        except httpx.HTTPError as e:
            logger.warning(f"CSL API error: {e}")
            return []
    
    def _screen_ofac_api(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """
        Screen against OFAC SDN List API.
        
        Args:
            party_name: Normalized party name
            address: Optional address
            country: Optional country
            threshold: Matching threshold
            
        Returns:
            List of matches from OFAC
        """
        try:
            # In production, make actual API call to OFAC
            # params = {"name": party_name, "type": "individual,entity"}
            # response = self.client.get(f"{self.ofac_base_url}/search", params=params)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_mock_ofac_matches(party_name, address, country, threshold)
            
        except httpx.HTTPError as e:
            logger.warning(f"OFAC API error: {e}")
            return []
    
    def _screen_bis_api(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """
        Screen against BIS Entity List API.
        
        Args:
            party_name: Normalized party name
            address: Optional address
            country: Optional country
            threshold: Matching threshold
            
        Returns:
            List of matches from BIS
        """
        try:
            # In production, make actual API call to BIS
            # params = {"name": party_name, "country": country} if country else {"name": party_name}
            # response = self.client.get(f"{self.bis_base_url}/entity_list", params=params)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_mock_bis_matches(party_name, address, country, threshold)
            
        except httpx.HTTPError as e:
            logger.warning(f"BIS API error: {e}")
            return []
    
    def _get_mock_csl_matches(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """Enhanced mock CSL matches with realistic data."""
        mock_entities = [
            {
                "name": "SHANGHAI TELECOM EQUIPMENT CO LTD",
                "alt_names": ["Shanghai Telecom Co., Ltd.", "Shanghai Telecom Equipment"],
                "list": "Entity List",
                "country": "CN",
                "address": "No. 123 Pudong Avenue, Shanghai, China",
                "reason": "Foreign policy concerns - activities contrary to U.S. national security",
                "date_added": "2025-01-15",
                "source": "CSL"
            },
            {
                "name": "GLOBAL IMPORTS INTERNATIONAL",
                "alt_names": ["Global Imports Int'l", "Global Import International"],
                "list": "Unverified List",
                "country": "CN",
                "address": "Building 5, Industrial Park, Shenzhen, China",
                "reason": "Failed end-use check verification",
                "date_added": "2024-11-15",
                "source": "CSL"
            }
        ]
        
        return self._find_fuzzy_matches(party_name, address, mock_entities, threshold)
    
    def _get_mock_ofac_matches(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """Enhanced mock OFAC matches with realistic data."""
        mock_entities = [
            {
                "name": "ACME TRADING LLC",
                "alt_names": ["Acme Trading Limited", "ACME Trade LLC"],
                "list": "SDN",
                "country": "RU",
                "address": "15 Tverskaya Street, Moscow, Russia",
                "reason": "Sanctions evasion activities",
                "date_added": "2024-12-01",
                "source": "OFAC"
            },
            {
                "name": "PETROCHEMICAL INDUSTRIES CORP",
                "alt_names": ["Petrochemical Industries Corporation", "PIC Corp"],
                "list": "Sectoral Sanctions",
                "country": "RU",
                "address": "Moscow, Russian Federation",
                "reason": "Operating in sanctioned sectors",
                "date_added": "2024-10-15",
                "source": "OFAC"
            }
        ]
        
        return self._find_fuzzy_matches(party_name, address, mock_entities, threshold)
    
    def _get_mock_bis_matches(self, party_name: str, address: str, country: str, threshold: float) -> List[Dict[str, Any]]:
        """Enhanced mock BIS matches with realistic data."""
        mock_entities = [
            {
                "name": "ADVANCED TECHNOLOGY SYSTEMS",
                "alt_names": ["Advanced Tech Systems", "ATS Corp"],
                "list": "Entity List",
                "country": "CN",
                "address": "Technology Park, Beijing, China",
                "reason": "Activities contrary to U.S. national security interests",
                "date_added": "2024-09-20",
                "source": "BIS"
            }
        ]
        
        return self._find_fuzzy_matches(party_name, address, mock_entities, threshold)
    
    def _find_fuzzy_matches(self, party_name: str, address: str, entities: List[Dict], threshold: float) -> List[Dict[str, Any]]:
        """
        Find fuzzy matches using enhanced similarity algorithms.
        
        Args:
            party_name: Normalized party name to match
            address: Optional address for enhanced matching
            entities: List of entities to match against
            threshold: Similarity threshold
            
        Returns:
            List of matches with confidence scores
        """
        matches = []
        
        for entity in entities:
            # Calculate name similarity
            name_similarity = self._calculate_enhanced_similarity(party_name, entity["name"])
            
            # Check alternative names
            max_alt_similarity = 0.0
            best_alt_name = None
            for alt_name in entity.get("alt_names", []):
                alt_similarity = self._calculate_enhanced_similarity(party_name, alt_name)
                if alt_similarity > max_alt_similarity:
                    max_alt_similarity = alt_similarity
                    best_alt_name = alt_name
            
            # Use the best similarity score
            best_similarity = max(name_similarity, max_alt_similarity)
            matched_name = entity["name"] if name_similarity >= max_alt_similarity else best_alt_name
            
            # Address matching bonus (if provided)
            address_bonus = 0.0
            if address and entity.get("address"):
                address_similarity = self._calculate_enhanced_similarity(
                    address.upper(), entity["address"].upper()
                )
                address_bonus = address_similarity * 0.1  # 10% bonus for address match
            
            final_confidence = min(best_similarity + address_bonus, 1.0)
            
            if final_confidence >= threshold:
                matches.append({
                    "matched_name": matched_name,
                    "original_name": entity["name"],
                    "list_name": entity["list"],
                    "country": entity["country"],
                    "address": entity.get("address"),
                    "reason": entity["reason"],
                    "date_added": entity["date_added"],
                    "confidence_score": round(final_confidence, 3),
                    "name_similarity": round(best_similarity, 3),
                    "address_similarity": round(address_similarity, 3) if address else None,
                    "source": entity["source"],
                    "match_type": "fuzzy",
                    "priority": self.list_priorities.get(entity["list"], 1)
                })
        
        return matches
    
    def _calculate_enhanced_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate enhanced similarity score using multiple algorithms.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        # Exact match
        if str1 == str2:
            return 1.0
        
        # Sequence matcher (similar to difflib)
        sequence_similarity = SequenceMatcher(None, str1, str2).ratio()
        
        # Token-based Jaccard similarity
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())
        
        if tokens1 and tokens2:
            intersection = tokens1.intersection(tokens2)
            union = tokens1.union(tokens2)
            jaccard_similarity = len(intersection) / len(union)
        else:
            jaccard_similarity = 0.0
        
        # Substring matching
        substring_similarity = 0.0
        if str1 in str2 or str2 in str1:
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            substring_similarity = shorter / longer
        
        # Weighted combination of similarities
        final_similarity = (
            sequence_similarity * 0.5 +
            jaccard_similarity * 0.3 +
            substring_similarity * 0.2
        )
        
        return min(final_similarity, 1.0)
    
    def _deduplicate_and_rank_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate matches and rank by confidence and priority.
        
        Args:
            matches: List of all matches from different sources
            
        Returns:
            Deduplicated and ranked matches
        """
        if not matches:
            return []
        
        # Group matches by normalized name
        grouped_matches = {}
        for match in matches:
            key = self._normalize_party_name(match["matched_name"])
            if key not in grouped_matches:
                grouped_matches[key] = []
            grouped_matches[key].append(match)
        
        # Select best match from each group
        unique_matches = []
        for group in grouped_matches.values():
            # Sort by priority (list importance) then confidence
            best_match = max(group, key=lambda x: (x["priority"], x["confidence_score"]))
            
            # Merge information from multiple sources if available
            if len(group) > 1:
                best_match["multiple_sources"] = True
                best_match["all_sources"] = list(set(m["source"] for m in group))
            else:
                best_match["multiple_sources"] = False
                best_match["all_sources"] = [best_match["source"]]
            
            unique_matches.append(best_match)
        
        # Sort final results by priority and confidence
        unique_matches.sort(key=lambda x: (x["priority"], x["confidence_score"]), reverse=True)
        
        return unique_matches
    
    def _calculate_risk_level(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate overall risk assessment based on matches.
        
        Args:
            matches: List of unique matches
            
        Returns:
            Risk assessment information
        """
        if not matches:
            return {
                "level": "clear",
                "score": 0,
                "description": "No sanctions matches found"
            }
        
        # Calculate risk score based on list priorities and confidence
        max_priority = max(match["priority"] for match in matches)
        max_confidence = max(match["confidence_score"] for match in matches)
        high_confidence_matches = [m for m in matches if m["confidence_score"] >= self.high_confidence_threshold]
        
        # Determine risk level
        if high_confidence_matches and max_priority >= 9:
            risk_level = "critical"
            risk_score = 95
            description = "High-confidence match on critical sanctions list"
        elif max_confidence >= self.high_confidence_threshold and max_priority >= 7:
            risk_level = "high"
            risk_score = 85
            description = "High-confidence match on important sanctions list"
        elif max_confidence >= self.medium_confidence_threshold:
            risk_level = "medium"
            risk_score = 65
            description = "Medium-confidence sanctions match requires review"
        else:
            risk_level = "low"
            risk_score = 35
            description = "Low-confidence potential match"
        
        return {
            "level": risk_level,
            "score": risk_score,
            "description": description,
            "max_confidence": max_confidence,
            "max_priority": max_priority,
            "total_matches": len(matches),
            "high_confidence_matches": len(high_confidence_matches)
        }
    
    def _generate_recommendations(self, matches: List[Dict[str, Any]], risk_assessment: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations based on screening results.
        
        Args:
            matches: List of matches
            risk_assessment: Risk assessment results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not matches:
            recommendations.append("No sanctions concerns identified - proceed with normal due diligence")
            return recommendations
        
        risk_level = risk_assessment["level"]
        
        if risk_level == "critical":
            recommendations.extend([
                "STOP: Do not proceed with transaction",
                "Immediately escalate to compliance team",
                "Conduct thorough investigation of entity identity",
                "Consider legal consultation before any engagement"
            ])
        elif risk_level == "high":
            recommendations.extend([
                "CAUTION: High-risk entity identified",
                "Conduct enhanced due diligence before proceeding",
                "Verify entity identity and address details",
                "Obtain legal clearance before transaction"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "REVIEW: Potential sanctions match requires investigation",
                "Verify if this is the same entity as the sanctioned party",
                "Check additional identifying information (address, registration)",
                "Document investigation results for audit trail"
            ])
        else:  # low risk
            recommendations.extend([
                "LOW RISK: Weak potential match identified",
                "Consider additional verification if high-value transaction",
                "Monitor for any changes in sanctions status"
            ])
        
        # Add specific recommendations based on match types
        sdn_matches = [m for m in matches if m["list_name"] == "SDN"]
        if sdn_matches:
            recommendations.append("SDN List match - U.S. persons prohibited from transactions")
        
        entity_list_matches = [m for m in matches if m["list_name"] == "Entity List"]
        if entity_list_matches:
            recommendations.append("Entity List match - Export license required for controlled items")
        
        return recommendations
    
    def batch_screen(self, parties: List[Dict[str, str]], lane_id: str = None) -> Dict[str, Any]:
        """
        Screen multiple parties at once with enhanced batch processing.
        
        Args:
            parties: List of party dictionaries with 'name', optional 'address', 'country'
            lane_id: Optional lane identifier
        
        Returns:
            Batch screening results with summary
        """
        logger.info(f"Batch screening {len(parties)} parties")
        
        if not parties:
            raise ValueError("No parties provided for screening")
        
        results = []
        summary = {
            "total_parties": len(parties),
            "parties_with_matches": 0,
            "critical_risk_parties": 0,
            "high_risk_parties": 0,
            "medium_risk_parties": 0,
            "low_risk_parties": 0,
            "clear_parties": 0,
            "errors": 0
        }
        
        for party in parties:
            try:
                party_name = party.get("name")
                if not party_name:
                    raise ValueError("Party name is required")
                
                result = self.run(
                    party_name=party_name,
                    address=party.get("address"),
                    country=party.get("country"),
                    lane_id=lane_id
                )
                
                if result.success:
                    screening_data = result.data
                    risk_level = screening_data["risk_assessment"]["level"]
                    
                    if screening_data["matches_found"]:
                        summary["parties_with_matches"] += 1
                    
                    summary[f"{risk_level}_parties"] += 1
                    
                    results.append({
                        "party_name": party_name,
                        "screening_result": screening_data,
                        "success": True
                    })
                else:
                    summary["errors"] += 1
                    results.append({
                        "party_name": party_name,
                        "success": False,
                        "error": result.error
                    })
                    
            except Exception as e:
                logger.error(f"Error screening party {party.get('name', 'unknown')}: {e}")
                summary["errors"] += 1
                results.append({
                    "party_name": party.get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "summary": summary,
            "results": results,
            "batch_id": f"batch_{len(parties)}_{hash(str(parties))}"[:16],
            "screening_date": "2025-01-20T00:00:00Z",
            "lane_id": lane_id
        }
    
    def get_sanctions_list_info(self, list_name: str) -> Dict[str, Any]:
        """
        Get information about a specific sanctions list.
        
        Args:
            list_name: Name of the sanctions list
            
        Returns:
            Information about the sanctions list
        """
        list_info = {
            "SDN": {
                "full_name": "Specially Designated Nationals and Blocked Persons List",
                "agency": "OFAC",
                "description": "Individuals and entities whose assets are blocked and with whom U.S. persons are prohibited from dealing",
                "enforcement": "Criminal and civil penalties up to millions of dollars",
                "update_frequency": "Real-time updates"
            },
            "Entity List": {
                "full_name": "Entity List",
                "agency": "BIS",
                "description": "Foreign entities subject to specific license requirements for exports of specified items",
                "enforcement": "Export license requirements, potential criminal penalties",
                "update_frequency": "Regular updates"
            },
            "DPL": {
                "full_name": "Denied Persons List",
                "agency": "BIS",
                "description": "Individuals and entities denied export privileges",
                "enforcement": "No exports allowed, criminal penalties for violations",
                "update_frequency": "Regular updates"
            },
            "Unverified List": {
                "full_name": "Unverified List",
                "agency": "BIS",
                "description": "End users that BIS has been unable to verify in prior transactions",
                "enforcement": "Enhanced due diligence required",
                "update_frequency": "Regular updates"
            }
        }
        
        return list_info.get(list_name, {
            "full_name": list_name,
            "agency": "Various",
            "description": "Sanctions or export control list",
            "enforcement": "Varies by list",
            "update_frequency": "Varies"
        })
    
    def validate_response_schema(self, data: Dict[str, Any]) -> bool:
        """Validate enhanced sanctions response schema."""
        required_fields = [
            "party_name", "matches_found", "match_count", "risk_assessment",
            "threshold", "sources_checked", "recommendations"
        ]
        
        # Check required fields
        if not all(field in data for field in required_fields):
            return False
        
        # Validate risk_assessment structure
        risk_assessment = data.get("risk_assessment", {})
        required_risk_fields = ["level", "score", "description"]
        if not all(field in risk_assessment for field in required_risk_fields):
            return False
        
        # Validate matches structure if present
        if data["matches_found"] and data["match_count"] > 0:
            matches = data.get("matches", [])
            if not matches:
                return False
            
            required_match_fields = ["matched_name", "list_name", "confidence_score", "source"]
            for match in matches:
                if not all(field in match for field in required_match_fields):
                    return False
        
        return True
