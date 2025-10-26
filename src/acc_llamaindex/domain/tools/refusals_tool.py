"""Enhanced FDA/FSIS import refusals tool with trend analysis and risk scoring."""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from loguru import logger

import httpx
from .base_tool import ComplianceTool, RetryConfig


class RefusalsTool(ComplianceTool):
    """Enhanced tool for querying FDA, FSIS, and APHIS import refusal data with trend analysis."""
    
    def __init__(self, 
                 fda_api_url: str = "https://api.fda.gov/food/enforcement.json",
                 fsis_api_url: str = "https://www.fsis.usda.gov/sites/default/files/media/file/2021-07/Import_Refusal_Report.json",
                 aphis_api_url: str = "https://www.aphis.usda.gov/aphis/ourfocus/planthealth/import-information/sa_import/sa_import_refusals",
                 api_key: Optional[str] = None,
                 cache_ttl_seconds: int = 86400):
        """
        Initialize enhanced refusals tool.
        
        Args:
            fda_api_url: FDA API endpoint for refusal data
            fsis_api_url: FSIS API endpoint for refusal data
            aphis_api_url: APHIS API endpoint for refusal data
            api_key: Optional API key for authenticated requests
            cache_ttl_seconds: Cache TTL (default: 24 hours)
        """
        # Configure retry logic for external API calls
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=20.0,
            exponential_backoff=True,
            jitter=True
        )
        
        # Configure circuit breaker for API failures
        circuit_breaker_config = {
            "failure_threshold": 5,
            "recovery_timeout": 600,  # 10 minutes
        }
        
        super().__init__(
            cache_ttl_seconds=cache_ttl_seconds,
            retry_config=retry_config,
            circuit_breaker_config=circuit_breaker_config
        )
        
        self.fda_api_url = fda_api_url
        self.fsis_api_url = fsis_api_url
        self.aphis_api_url = aphis_api_url
        self.api_key = api_key
        self.name = "fetch_refusals"
        self.description = "Fetch and analyze FDA, FSIS, and APHIS import refusal data with trend analysis"
        
        # Update HTTP client headers for API authentication
        if self.api_key:
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})
        
        # Risk scoring weights
        self.risk_weights = {
            "frequency": 0.4,      # How often refusals occur
            "severity": 0.3,       # Severity of refusal reasons
            "recency": 0.2,        # How recent the refusals are
            "trend": 0.1          # Whether refusals are increasing
        }
        
        # Refusal reason severity mapping
        self.severity_mapping = {
            # High severity (health/safety risks)
            "salmonella": 10,
            "listeria": 10,
            "e. coli": 10,
            "botulism": 10,
            "pesticide": 9,
            "drug residue": 9,
            "heavy metals": 9,
            "aflatoxin": 9,
            
            # Medium severity (quality/regulatory issues)
            "filth": 7,
            "decomposition": 7,
            "adulteration": 7,
            "misbranding": 6,
            "lack of process filing": 6,
            "lack of registration": 6,
            
            # Lower severity (documentation/procedural)
            "lack of documentation": 4,
            "improper labeling": 4,
            "facility not registered": 3,
            "administrative": 2
        }
        
        # Agency-specific configurations
        self.agency_configs = {
            "FDA": {
                "name": "Food and Drug Administration",
                "jurisdiction": ["food", "drugs", "medical devices", "cosmetics"],
                "api_rate_limit": 1000  # requests per hour
            },
            "FSIS": {
                "name": "Food Safety and Inspection Service",
                "jurisdiction": ["meat", "poultry", "egg products"],
                "api_rate_limit": 500
            },
            "APHIS": {
                "name": "Animal and Plant Health Inspection Service",
                "jurisdiction": ["plants", "animals", "agricultural products"],
                "api_rate_limit": 300
            }
        }
    
    def _run_impl(self, hts_code: str = None, product_keyword: str = None, 
                  country: str = None, lane_id: str = None, days: int = 90,
                  include_trend_analysis: bool = True) -> Dict[str, Any]:
        """
        Query import refusals with enhanced analysis and risk scoring.
        
        Args:
            hts_code: HTS code to filter by
            product_keyword: Product description keyword
            country: Country of origin (ISO 2-letter code)
            lane_id: Optional lane identifier
            days: Number of days to look back (default: 90)
            include_trend_analysis: Whether to include trend analysis
        
        Returns:
            Dict containing comprehensive refusal data and analysis
        """
        logger.info(f"Enhanced refusals query - HTS: {hts_code}, keyword: {product_keyword}, country: {country}")
        
        if not any([hts_code, product_keyword, country]):
            raise ValueError("Must provide at least one search criterion")
        
        try:
            # Query multiple agencies
            fda_refusals = self._query_fda_api(hts_code, product_keyword, country, days)
            fsis_refusals = self._query_fsis_api(hts_code, product_keyword, country, days)
            aphis_refusals = self._query_aphis_api(hts_code, product_keyword, country, days)
            
            # Combine all refusals
            all_refusals = fda_refusals + fsis_refusals + aphis_refusals
            
            # Calculate risk score
            risk_analysis = self._calculate_risk_score(all_refusals, country, product_keyword)
            
            # Perform trend analysis if requested
            trend_analysis = None
            if include_trend_analysis and all_refusals:
                trend_analysis = self._analyze_trends(all_refusals, days)
            
            # Generate insights and recommendations
            insights = self._generate_insights(all_refusals, risk_analysis, trend_analysis)
            
            return {
                "total_refusals": len(all_refusals),
                "refusals_by_agency": {
                    "FDA": len(fda_refusals),
                    "FSIS": len(fsis_refusals),
                    "APHIS": len(aphis_refusals)
                },
                "refusals": all_refusals,
                "risk_analysis": risk_analysis,
                "trend_analysis": trend_analysis,
                "insights": insights,
                "search_criteria": {
                    "hts_code": hts_code,
                    "product_keyword": product_keyword,
                    "country": country,
                    "days": days,
                    "lane_id": lane_id
                },
                "query_date": "2025-01-20T00:00:00Z",
                "data_sources": [
                    {"agency": "FDA", "url": self.fda_api_url, "status": "active"},
                    {"agency": "FSIS", "url": self.fsis_api_url, "status": "active"},
                    {"agency": "APHIS", "url": self.aphis_api_url, "status": "active"}
                ]
            }
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying refusals APIs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error querying refusals: {e}")
            raise
    
    def _query_fda_api(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Query FDA API for refusal data.
        
        Args:
            hts_code: HTS code filter
            keyword: Product keyword filter
            country: Country filter
            days: Days to look back
            
        Returns:
            List of FDA refusals
        """
        try:
            # In production, make actual API call to FDA
            # params = {
            #     "search": f"product_description:{keyword}" if keyword else "",
            #     "count": 100,
            #     "skip": 0
            # }
            # response = self.client.get(self.fda_api_url, params=params)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_enhanced_mock_fda_refusals(hts_code, keyword, country, days)
            
        except httpx.HTTPError as e:
            logger.warning(f"FDA API error: {e}")
            return []
    
    def _query_fsis_api(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Query FSIS API for refusal data.
        
        Args:
            hts_code: HTS code filter
            keyword: Product keyword filter
            country: Country filter
            days: Days to look back
            
        Returns:
            List of FSIS refusals
        """
        try:
            # In production, make actual API call to FSIS
            # response = self.client.get(self.fsis_api_url)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_enhanced_mock_fsis_refusals(hts_code, keyword, country, days)
            
        except httpx.HTTPError as e:
            logger.warning(f"FSIS API error: {e}")
            return []
    
    def _query_aphis_api(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Query APHIS API for refusal data.
        
        Args:
            hts_code: HTS code filter
            keyword: Product keyword filter
            country: Country filter
            days: Days to look back
            
        Returns:
            List of APHIS refusals
        """
        try:
            # In production, make actual API call to APHIS
            # response = self.client.get(self.aphis_api_url)
            # response.raise_for_status()
            # api_data = response.json()
            
            # For now, use enhanced mock data
            return self._get_enhanced_mock_aphis_refusals(hts_code, keyword, country, days)
            
        except httpx.HTTPError as e:
            logger.warning(f"APHIS API error: {e}")
            return []
    
    def _get_enhanced_mock_fda_refusals(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """Enhanced mock FDA refusal data with realistic patterns."""
        mock_refusals = [
            {
                "agency": "FDA",
                "date": "2025-01-10",
                "product": "Frozen shrimp and prawns",
                "country": "CN",
                "refusal_reason": "Salmonella",
                "hts_code": "0306.17.00",
                "firm_name": "Seafood Processing Co Ltd",
                "port_of_entry": "Los Angeles, CA",
                "fda_sample_analysis": "Positive for Salmonella spp.",
                "disposition": "Refused Entry",
                "severity_score": 10,
                "product_code": "16A"
            },
            {
                "agency": "FDA",
                "date": "2024-12-20",
                "product": "Dried shiitake mushrooms",
                "country": "CN",
                "refusal_reason": "Pesticide residue",
                "hts_code": "0712.39.00",
                "firm_name": "Mountain Harvest Foods",
                "port_of_entry": "Seattle, WA",
                "fda_sample_analysis": "Pesticide residue exceeds established tolerance",
                "disposition": "Refused Entry",
                "severity_score": 9,
                "product_code": "16B"
            },
            {
                "agency": "FDA",
                "date": "2024-12-15",
                "product": "Canned fish products",
                "country": "TH",
                "refusal_reason": "Filth",
                "hts_code": "1604.14.00",
                "firm_name": "Thai Ocean Products",
                "port_of_entry": "Long Beach, CA",
                "fda_sample_analysis": "Contains filthy, putrid, or decomposed substance",
                "disposition": "Refused Entry",
                "severity_score": 7,
                "product_code": "16C"
            },
            {
                "agency": "FDA",
                "date": "2024-11-30",
                "product": "Spices and seasonings",
                "country": "IN",
                "refusal_reason": "Aflatoxin",
                "hts_code": "0910.30.00",
                "firm_name": "Spice Traders International",
                "port_of_entry": "New York, NY",
                "fda_sample_analysis": "Aflatoxin levels exceed FDA action levels",
                "disposition": "Refused Entry",
                "severity_score": 9,
                "product_code": "16D"
            }
        ]
        
        return self._filter_refusals_by_criteria(mock_refusals, hts_code, keyword, country, days)
    
    def _get_enhanced_mock_fsis_refusals(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """Enhanced mock FSIS refusal data with realistic patterns."""
        mock_refusals = [
            {
                "agency": "FSIS",
                "date": "2025-01-05",
                "product": "Fresh beef, boneless",
                "country": "BR",
                "refusal_reason": "Lack of equivalency documentation",
                "hts_code": "0201.30.02",
                "firm_name": "Brazilian Beef Exporters SA",
                "port_of_entry": "Miami, FL",
                "fsis_note": "Establishment not on eligible establishments list",
                "disposition": "Entry Refused",
                "severity_score": 6,
                "establishment_number": "BR2345"
            },
            {
                "agency": "FSIS",
                "date": "2024-12-28",
                "product": "Frozen chicken parts",
                "country": "CN",
                "refusal_reason": "Lack of health certificate",
                "hts_code": "0207.14.00",
                "firm_name": "China Poultry Processing",
                "port_of_entry": "Los Angeles, CA",
                "fsis_note": "Missing required health certificate from competent authority",
                "disposition": "Entry Refused",
                "severity_score": 4,
                "establishment_number": "CN8901"
            }
        ]
        
        return self._filter_refusals_by_criteria(mock_refusals, hts_code, keyword, country, days)
    
    def _get_enhanced_mock_aphis_refusals(self, hts_code: str, keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """Enhanced mock APHIS refusal data with realistic patterns."""
        mock_refusals = [
            {
                "agency": "APHIS",
                "date": "2024-12-18",
                "product": "Fresh citrus fruits",
                "country": "MX",
                "refusal_reason": "Pest interception",
                "hts_code": "0805.10.00",
                "firm_name": "Mexican Citrus Growers",
                "port_of_entry": "Laredo, TX",
                "aphis_note": "Mediterranean fruit fly larvae detected",
                "disposition": "Entry Refused",
                "severity_score": 8,
                "permit_number": "P526-24-00123"
            },
            {
                "agency": "APHIS",
                "date": "2024-11-25",
                "product": "Cut flowers and foliage",
                "country": "CO",
                "refusal_reason": "Phytosanitary certificate issues",
                "hts_code": "0603.19.00",
                "firm_name": "Colombian Flower Exports",
                "port_of_entry": "Miami, FL",
                "aphis_note": "Phytosanitary certificate not properly endorsed",
                "disposition": "Entry Refused",
                "severity_score": 3,
                "permit_number": "P526-24-00456"
            }
        ]
        
        return self._filter_refusals_by_criteria(mock_refusals, hts_code, keyword, country, days)
    
    def _filter_refusals_by_criteria(self, refusals: List[Dict[str, Any]], hts_code: str, 
                                   keyword: str, country: str, days: int) -> List[Dict[str, Any]]:
        """
        Filter refusals based on search criteria.
        
        Args:
            refusals: List of refusal records
            hts_code: HTS code filter
            keyword: Product keyword filter
            country: Country filter
            days: Days to look back
            
        Returns:
            Filtered refusals
        """
        filtered = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for refusal in refusals:
            matches = True
            
            # Date filter
            refusal_date = datetime.strptime(refusal["date"], "%Y-%m-%d")
            if refusal_date < cutoff_date:
                matches = False
            
            # HTS code filter
            if hts_code and not refusal["hts_code"].startswith(hts_code[:6]):
                matches = False
            
            # Keyword filter
            if keyword and keyword.lower() not in refusal["product"].lower():
                matches = False
            
            # Country filter
            if country and refusal["country"] != country:
                matches = False
            
            if matches:
                filtered.append(refusal)
        
        return filtered
    
    def _calculate_risk_score(self, refusals: List[Dict[str, Any]], country: str, product: str) -> Dict[str, Any]:
        """
        Calculate risk score based on refusal patterns.
        
        Args:
            refusals: List of refusal records
            country: Country being analyzed
            product: Product being analyzed
            
        Returns:
            Risk analysis with score and factors
        """
        if not refusals:
            return {
                "risk_level": "low",
                "risk_score": 0,
                "factors": {
                    "frequency": 0,
                    "severity": 0,
                    "recency": 0,
                    "trend": 0
                },
                "description": "No refusals found for specified criteria"
            }
        
        # Calculate frequency score (0-100)
        frequency_score = min(len(refusals) * 10, 100)
        
        # Calculate severity score (0-100)
        severity_scores = []
        for refusal in refusals:
            reason = refusal.get("refusal_reason", "").lower()
            severity = 5  # default
            for key, value in self.severity_mapping.items():
                if key in reason:
                    severity = value
                    break
            severity_scores.append(severity)
        
        avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 5
        severity_score = (avg_severity / 10) * 100
        
        # Calculate recency score (0-100)
        most_recent = max(refusals, key=lambda x: x["date"])
        days_since_recent = (datetime.now() - datetime.strptime(most_recent["date"], "%Y-%m-%d")).days
        recency_score = max(100 - (days_since_recent * 2), 0)
        
        # Calculate trend score (0-100)
        trend_score = self._calculate_trend_score(refusals)
        
        # Calculate weighted overall score
        overall_score = (
            frequency_score * self.risk_weights["frequency"] +
            severity_score * self.risk_weights["severity"] +
            recency_score * self.risk_weights["recency"] +
            trend_score * self.risk_weights["trend"]
        )
        
        # Determine risk level
        if overall_score >= 80:
            risk_level = "critical"
        elif overall_score >= 60:
            risk_level = "high"
        elif overall_score >= 40:
            risk_level = "medium"
        elif overall_score >= 20:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "risk_level": risk_level,
            "risk_score": round(overall_score, 1),
            "factors": {
                "frequency": round(frequency_score, 1),
                "severity": round(severity_score, 1),
                "recency": round(recency_score, 1),
                "trend": round(trend_score, 1)
            },
            "total_refusals": len(refusals),
            "avg_severity": round(avg_severity, 1),
            "days_since_recent": days_since_recent,
            "description": self._get_risk_description(risk_level, overall_score)
        }
    
    def _calculate_trend_score(self, refusals: List[Dict[str, Any]]) -> float:
        """
        Calculate trend score based on refusal patterns over time.
        
        Args:
            refusals: List of refusal records
            
        Returns:
            Trend score (0-100)
        """
        if len(refusals) < 2:
            return 50  # neutral trend
        
        # Group refusals by month
        monthly_counts = defaultdict(int)
        for refusal in refusals:
            date = datetime.strptime(refusal["date"], "%Y-%m-%d")
            month_key = f"{date.year}-{date.month:02d}"
            monthly_counts[month_key] += 1
        
        # Calculate trend
        months = sorted(monthly_counts.keys())
        if len(months) < 2:
            return 50
        
        counts = [monthly_counts[month] for month in months]
        
        # Simple linear trend calculation
        n = len(counts)
        x_sum = sum(range(n))
        y_sum = sum(counts)
        xy_sum = sum(i * counts[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        if n * x2_sum - x_sum * x_sum == 0:
            return 50
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        # Convert slope to score (0-100)
        if slope > 0:
            return min(50 + (slope * 25), 100)  # increasing trend
        else:
            return max(50 + (slope * 25), 0)    # decreasing trend
    
    def _analyze_trends(self, refusals: List[Dict[str, Any]], days: int) -> Dict[str, Any]:
        """
        Perform comprehensive trend analysis on refusals.
        
        Args:
            refusals: List of refusal records
            days: Analysis period in days
            
        Returns:
            Trend analysis results
        """
        if not refusals:
            return {"trend": "no_data", "analysis": "No refusals to analyze"}
        
        # Analyze by reason
        reason_counts = Counter(refusal["refusal_reason"] for refusal in refusals)
        top_reasons = reason_counts.most_common(5)
        
        # Analyze by country
        country_counts = Counter(refusal["country"] for refusal in refusals)
        top_countries = country_counts.most_common(5)
        
        # Analyze by agency
        agency_counts = Counter(refusal["agency"] for refusal in refusals)
        
        # Analyze by product
        product_counts = Counter(refusal["product"] for refusal in refusals)
        top_products = product_counts.most_common(5)
        
        # Time-based analysis
        monthly_trend = self._get_monthly_trend(refusals)
        
        return {
            "analysis_period_days": days,
            "total_refusals": len(refusals),
            "top_refusal_reasons": [{"reason": reason, "count": count} for reason, count in top_reasons],
            "top_countries": [{"country": country, "count": count} for country, count in top_countries],
            "agency_breakdown": dict(agency_counts),
            "top_products": [{"product": product, "count": count} for product, count in top_products],
            "monthly_trend": monthly_trend,
            "trend_direction": self._determine_trend_direction(monthly_trend)
        }
    
    def _get_monthly_trend(self, refusals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get monthly refusal counts for trend analysis."""
        monthly_counts = defaultdict(int)
        for refusal in refusals:
            date = datetime.strptime(refusal["date"], "%Y-%m-%d")
            month_key = f"{date.year}-{date.month:02d}"
            monthly_counts[month_key] += 1
        
        return [{"month": month, "count": count} for month, count in sorted(monthly_counts.items())]
    
    def _determine_trend_direction(self, monthly_trend: List[Dict[str, Any]]) -> str:
        """Determine overall trend direction."""
        if len(monthly_trend) < 2:
            return "insufficient_data"
        
        counts = [item["count"] for item in monthly_trend]
        first_half = counts[:len(counts)//2]
        second_half = counts[len(counts)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_second > avg_first * 1.2:
            return "increasing"
        elif avg_second < avg_first * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_insights(self, refusals: List[Dict[str, Any]], risk_analysis: Dict[str, Any], 
                          trend_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate actionable insights from refusal data.
        
        Args:
            refusals: List of refusal records
            risk_analysis: Risk analysis results
            trend_analysis: Trend analysis results
            
        Returns:
            Insights and recommendations
        """
        insights = {
            "key_findings": [],
            "recommendations": [],
            "risk_factors": [],
            "mitigation_strategies": []
        }
        
        if not refusals:
            insights["key_findings"].append("No refusals found for specified criteria")
            insights["recommendations"].append("Continue monitoring for any changes")
            return insights
        
        # Key findings
        risk_level = risk_analysis["risk_level"]
        total_refusals = len(refusals)
        
        insights["key_findings"].append(f"Found {total_refusals} refusals with {risk_level} risk level")
        
        if trend_analysis:
            trend_direction = trend_analysis.get("trend_direction", "unknown")
            insights["key_findings"].append(f"Refusal trend is {trend_direction}")
            
            if trend_analysis["top_refusal_reasons"]:
                top_reason = trend_analysis["top_refusal_reasons"][0]
                insights["key_findings"].append(f"Most common refusal reason: {top_reason['reason']} ({top_reason['count']} cases)")
        
        # Risk-based recommendations
        if risk_level in ["critical", "high"]:
            insights["recommendations"].extend([
                "Implement enhanced supplier verification procedures",
                "Consider alternative suppliers or countries",
                "Increase pre-shipment testing and quality controls"
            ])
        elif risk_level == "medium":
            insights["recommendations"].extend([
                "Monitor supplier performance closely",
                "Implement additional quality assurance measures",
                "Consider supplier audits"
            ])
        else:
            insights["recommendations"].append("Continue standard monitoring procedures")
        
        # Risk factors
        if risk_analysis["factors"]["severity"] > 70:
            insights["risk_factors"].append("High severity refusal reasons (health/safety risks)")
        
        if risk_analysis["factors"]["frequency"] > 60:
            insights["risk_factors"].append("High frequency of refusals")
        
        if risk_analysis["factors"]["recency"] > 80:
            insights["risk_factors"].append("Recent refusals indicate ongoing issues")
        
        # Mitigation strategies
        if trend_analysis and trend_analysis["top_refusal_reasons"]:
            top_reason = trend_analysis["top_refusal_reasons"][0]["reason"].lower()
            
            if "salmonella" in top_reason or "listeria" in top_reason:
                insights["mitigation_strategies"].append("Implement HACCP controls and pathogen testing")
            elif "pesticide" in top_reason:
                insights["mitigation_strategies"].append("Verify supplier pesticide use and residue testing")
            elif "documentation" in top_reason:
                insights["mitigation_strategies"].append("Improve documentation and certification processes")
            elif "registration" in top_reason:
                insights["mitigation_strategies"].append("Ensure all facilities are properly registered")
        
        return insights
    
    def _get_risk_description(self, risk_level: str, score: float) -> str:
        """Get descriptive text for risk level."""
        descriptions = {
            "critical": f"Critical risk (score: {score:.1f}) - Immediate action required",
            "high": f"High risk (score: {score:.1f}) - Enhanced controls needed",
            "medium": f"Medium risk (score: {score:.1f}) - Increased monitoring recommended",
            "low": f"Low risk (score: {score:.1f}) - Standard monitoring sufficient",
            "minimal": f"Minimal risk (score: {score:.1f}) - Continue routine monitoring"
        }
        return descriptions.get(risk_level, f"Risk level: {risk_level} (score: {score:.1f})")
    
    def get_refusal_trends(self, country: str, days: int = 180, product_category: str = None) -> Dict[str, Any]:
        """
        Get comprehensive refusal trends for a country over time.
        
        Args:
            country: Country code (e.g., "CN", "MX")
            days: Number of days to analyze (default: 180)
            product_category: Optional product category filter
        
        Returns:
            Dict with comprehensive trend analysis
        """
        logger.info(f"Analyzing refusal trends for {country} over {days} days")
        
        if not country or len(country) != 2:
            raise ValueError("Country must be a valid 2-letter ISO code")
        
        try:
            # Query all agencies for the country
            all_refusals = []
            all_refusals.extend(self._query_fda_api(None, product_category, country, days))
            all_refusals.extend(self._query_fsis_api(None, product_category, country, days))
            all_refusals.extend(self._query_aphis_api(None, product_category, country, days))
            
            if not all_refusals:
                return {
                    "country": country,
                    "period_days": days,
                    "product_category": product_category,
                    "total_refusals": 0,
                    "trend_direction": "no_data",
                    "message": "No refusals found for specified criteria"
                }
            
            # Perform comprehensive trend analysis
            trend_analysis = self._analyze_trends(all_refusals, days)
            risk_analysis = self._calculate_risk_score(all_refusals, country, product_category)
            
            # Calculate month-over-month changes
            monthly_changes = self._calculate_monthly_changes(trend_analysis["monthly_trend"])
            
            # Identify seasonal patterns
            seasonal_patterns = self._identify_seasonal_patterns(all_refusals)
            
            return {
                "country": country,
                "period_days": days,
                "product_category": product_category,
                "total_refusals": len(all_refusals),
                "trend_direction": trend_analysis["trend_direction"],
                "risk_assessment": risk_analysis,
                "top_reasons": trend_analysis["top_refusal_reasons"],
                "top_products": trend_analysis["top_products"],
                "agency_breakdown": trend_analysis["agency_breakdown"],
                "monthly_trend": trend_analysis["monthly_trend"],
                "monthly_changes": monthly_changes,
                "seasonal_patterns": seasonal_patterns,
                "analysis_date": "2025-01-20T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trends for {country}: {e}")
            raise
    
    def _calculate_monthly_changes(self, monthly_trend: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate month-over-month percentage changes."""
        if len(monthly_trend) < 2:
            return []
        
        changes = []
        for i in range(1, len(monthly_trend)):
            current = monthly_trend[i]["count"]
            previous = monthly_trend[i-1]["count"]
            
            if previous == 0:
                change_pct = 100 if current > 0 else 0
            else:
                change_pct = ((current - previous) / previous) * 100
            
            changes.append({
                "month": monthly_trend[i]["month"],
                "count": current,
                "previous_count": previous,
                "change_percent": round(change_pct, 1)
            })
        
        return changes
    
    def _identify_seasonal_patterns(self, refusals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify seasonal patterns in refusals."""
        monthly_counts = defaultdict(int)
        
        for refusal in refusals:
            date = datetime.strptime(refusal["date"], "%Y-%m-%d")
            month = date.month
            monthly_counts[month] += 1
        
        # Calculate average by season
        seasons = {
            "Spring": [3, 4, 5],
            "Summer": [6, 7, 8],
            "Fall": [9, 10, 11],
            "Winter": [12, 1, 2]
        }
        
        seasonal_averages = {}
        for season, months in seasons.items():
            total = sum(monthly_counts[month] for month in months)
            seasonal_averages[season] = round(total / len(months), 1)
        
        # Find peak season
        peak_season = max(seasonal_averages, key=seasonal_averages.get)
        
        return {
            "seasonal_averages": seasonal_averages,
            "peak_season": peak_season,
            "peak_season_avg": seasonal_averages[peak_season],
            "has_seasonal_pattern": max(seasonal_averages.values()) > min(seasonal_averages.values()) * 1.5
        }
    
    def get_agency_comparison(self, country: str = None, days: int = 90) -> Dict[str, Any]:
        """
        Compare refusal patterns across different agencies.
        
        Args:
            country: Optional country filter
            days: Analysis period
            
        Returns:
            Agency comparison analysis
        """
        logger.info(f"Comparing agency refusal patterns for {country or 'all countries'}")
        
        try:
            # Get refusals from all agencies
            fda_refusals = self._query_fda_api(None, None, country, days)
            fsis_refusals = self._query_fsis_api(None, None, country, days)
            aphis_refusals = self._query_aphis_api(None, None, country, days)
            
            agency_data = {
                "FDA": {
                    "refusals": fda_refusals,
                    "count": len(fda_refusals),
                    "jurisdiction": self.agency_configs["FDA"]["jurisdiction"]
                },
                "FSIS": {
                    "refusals": fsis_refusals,
                    "count": len(fsis_refusals),
                    "jurisdiction": self.agency_configs["FSIS"]["jurisdiction"]
                },
                "APHIS": {
                    "refusals": aphis_refusals,
                    "count": len(aphis_refusals),
                    "jurisdiction": self.agency_configs["APHIS"]["jurisdiction"]
                }
            }
            
            # Calculate agency-specific insights
            total_refusals = sum(data["count"] for data in agency_data.values())
            
            for agency, data in agency_data.items():
                if data["count"] > 0:
                    # Calculate percentage of total
                    data["percentage_of_total"] = round((data["count"] / total_refusals) * 100, 1)
                    
                    # Get top refusal reasons for this agency
                    reason_counts = Counter(r["refusal_reason"] for r in data["refusals"])
                    data["top_reasons"] = [{"reason": r, "count": c} for r, c in reason_counts.most_common(3)]
                    
                    # Calculate average severity
                    severities = [self.severity_mapping.get(r["refusal_reason"].lower(), 5) for r in data["refusals"]]
                    data["avg_severity"] = round(sum(severities) / len(severities), 1) if severities else 0
                else:
                    data["percentage_of_total"] = 0
                    data["top_reasons"] = []
                    data["avg_severity"] = 0
            
            return {
                "analysis_period_days": days,
                "country_filter": country,
                "total_refusals": total_refusals,
                "agency_breakdown": agency_data,
                "most_active_agency": max(agency_data.keys(), key=lambda k: agency_data[k]["count"]) if total_refusals > 0 else None,
                "analysis_date": "2025-01-20T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Error in agency comparison: {e}")
            raise
    
    def validate_response_schema(self, data: Dict[str, Any]) -> bool:
        """Validate enhanced refusals response schema."""
        required_fields = [
            "total_refusals", "refusals_by_agency", "risk_analysis", 
            "search_criteria", "data_sources"
        ]
        
        # Check required fields
        if not all(field in data for field in required_fields):
            return False
        
        # Validate risk_analysis structure
        risk_analysis = data.get("risk_analysis", {})
        required_risk_fields = ["risk_level", "risk_score", "factors"]
        if not all(field in risk_analysis for field in required_risk_fields):
            return False
        
        # Validate refusals_by_agency structure
        agency_breakdown = data.get("refusals_by_agency", {})
        expected_agencies = ["FDA", "FSIS", "APHIS"]
        if not all(agency in agency_breakdown for agency in expected_agencies):
            return False
        
        return True
