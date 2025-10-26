"""Enhanced CBP CROSS rulings tool with semantic search and relevance scoring."""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from loguru import logger

import httpx
from .base_tool import ComplianceTool, RetryConfig


class RulingsTool(ComplianceTool):
    """Enhanced tool for searching CBP CROSS with semantic search and relevance scoring."""
    
    def __init__(self, 
                 cross_api_url: str = "https://rulings.cbp.gov/api/v1",
                 binding_rulings_url: str = "https://rulings.cbp.gov/binding_rulings",
                 api_key: Optional[str] = None,
                 cache_ttl_seconds: int = 86400):
        """
        Initialize enhanced rulings tool.
        
        Args:
            cross_api_url: CBP CROSS API endpoint
            binding_rulings_url: Binding rulings API endpoint
            api_key: Optional API key for authenticated requests
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        # Configure retry logic for external API calls
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.5,
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
        
        self.cross_api_url = cross_api_url
        self.binding_rulings_url = binding_rulings_url
        self.api_key = api_key
        self.name = "find_rulings"
        self.description = "Search CBP classification rulings with semantic search and relevance scoring"
        
        # Update HTTP client headers for API authentication
        if self.api_key:
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})
        
        # Ruling type priorities (higher = more authoritative)
        self.ruling_priorities = {
            "Binding Ruling": 10,
            "Headquarters Ruling": 9,
            "Port Ruling": 7,
            "Internal Advice": 6,
            "Prospective Ruling": 8,
            "Revocation": 5,
            "Modification": 6
        }
        
        # Relevance scoring weights
        self.relevance_weights = {
            "hts_match": 0.4,        # HTS code exact/partial match
            "description_match": 0.3, # Product description similarity
            "keyword_match": 0.2,     # Keyword presence
            "recency": 0.1           # How recent the ruling is
        }
        
        # Ruling number patterns
        self.ruling_patterns = {
            "ny": re.compile(r"^NY\s*[A-Z]?\d{6}$", re.IGNORECASE),      # NY A123456
            "hq": re.compile(r"^HQ\s*[A-Z]?\d{6}$", re.IGNORECASE),      # HQ H123456
            "w": re.compile(r"^W\d{6}$", re.IGNORECASE),                 # W123456
            "n": re.compile(r"^N\d{6}$", re.IGNORECASE)                  # N123456
        }
    
    def _run_impl(self, hts_code: str = None, keyword: str = None, 
                  ruling_number: str = None, product_description: str = None,
                  date_from: str = None, date_to: str = None, 
                  ruling_type: str = None, lane_id: str = None,
                  include_precedent_analysis: bool = True) -> Dict[str, Any]:
        """
        Search for CBP rulings with enhanced semantic search and relevance scoring.
        
        Args:
            hts_code: HTS code to search for
            keyword: Keyword search in ruling text
            ruling_number: Specific ruling number
            product_description: Product description for semantic matching
            date_from: Start date for ruling search (YYYY-MM-DD)
            date_to: End date for ruling search (YYYY-MM-DD)
            ruling_type: Type of ruling (Binding, Headquarters, etc.)
            lane_id: Optional lane identifier
            include_precedent_analysis: Whether to include precedent analysis
        
        Returns:
            Dict containing comprehensive ruling search results
        """
        logger.info(f"Enhanced rulings search - HTS: {hts_code}, keyword: {keyword}, ruling: {ruling_number}")
        
        if not any([hts_code, keyword, ruling_number, product_description]):
            raise ValueError("Must provide at least one search criterion")
        
        try:
            # Validate ruling number format if provided
            if ruling_number:
                self._validate_ruling_number(ruling_number)
            
            # Query CBP CROSS API
            rulings = self._query_cross_api(
                hts_code, keyword, ruling_number, product_description,
                date_from, date_to, ruling_type
            )
            
            # Calculate relevance scores
            scored_rulings = self._calculate_relevance_scores(
                rulings, hts_code, keyword, product_description
            )
            
            # Sort by relevance score
            scored_rulings.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Perform precedent analysis if requested
            precedent_analysis = None
            if include_precedent_analysis and scored_rulings:
                precedent_analysis = self._analyze_precedents(scored_rulings, hts_code)
            
            # Generate insights and recommendations
            insights = self._generate_ruling_insights(scored_rulings, precedent_analysis)
            
            return {
                "total_rulings": len(scored_rulings),
                "rulings": scored_rulings,
                "precedent_analysis": precedent_analysis,
                "insights": insights,
                "search_criteria": {
                    "hts_code": hts_code,
                    "keyword": keyword,
                    "ruling_number": ruling_number,
                    "product_description": product_description,
                    "date_from": date_from,
                    "date_to": date_to,
                    "ruling_type": ruling_type,
                    "lane_id": lane_id
                },
                "search_date": "2025-01-20T00:00:00Z",
                "data_sources": [
                    {"name": "CBP CROSS", "url": self.cross_api_url, "status": "active"},
                    {"name": "Binding Rulings", "url": self.binding_rulings_url, "status": "active"}
                ]
            }
        
        except ValueError as e:
            logger.error(f"Validation error in rulings search: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying CBP CROSS: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching rulings: {e}")
            raise
    
    def _validate_ruling_number(self, ruling_number: str) -> str:
        """
        Validate and normalize ruling number format.
        
        Args:
            ruling_number: Raw ruling number input
            
        Returns:
            Normalized ruling number
            
        Raises:
            ValueError: If ruling number format is invalid
        """
        if not ruling_number:
            raise ValueError("Ruling number cannot be empty")
        
        # Clean and normalize
        ruling_clean = ruling_number.strip().upper().replace(" ", "")
        
        # Check against known patterns
        for pattern_name, pattern in self.ruling_patterns.items():
            if pattern.match(ruling_clean):
                return ruling_clean
        
        raise ValueError(f"Invalid ruling number format: {ruling_number}. Expected formats: NY123456, HQ123456, W123456, N123456")
    
    def _query_cross_api(self, hts_code: str, keyword: str, ruling_number: str,
                        product_description: str, date_from: str, date_to: str,
                        ruling_type: str) -> List[Dict[str, Any]]:
        """
        Query CBP CROSS API for rulings.
        
        Args:
            hts_code: HTS code filter
            keyword: Keyword filter
            ruling_number: Specific ruling number
            product_description: Product description
            date_from: Start date filter
            date_to: End date filter
            ruling_type: Ruling type filter
            
        Returns:
            List of rulings from API
        """
        try:
            # In production, make actual API call to CBP CROSS
            # params = {
            #     "hts_code": hts_code,
            #     "keyword": keyword,
            #     "ruling_number": ruling_number,
            #     "product_description": product_description,
            #     "date_from": date_from,
            #     "date_to": date_to,
            #     "ruling_type": ruling_type,
            #     "format": "json"
            # }
            # response = self.client.get(f"{self.cross_api_url}/search", params=params)
            # response.raise_for_status()
            # return response.json().get("rulings", [])
            
            # For now, use enhanced mock data
            return self._get_enhanced_mock_rulings(
                hts_code, keyword, ruling_number, product_description,
                date_from, date_to, ruling_type
            )
            
        except httpx.HTTPError as e:
            logger.warning(f"CBP CROSS API error: {e}")
            return []
    
    def _get_enhanced_mock_rulings(self, hts_code: str, keyword: str, ruling_number: str,
                                  product_description: str, date_from: str, date_to: str,
                                  ruling_type: str) -> List[Dict[str, Any]]:
        """Enhanced mock rulings data with comprehensive information."""
        mock_rulings = [
            {
                "ruling_number": "NY N312345",
                "ruling_type": "Binding Ruling",
                "date": "2024-12-15",
                "hts_code": "8517.12.00",
                "product_description": "Cellular telephones with dual SIM capability and GPS functionality",
                "classification_rationale": "The merchandise consists of cellular telephones designed for voice and data transmission. Classification under HTS 8517.12.00 as cellular telephones.",
                "duty_rate": "Free",
                "precedent_value": "high",
                "ruling_text": "The submitted samples are cellular telephones capable of dual SIM operation...",
                "related_rulings": ["NY N298765", "HQ H234567"],
                "port_of_entry": "Los Angeles, CA",
                "importer": "Tech Import Corp",
                "ruling_url": f"{self.cross_api_url}/ruling/NY_N312345",
                "status": "active"
            },
            {
                "ruling_number": "HQ H234567",
                "ruling_type": "Headquarters Ruling",
                "date": "2024-11-20",
                "hts_code": "8708.30.50",
                "product_description": "Brake pads for passenger motor vehicles, ceramic composition",
                "classification_rationale": "The brake pads are specifically designed for passenger vehicles and are classified under HTS 8708.30.50.",
                "duty_rate": "2.5%",
                "precedent_value": "high",
                "ruling_text": "The merchandise consists of brake pads manufactured from ceramic materials...",
                "related_rulings": ["NY N287654", "NY N298123"],
                "port_of_entry": "Detroit, MI",
                "importer": "Auto Parts International",
                "ruling_url": f"{self.cross_api_url}/ruling/HQ_H234567",
                "status": "active"
            },
            {
                "ruling_number": "NY N298765",
                "ruling_type": "Binding Ruling",
                "date": "2024-10-10",
                "hts_code": "8517.12.00",
                "product_description": "Smartphone with 5G capability and wireless charging",
                "classification_rationale": "The device is a smartphone with advanced communication capabilities, properly classified under HTS 8517.12.00.",
                "duty_rate": "Free",
                "precedent_value": "medium",
                "ruling_text": "The submitted merchandise is a smartphone device with 5G wireless communication...",
                "related_rulings": ["NY N312345", "NY N276543"],
                "port_of_entry": "New York, NY",
                "importer": "Mobile Device Imports LLC",
                "ruling_url": f"{self.cross_api_url}/ruling/NY_N298765",
                "status": "active"
            },
            {
                "ruling_number": "NY N287654",
                "ruling_type": "Port Ruling",
                "date": "2024-09-05",
                "hts_code": "8708.30.10",
                "product_description": "Brake drums for commercial vehicles",
                "classification_rationale": "Brake drums designed for commercial vehicles are classified under HTS 8708.30.10.",
                "duty_rate": "2.5%",
                "precedent_value": "medium",
                "ruling_text": "The brake drums are manufactured for use in commercial vehicles...",
                "related_rulings": ["HQ H234567"],
                "port_of_entry": "Long Beach, CA",
                "importer": "Commercial Auto Parts Inc",
                "ruling_url": f"{self.cross_api_url}/ruling/NY_N287654",
                "status": "active"
            },
            {
                "ruling_number": "W123456",
                "ruling_type": "Internal Advice",
                "date": "2024-08-15",
                "hts_code": "6203.42.40",
                "product_description": "Men's cotton trousers with elastic waistband",
                "classification_rationale": "Cotton trousers for men are classified under HTS 6203.42.40 based on material composition and construction.",
                "duty_rate": "16.6%",
                "precedent_value": "low",
                "ruling_text": "The garments are men's trousers constructed of cotton fabric...",
                "related_rulings": [],
                "port_of_entry": "Miami, FL",
                "importer": "Fashion Imports USA",
                "ruling_url": f"{self.cross_api_url}/ruling/W_123456",
                "status": "active"
            }
        ]
        
        return self._filter_rulings_by_criteria(
            mock_rulings, hts_code, keyword, ruling_number, product_description,
            date_from, date_to, ruling_type
        )
    
    def _filter_rulings_by_criteria(self, rulings: List[Dict[str, Any]], hts_code: str,
                                   keyword: str, ruling_number: str, product_description: str,
                                   date_from: str, date_to: str, ruling_type: str) -> List[Dict[str, Any]]:
        """Filter rulings based on search criteria."""
        filtered = []
        
        for ruling in rulings:
            matches = True
            
            # Ruling number exact match
            if ruling_number and ruling["ruling_number"].replace(" ", "") != ruling_number.replace(" ", ""):
                matches = False
            
            # HTS code match (exact or partial)
            if hts_code and not ruling["hts_code"].startswith(hts_code[:6]):
                matches = False
            
            # Keyword search in multiple fields
            if keyword:
                keyword_lower = keyword.lower()
                searchable_text = (
                    ruling["product_description"] + " " +
                    ruling["classification_rationale"] + " " +
                    ruling.get("ruling_text", "")
                ).lower()
                
                if keyword_lower not in searchable_text:
                    matches = False
            
            # Product description similarity
            if product_description:
                similarity = self._calculate_text_similarity(
                    product_description.lower(),
                    ruling["product_description"].lower()
                )
                if similarity < 0.3:  # Minimum similarity threshold
                    matches = False
            
            # Date range filter
            if date_from or date_to:
                ruling_date = datetime.strptime(ruling["date"], "%Y-%m-%d")
                
                if date_from:
                    from_date = datetime.strptime(date_from, "%Y-%m-%d")
                    if ruling_date < from_date:
                        matches = False
                
                if date_to:
                    to_date = datetime.strptime(date_to, "%Y-%m-%d")
                    if ruling_date > to_date:
                        matches = False
            
            # Ruling type filter
            if ruling_type and ruling["ruling_type"] != ruling_type:
                matches = False
            
            if matches:
                filtered.append(ruling)
        
        return filtered
    
    def _calculate_relevance_scores(self, rulings: List[Dict[str, Any]], hts_code: str,
                                   keyword: str, product_description: str) -> List[Dict[str, Any]]:
        """
        Calculate relevance scores for rulings based on search criteria.
        
        Args:
            rulings: List of ruling records
            hts_code: HTS code search criterion
            keyword: Keyword search criterion
            product_description: Product description search criterion
            
        Returns:
            Rulings with relevance scores added
        """
        scored_rulings = []
        
        for ruling in rulings:
            scores = {
                "hts_match": 0.0,
                "description_match": 0.0,
                "keyword_match": 0.0,
                "recency": 0.0
            }
            
            # HTS code matching score
            if hts_code:
                if ruling["hts_code"] == hts_code:
                    scores["hts_match"] = 1.0
                elif ruling["hts_code"].startswith(hts_code[:6]):
                    scores["hts_match"] = 0.8
                elif ruling["hts_code"].startswith(hts_code[:4]):
                    scores["hts_match"] = 0.6
                elif ruling["hts_code"].startswith(hts_code[:2]):
                    scores["hts_match"] = 0.3
            
            # Product description similarity
            if product_description:
                scores["description_match"] = self._calculate_text_similarity(
                    product_description.lower(),
                    ruling["product_description"].lower()
                )
            
            # Keyword matching in ruling text
            if keyword:
                keyword_lower = keyword.lower()
                searchable_text = (
                    ruling["product_description"] + " " +
                    ruling["classification_rationale"] + " " +
                    ruling.get("ruling_text", "")
                ).lower()
                
                # Count keyword occurrences
                keyword_count = searchable_text.count(keyword_lower)
                scores["keyword_match"] = min(keyword_count * 0.2, 1.0)
            
            # Recency score (more recent = higher score)
            ruling_date = datetime.strptime(ruling["date"], "%Y-%m-%d")
            days_old = (datetime.now() - ruling_date).days
            scores["recency"] = max(1.0 - (days_old / 365), 0.0)  # Decay over 1 year
            
            # Calculate weighted overall relevance score
            relevance_score = sum(
                scores[factor] * weight
                for factor, weight in self.relevance_weights.items()
            )
            
            # Add priority bonus based on ruling type
            priority_bonus = self.ruling_priorities.get(ruling["ruling_type"], 5) / 10 * 0.1
            relevance_score += priority_bonus
            
            # Ensure score is between 0 and 1
            relevance_score = min(max(relevance_score, 0.0), 1.0)
            
            # Add scores to ruling
            ruling_with_score = ruling.copy()
            ruling_with_score["relevance_score"] = round(relevance_score, 3)
            ruling_with_score["score_breakdown"] = {k: round(v, 3) for k, v in scores.items()}
            ruling_with_score["priority_bonus"] = round(priority_bonus, 3)
            
            scored_rulings.append(ruling_with_score)
        
        return scored_rulings
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for basic similarity
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _analyze_precedents(self, rulings: List[Dict[str, Any]], hts_code: str) -> Dict[str, Any]:
        """
        Analyze precedent value and consistency of rulings.
        
        Args:
            rulings: List of scored rulings
            hts_code: HTS code being analyzed
            
        Returns:
            Precedent analysis results
        """
        if not rulings:
            return {"analysis": "No rulings available for precedent analysis"}
        
        # Group rulings by HTS code
        hts_groups = defaultdict(list)
        for ruling in rulings:
            hts_groups[ruling["hts_code"]].append(ruling)
        
        # Analyze consistency within HTS codes
        consistency_analysis = {}
        for hts, hts_rulings in hts_groups.items():
            if len(hts_rulings) > 1:
                # Check for consistent classification rationale
                rationales = [r["classification_rationale"] for r in hts_rulings]
                consistency_score = self._calculate_consistency_score(rationales)
                
                # Check for consistent duty rates
                duty_rates = [r["duty_rate"] for r in hts_rulings]
                duty_consistency = len(set(duty_rates)) == 1
                
                consistency_analysis[hts] = {
                    "ruling_count": len(hts_rulings),
                    "consistency_score": consistency_score,
                    "duty_rate_consistent": duty_consistency,
                    "duty_rates": list(set(duty_rates)),
                    "precedent_strength": self._assess_precedent_strength(hts_rulings)
                }
        
        # Identify most authoritative rulings
        authoritative_rulings = [
            r for r in rulings 
            if r["ruling_type"] in ["Binding Ruling", "Headquarters Ruling"] and
            r["precedent_value"] in ["high", "medium"]
        ]
        
        # Find related rulings and citation patterns
        citation_network = self._analyze_citation_network(rulings)
        
        return {
            "total_rulings_analyzed": len(rulings),
            "hts_codes_covered": list(hts_groups.keys()),
            "consistency_analysis": consistency_analysis,
            "authoritative_rulings": len(authoritative_rulings),
            "most_authoritative": authoritative_rulings[:3] if authoritative_rulings else [],
            "citation_network": citation_network,
            "precedent_recommendations": self._generate_precedent_recommendations(
                consistency_analysis, authoritative_rulings
            )
        }
    
    def _calculate_consistency_score(self, rationales: List[str]) -> float:
        """Calculate consistency score for classification rationales."""
        if len(rationales) < 2:
            return 1.0
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(rationales)):
            for j in range(i + 1, len(rationales)):
                similarity = self._calculate_text_similarity(rationales[i], rationales[j])
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _assess_precedent_strength(self, rulings: List[Dict[str, Any]]) -> str:
        """Assess the precedent strength of a group of rulings."""
        if not rulings:
            return "none"
        
        # Count high-authority rulings
        high_authority = sum(1 for r in rulings if r["ruling_type"] in ["Binding Ruling", "Headquarters Ruling"])
        total_rulings = len(rulings)
        
        # Check recency
        most_recent = max(rulings, key=lambda x: x["date"])
        days_old = (datetime.now() - datetime.strptime(most_recent["date"], "%Y-%m-%d")).days
        
        if high_authority >= 2 and days_old < 365:
            return "strong"
        elif high_authority >= 1 and days_old < 730:
            return "moderate"
        elif total_rulings >= 3:
            return "weak"
        else:
            return "minimal"
    
    def _analyze_citation_network(self, rulings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze citation patterns between rulings."""
        citation_map = {}
        cited_rulings = set()
        
        for ruling in rulings:
            ruling_num = ruling["ruling_number"]
            related = ruling.get("related_rulings", [])
            
            citation_map[ruling_num] = related
            cited_rulings.update(related)
        
        # Find most cited rulings
        citation_counts = defaultdict(int)
        for related_list in citation_map.values():
            for cited in related_list:
                citation_counts[cited] += 1
        
        most_cited = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_citations": sum(citation_counts.values()),
            "most_cited_rulings": [{"ruling": ruling, "citations": count} for ruling, count in most_cited],
            "citation_density": len(cited_rulings) / len(rulings) if rulings else 0,
            "interconnected_rulings": len(cited_rulings)
        }
    
    def _generate_precedent_recommendations(self, consistency_analysis: Dict[str, Any],
                                          authoritative_rulings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on precedent analysis."""
        recommendations = []
        
        if not consistency_analysis:
            recommendations.append("Insufficient rulings for precedent analysis")
            return recommendations
        
        # Check for strong precedents
        strong_precedents = [
            hts for hts, analysis in consistency_analysis.items()
            if analysis["precedent_strength"] == "strong"
        ]
        
        if strong_precedents:
            recommendations.append(f"Strong precedents exist for HTS codes: {', '.join(strong_precedents)}")
        
        # Check for inconsistencies
        inconsistent_hts = [
            hts for hts, analysis in consistency_analysis.items()
            if analysis["consistency_score"] < 0.7 or not analysis["duty_rate_consistent"]
        ]
        
        if inconsistent_hts:
            recommendations.append(f"Inconsistent rulings found for HTS codes: {', '.join(inconsistent_hts)} - review carefully")
        
        # Recommend most authoritative rulings
        if authoritative_rulings:
            top_ruling = authoritative_rulings[0]
            recommendations.append(f"Most authoritative ruling: {top_ruling['ruling_number']} ({top_ruling['ruling_type']})")
        
        return recommendations
    
    def _generate_ruling_insights(self, rulings: List[Dict[str, Any]], 
                                 precedent_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate insights and recommendations from ruling search results.
        
        Args:
            rulings: List of scored rulings
            precedent_analysis: Precedent analysis results
            
        Returns:
            Insights and recommendations
        """
        insights = {
            "key_findings": [],
            "classification_guidance": [],
            "risk_factors": [],
            "recommendations": []
        }
        
        if not rulings:
            insights["key_findings"].append("No relevant rulings found for search criteria")
            insights["recommendations"].append("Consider broadening search criteria or consulting with customs broker")
            return insights
        
        # Key findings
        total_rulings = len(rulings)
        avg_relevance = sum(r["relevance_score"] for r in rulings) / total_rulings
        
        insights["key_findings"].append(f"Found {total_rulings} relevant rulings with average relevance score of {avg_relevance:.2f}")
        
        # Analyze ruling types
        ruling_types = defaultdict(int)
        for ruling in rulings:
            ruling_types[ruling["ruling_type"]] += 1
        
        most_common_type = max(ruling_types, key=ruling_types.get)
        insights["key_findings"].append(f"Most common ruling type: {most_common_type} ({ruling_types[most_common_type]} rulings)")
        
        # Classification guidance
        if rulings:
            top_ruling = rulings[0]  # Highest relevance score
            insights["classification_guidance"].append(
                f"Top precedent: {top_ruling['ruling_number']} classifies similar products under HTS {top_ruling['hts_code']}"
            )
            insights["classification_guidance"].append(f"Duty rate: {top_ruling['duty_rate']}")
            
            # Check for consistent classification across top rulings
            top_3_hts = [r["hts_code"] for r in rulings[:3]]
            if len(set(top_3_hts)) == 1:
                insights["classification_guidance"].append("Consistent classification across top precedents")
            else:
                insights["classification_guidance"].append("Mixed classifications in top precedents - careful analysis needed")
        
        # Risk factors
        if precedent_analysis:
            inconsistent_hts = [
                hts for hts, analysis in precedent_analysis.get("consistency_analysis", {}).items()
                if analysis["consistency_score"] < 0.7
            ]
            
            if inconsistent_hts:
                insights["risk_factors"].append("Inconsistent precedents may lead to classification disputes")
        
        # Check for old rulings
        old_rulings = [
            r for r in rulings
            if (datetime.now() - datetime.strptime(r["date"], "%Y-%m-%d")).days > 1095  # 3 years
        ]
        
        if old_rulings:
            insights["risk_factors"].append(f"{len(old_rulings)} rulings are over 3 years old - verify current applicability")
        
        # Recommendations
        if rulings[0]["relevance_score"] > 0.8:
            insights["recommendations"].append("High-confidence classification precedent found")
        elif rulings[0]["relevance_score"] > 0.6:
            insights["recommendations"].append("Good precedent found - verify product details match ruling")
        else:
            insights["recommendations"].append("Weak precedents - consider requesting binding ruling")
        
        # Binding ruling recommendations
        binding_rulings = [r for r in rulings if r["ruling_type"] == "Binding Ruling"]
        if not binding_rulings and total_rulings < 3:
            insights["recommendations"].append("Consider requesting binding ruling for classification certainty")
        
        return insights
    
    def get_binding_ruling_status(self, ruling_number: str) -> Dict[str, Any]:
        """
        Check the status of a binding ruling request.
        
        Args:
            ruling_number: Binding ruling number to check
            
        Returns:
            Status information for the binding ruling
        """
        logger.info(f"Checking binding ruling status: {ruling_number}")
        
        try:
            # Validate ruling number
            normalized_number = self._validate_ruling_number(ruling_number)
            
            # In production, query actual CBP binding ruling status API
            # response = self.client.get(f"{self.binding_rulings_url}/status/{normalized_number}")
            # response.raise_for_status()
            # return response.json()
            
            # Mock status data
            return self._get_mock_binding_ruling_status(normalized_number)
            
        except ValueError as e:
            logger.error(f"Invalid ruling number: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Error checking binding ruling status: {e}")
            raise
    
    def _get_mock_binding_ruling_status(self, ruling_number: str) -> Dict[str, Any]:
        """Mock binding ruling status data."""
        # Mock status based on ruling number pattern
        if ruling_number.startswith("NY"):
            status = "issued"
            issue_date = "2024-12-15"
            processing_time = 45
        elif ruling_number.startswith("HQ"):
            status = "under_review"
            issue_date = None
            processing_time = None
        else:
            status = "pending"
            issue_date = None
            processing_time = None
        
        return {
            "ruling_number": ruling_number,
            "status": status,
            "submission_date": "2024-11-01",
            "issue_date": issue_date,
            "processing_time_days": processing_time,
            "estimated_completion": "2025-02-15" if status == "under_review" else None,
            "status_description": {
                "issued": "Binding ruling has been issued and is available",
                "under_review": "Ruling is currently under review by CBP",
                "pending": "Ruling request is pending initial review"
            }.get(status, "Unknown status"),
            "next_steps": {
                "issued": "Ruling is available for use in import transactions",
                "under_review": "No action required - await CBP decision",
                "pending": "Ensure all required documentation has been submitted"
            }.get(status, "Contact CBP for status update")
        }
    
    def validate_response_schema(self, data: Dict[str, Any]) -> bool:
        """Validate enhanced rulings response schema."""
        required_fields = [
            "total_rulings", "rulings", "search_criteria", "data_sources"
        ]
        
        # Check required fields
        if not all(field in data for field in required_fields):
            return False
        
        # Validate rulings structure
        rulings = data.get("rulings", [])
        if rulings:
            required_ruling_fields = [
                "ruling_number", "ruling_type", "date", "hts_code",
                "product_description", "relevance_score"
            ]
            
            for ruling in rulings:
                if not all(field in ruling for field in required_ruling_fields):
                    return False
        
        # Validate precedent_analysis if present
        if "precedent_analysis" in data and data["precedent_analysis"]:
            precedent = data["precedent_analysis"]
            if not isinstance(precedent, dict):
                return False
        
        return True
