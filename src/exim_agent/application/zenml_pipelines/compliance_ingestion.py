"""ZenML pipeline for compliance data ingestion."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

from zenml import pipeline, step

from exim_agent.infrastructure.db.compliance_collections import compliance_collections
from exim_agent.infrastructure.db.supabase_client import supabase_client
from exim_agent.domain.tools.hts_tool import HTSTool
from exim_agent.domain.tools.sanctions_tool import SanctionsTool
from exim_agent.domain.tools.refusals_tool import RefusalsTool
from exim_agent.domain.tools.rulings_tool import RulingsTool
from exim_agent.application.crawl_service.service import CrawlService


def _enhance_crawled_metadata(item: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """
    Enhance metadata for crawled content with advanced categorization and attribution.
    
    Args:
        item: Crawled content item
        domain: Compliance domain (hts, rulings, sanctions, refusals)
        
    Returns:
        Enhanced metadata dictionary
    """
    # Base metadata from crawling
    base_metadata = item["metadata"]
    
    # Content categorization based on domain and extracted data
    content_categories = _categorize_crawled_content(item["extracted_data"], domain)
    
    # Regulatory authority identification
    regulatory_authority = _identify_regulatory_authority(item["source_url"], domain)
    
    # Content quality assessment
    quality_score = _assess_content_quality(item, domain)
    
    # Structured metadata for ChromaDB storage
    structured_metadata = _build_structured_metadata(item["extracted_data"], domain)
    
    # Enhanced metadata combining all aspects
    enhanced_metadata = {
        # Basic crawl metadata
        "doc_type": f"crawled_{item['content_type']}",
        "source": "crawl4ai",
        "source_attribution": base_metadata["source_attribution"],
        "source_url": item["source_url"],
        "data_quality": "crawled",
        "update_frequency": "on_demand",
        
        # Enhanced categorization
        "content_categories": content_categories,
        "primary_category": content_categories[0] if content_categories else "general",
        "regulatory_authority": regulatory_authority,
        "compliance_domain": domain,
        
        # Quality and confidence metrics
        "extraction_confidence": base_metadata["extraction_confidence"],
        "content_quality_score": quality_score,
        "extraction_method": base_metadata["extraction_method"],
        
        # Technical metadata
        "content_hash": base_metadata["content_hash"],
        "change_detected": base_metadata["change_detected"],
        "rate_limit_applied": base_metadata["rate_limit_applied"],
        "last_modified": base_metadata["last_modified"],
        "last_seen_at": base_metadata["scraped_at"],
        
        # Structured metadata for RAG retrieval
        "structured_fields": structured_metadata,
        
        # Search and indexing metadata
        "searchable_text": _extract_searchable_text(item["extracted_data"]),
        "key_terms": _extract_key_terms(item["extracted_data"], domain),
        "effective_date": _extract_effective_date(item["extracted_data"]),
        "document_language": "en",  # Assume English for US compliance content
        
        # Lineage and provenance
        "crawl_session_id": f"session_{datetime.utcnow().strftime('%Y%m%d_%H')}",
        "processing_pipeline": "zenml_crawl4ai_integration",
        "ingestion_timestamp": datetime.utcnow().isoformat()
    }
    
    return enhanced_metadata


def _categorize_crawled_content(extracted_data: Dict[str, Any], domain: str) -> List[str]:
    """
    Categorize crawled content based on extracted data and domain.
    
    Args:
        extracted_data: Extracted structured data
        domain: Compliance domain
        
    Returns:
        List of content categories
    """
    categories = []
    
    # Domain-specific categorization
    if domain == "hts":
        if "tariff" in str(extracted_data).lower():
            categories.append("tariff_schedule")
        if "duty" in str(extracted_data).lower():
            categories.append("duty_rates")
        if "classification" in str(extracted_data).lower():
            categories.append("classification_guidance")
        if "note" in str(extracted_data).lower():
            categories.append("explanatory_notes")
    
    elif domain == "rulings":
        if "ruling" in str(extracted_data).lower():
            categories.append("classification_ruling")
        if "precedent" in str(extracted_data).lower():
            categories.append("precedent_decision")
        if "interpretation" in str(extracted_data).lower():
            categories.append("regulatory_interpretation")
    
    elif domain == "sanctions":
        if "sanction" in str(extracted_data).lower():
            categories.append("sanctions_list")
        if "embargo" in str(extracted_data).lower():
            categories.append("trade_embargo")
        if "restricted" in str(extracted_data).lower():
            categories.append("restricted_entity")
        if "denied" in str(extracted_data).lower():
            categories.append("denied_persons")
    
    elif domain == "refusals":
        if "refusal" in str(extracted_data).lower():
            categories.append("import_refusal")
        if "detention" in str(extracted_data).lower():
            categories.append("detention_notice")
        if "violation" in str(extracted_data).lower():
            categories.append("regulatory_violation")
    
    # General categories
    if "policy" in str(extracted_data).lower():
        categories.append("policy_update")
    if "guidance" in str(extracted_data).lower():
        categories.append("regulatory_guidance")
    if "announcement" in str(extracted_data).lower():
        categories.append("official_announcement")
    
    return categories if categories else ["general_compliance"]


def _identify_regulatory_authority(source_url: str, domain: str) -> str:
    """
    Identify the regulatory authority based on source URL and domain.
    
    Args:
        source_url: Source URL of the content
        domain: Compliance domain
        
    Returns:
        Regulatory authority identifier
    """
    url_lower = source_url.lower()
    
    # URL-based identification
    if "usitc.gov" in url_lower:
        return "usitc"
    elif "cbp.gov" in url_lower:
        return "cbp"
    elif "treasury.gov" in url_lower or "ofac" in url_lower:
        return "ofac"
    elif "bis.doc.gov" in url_lower:
        return "bis"
    elif "fda.gov" in url_lower:
        return "fda"
    elif "trade.gov" in url_lower:
        return "ita"
    
    # Domain-based fallback
    authority_mapping = {
        "hts": "usitc",
        "rulings": "cbp",
        "sanctions": "ofac",
        "refusals": "fda"
    }
    
    return authority_mapping.get(domain, "unknown")


def _assess_content_quality(item: Dict[str, Any], domain: str) -> float:
    """
    Assess the quality of crawled content.
    
    Args:
        item: Crawled content item
        domain: Compliance domain
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    quality_score = 0.0
    
    # Base score from extraction confidence
    extraction_confidence = item["metadata"]["extraction_confidence"]
    quality_score += extraction_confidence * 0.4
    
    # Content completeness
    extracted_data = item["extracted_data"]
    if extracted_data and len(str(extracted_data)) > 100:
        quality_score += 0.2
    
    # Source reliability (official government sites get higher scores)
    source_url = item["source_url"]
    if any(domain in source_url for domain in [".gov", "usitc", "cbp", "treasury", "fda"]):
        quality_score += 0.3
    
    # Content freshness
    if item["metadata"]["change_detected"]:
        quality_score += 0.1
    
    return min(quality_score, 1.0)


def _build_structured_metadata(extracted_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """
    Build structured metadata for improved ChromaDB storage and RAG retrieval.
    
    Args:
        extracted_data: Extracted structured data
        domain: Compliance domain
        
    Returns:
        Structured metadata dictionary
    """
    structured_metadata = {}
    
    # Extract domain-specific structured fields
    if domain == "hts" and isinstance(extracted_data, dict):
        structured_metadata.update({
            "hts_code": extracted_data.get("hts_code", ""),
            "description": extracted_data.get("description", ""),
            "duty_rate": extracted_data.get("duty_rate", ""),
            "chapter": extracted_data.get("hts_code", "")[:2] if extracted_data.get("hts_code") else "",
            "heading": extracted_data.get("hts_code", "")[:4] if extracted_data.get("hts_code") else ""
        })
    
    elif domain == "rulings" and isinstance(extracted_data, dict):
        structured_metadata.update({
            "ruling_number": extracted_data.get("ruling_number", ""),
            "hts_code": extracted_data.get("hts_code", ""),
            "ruling_date": extracted_data.get("ruling_date", ""),
            "product_description": extracted_data.get("description", "")
        })
    
    elif domain == "sanctions" and isinstance(extracted_data, dict):
        structured_metadata.update({
            "entity_name": extracted_data.get("entity_name", ""),
            "list_source": extracted_data.get("list_source", ""),
            "programs": extracted_data.get("programs", []),
            "country": extracted_data.get("country", "")
        })
    
    elif domain == "refusals" and isinstance(extracted_data, dict):
        structured_metadata.update({
            "firm_name": extracted_data.get("firm_name", ""),
            "product_description": extracted_data.get("product_description", ""),
            "refusal_reason": extracted_data.get("refusal_reason", ""),
            "country": extracted_data.get("country", "")
        })
    
    return structured_metadata


def _extract_searchable_text(extracted_data: Dict[str, Any]) -> str:
    """
    Extract searchable text from extracted data.
    
    Args:
        extracted_data: Extracted structured data
        
    Returns:
        Searchable text string
    """
    if isinstance(extracted_data, dict):
        # Combine all text values from the dictionary
        text_parts = []
        for key, value in extracted_data.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, list):
                text_parts.extend([str(item) for item in value if isinstance(item, str)])
        return " ".join(text_parts)
    elif isinstance(extracted_data, str):
        return extracted_data
    else:
        return str(extracted_data)


def _extract_key_terms(extracted_data: Dict[str, Any], domain: str) -> List[str]:
    """
    Extract key terms for indexing and search.
    
    Args:
        extracted_data: Extracted structured data
        domain: Compliance domain
        
    Returns:
        List of key terms
    """
    key_terms = []
    
    # Domain-specific key term extraction
    if domain == "hts" and isinstance(extracted_data, dict):
        if "hts_code" in extracted_data:
            key_terms.append(extracted_data["hts_code"])
        if "description" in extracted_data:
            # Extract product keywords from description
            description = extracted_data["description"].lower()
            product_keywords = ["steel", "textile", "electronic", "machinery", "chemical", "food"]
            key_terms.extend([kw for kw in product_keywords if kw in description])
    
    elif domain == "rulings" and isinstance(extracted_data, dict):
        if "ruling_number" in extracted_data:
            key_terms.append(extracted_data["ruling_number"])
        if "hts_code" in extracted_data:
            key_terms.append(extracted_data["hts_code"])
    
    elif domain == "sanctions" and isinstance(extracted_data, dict):
        if "entity_name" in extracted_data:
            key_terms.append(extracted_data["entity_name"])
        if "programs" in extracted_data and isinstance(extracted_data["programs"], list):
            key_terms.extend(extracted_data["programs"])
    
    elif domain == "refusals" and isinstance(extracted_data, dict):
        if "firm_name" in extracted_data:
            key_terms.append(extracted_data["firm_name"])
        if "country" in extracted_data:
            key_terms.append(extracted_data["country"])
    
    return [term for term in key_terms if term]  # Remove empty terms


def _extract_effective_date(extracted_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract effective date from extracted data.
    
    Args:
        extracted_data: Extracted structured data
        
    Returns:
        Effective date string or None
    """
    if isinstance(extracted_data, dict):
        # Look for common date fields
        date_fields = ["effective_date", "ruling_date", "refusal_date", "date", "published_date"]
        for field in date_fields:
            if field in extracted_data and extracted_data[field]:
                return extracted_data[field]
    
    return None


def _get_existing_content_hashes() -> set:
    """
    Get existing content hashes from ChromaDB collections for deduplication.
    
    Returns:
        Set of existing content hashes
    """
    existing_hashes = set()
    
    try:
        # Query all collections for existing content hashes
        collections = [
            compliance_collections.HTS_NOTES,
            compliance_collections.RULINGS,
            compliance_collections.REFUSALS,
            compliance_collections.POLICY
        ]
        
        for collection_name in collections:
            try:
                collection = compliance_collections.get_collection(collection_name)
                # Get all documents with content_hash metadata
                results = collection.get(include=["metadatas"])
                
                if results and results.get("metadatas"):
                    for metadata in results["metadatas"]:
                        if metadata and "content_hash" in metadata:
                            existing_hashes.add(metadata["content_hash"])
                            
            except Exception as e:
                logger.warning(f"Failed to get hashes from collection {collection_name}: {e}")
                
    except Exception as e:
        logger.warning(f"Failed to retrieve existing content hashes: {e}")
    
    logger.info(f"Found {len(existing_hashes)} existing content hashes for deduplication")
    return existing_hashes


def _build_crawled_hts_content(record: Dict[str, Any], data: Dict[str, Any], enhanced_meta: Dict[str, Any]) -> str:
    """
    Build content string for crawled HTS data with enhanced structure.
    
    Args:
        record: Record data
        data: Extracted data
        enhanced_meta: Enhanced metadata
        
    Returns:
        Formatted content string
    """
    content_parts = []
    
    # Source attribution for crawled content
    content_parts.append(f"Source: {enhanced_meta.get('source_attribution', 'Web Crawled Content')}")
    content_parts.append(f"URL: {record.get('source_id', '')}")
    
    # Structured fields from crawled data
    structured_fields = enhanced_meta.get("structured_fields", {})
    if structured_fields.get("hts_code"):
        content_parts.append(f"HTS Code: {structured_fields['hts_code']}")
    if structured_fields.get("description"):
        content_parts.append(f"Description: {structured_fields['description']}")
    if structured_fields.get("duty_rate"):
        content_parts.append(f"Duty Rate: {structured_fields['duty_rate']}")
    
    # Raw extracted content
    if data:
        content_parts.append(f"Extracted Data: {str(data)}")
    
    # Content categories and key terms
    categories = enhanced_meta.get("content_categories", [])
    if categories:
        content_parts.append(f"Categories: {', '.join(categories)}")
    
    key_terms = enhanced_meta.get("key_terms", [])
    if key_terms:
        content_parts.append(f"Key Terms: {', '.join(key_terms)}")
    
    return "\n".join(content_parts)


def _build_api_hts_content(record: Dict[str, Any], data: Dict[str, Any]) -> str:
    """
    Build content string for API-sourced HTS data (existing format).
    
    Args:
        record: Record data
        data: API response data
        
    Returns:
        Formatted content string
    """
    content = f"HTS Code: {record['source_id']}\n"
    content += f"Description: {data.get('description', '')}\n"
    content += f"Duty Rate: {data.get('duty_rate', 'Unknown')}\n"
    content += f"Notes: {', '.join(data.get('notes', []))}"
    return content


def _build_chromadb_metadata(record: Dict[str, Any], enhanced_meta: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """
    Build optimized metadata for ChromaDB storage and RAG retrieval.
    
    Args:
        record: Record data
        enhanced_meta: Enhanced metadata
        domain: Compliance domain
        
    Returns:
        ChromaDB-optimized metadata dictionary
    """
    # Base metadata
    metadata = {
        "domain": domain,
        "source_type": enhanced_meta.get("source", "api"),
        "doc_type": enhanced_meta.get("doc_type", f"{domain}_document"),
        "ingested_at": datetime.utcnow().isoformat(),
        "data_quality": enhanced_meta.get("data_quality", "unknown"),
        "regulatory_authority": enhanced_meta.get("regulatory_authority", "unknown")
    }
    
    # Add source attribution
    if "source_attribution" in enhanced_meta:
        metadata["source_attribution"] = enhanced_meta["source_attribution"]
    if "source_url" in enhanced_meta:
        metadata["source_url"] = enhanced_meta["source_url"]
    
    # Add content categorization
    if "content_categories" in enhanced_meta:
        metadata["categories"] = enhanced_meta["content_categories"]
        metadata["primary_category"] = enhanced_meta.get("primary_category", "general")
    
    # Add quality metrics
    if "extraction_confidence" in enhanced_meta:
        metadata["extraction_confidence"] = enhanced_meta["extraction_confidence"]
    if "content_quality_score" in enhanced_meta:
        metadata["quality_score"] = enhanced_meta["content_quality_score"]
    
    # Add structured fields for domain-specific search
    structured_fields = enhanced_meta.get("structured_fields", {})
    for field, value in structured_fields.items():
        if value:  # Only add non-empty values
            metadata[field] = value
    
    # Add searchable metadata
    if "key_terms" in enhanced_meta:
        metadata["key_terms"] = enhanced_meta["key_terms"]
    if "effective_date" in enhanced_meta:
        metadata["effective_date"] = enhanced_meta["effective_date"]
    
    # Add change detection metadata for crawled content
    if enhanced_meta.get("source") == "crawl4ai":
        metadata["change_detected"] = enhanced_meta.get("change_detected", False)
        metadata["content_hash"] = enhanced_meta.get("content_hash", "")
        metadata["last_modified"] = enhanced_meta.get("last_modified")
        metadata["crawl_session_id"] = enhanced_meta.get("crawl_session_id", "")
    
    return metadata


def _generate_document_id(record: Dict[str, Any], enhanced_meta: Dict[str, Any], domain: str) -> str:
    """
    Generate unique document ID with source differentiation.
    
    Args:
        record: Record data
        enhanced_meta: Enhanced metadata
        domain: Compliance domain
        
    Returns:
        Unique document ID
    """
    source_type = enhanced_meta.get("source", "api")
    base_id = record.get("id", "unknown")
    source_id = record.get("source_id", "")
    
    # Create ID that differentiates between API and crawled content
    if source_type == "crawl4ai":
        # Use content hash for crawled content to enable deduplication
        content_hash = enhanced_meta.get("content_hash", "")
        return f"{domain}_crawled_{content_hash[:8]}_{base_id}"
    else:
        # Use source_id for API content
        return f"{domain}_api_{source_id}_{base_id}"


def _build_crawled_rulings_content(record: Dict[str, Any], data: Dict[str, Any], enhanced_meta: Dict[str, Any]) -> str:
    """
    Build content string for crawled rulings data.
    
    Args:
        record: Record data
        data: Extracted data
        enhanced_meta: Enhanced metadata
        
    Returns:
        Formatted content string
    """
    content_parts = []
    
    # Source attribution
    content_parts.append(f"Source: {enhanced_meta.get('source_attribution', 'Web Crawled Ruling')}")
    content_parts.append(f"URL: {record.get('source_id', '')}")
    
    # Structured fields
    structured_fields = enhanced_meta.get("structured_fields", {})
    if structured_fields.get("ruling_number"):
        content_parts.append(f"Ruling Number: {structured_fields['ruling_number']}")
    if structured_fields.get("hts_code"):
        content_parts.append(f"HTS Code: {structured_fields['hts_code']}")
    if structured_fields.get("ruling_date"):
        content_parts.append(f"Date: {structured_fields['ruling_date']}")
    if structured_fields.get("product_description"):
        content_parts.append(f"Product: {structured_fields['product_description']}")
    
    # Raw extracted content
    if data:
        content_parts.append(f"Extracted Content: {str(data)}")
    
    # Categories and key terms
    categories = enhanced_meta.get("content_categories", [])
    if categories:
        content_parts.append(f"Categories: {', '.join(categories)}")
    
    return "\n".join(content_parts)


def _build_api_rulings_content(ruling: Dict[str, Any]) -> str:
    """
    Build content string for API-sourced rulings data.
    
    Args:
        ruling: Individual ruling data
        
    Returns:
        Formatted content string
    """
    content = f"Ruling Number: {ruling.get('ruling_number', '')}\n"
    content += f"Description: {ruling.get('description', '')}\n"
    content += f"HTS Code: {ruling.get('hts_code', '')}\n"
    content += f"Date: {ruling.get('ruling_date', '')}"
    return content


def _build_crawled_refusals_content(record: Dict[str, Any], data: Dict[str, Any], enhanced_meta: Dict[str, Any]) -> str:
    """
    Build content string for crawled refusals data.
    
    Args:
        record: Record data
        data: Extracted data
        enhanced_meta: Enhanced metadata
        
    Returns:
        Formatted content string
    """
    content_parts = []
    
    # Source attribution
    content_parts.append(f"Source: {enhanced_meta.get('source_attribution', 'Web Crawled Refusal')}")
    content_parts.append(f"URL: {record.get('source_id', '')}")
    
    # Structured fields
    structured_fields = enhanced_meta.get("structured_fields", {})
    if structured_fields.get("firm_name"):
        content_parts.append(f"Firm: {structured_fields['firm_name']}")
    if structured_fields.get("product_description"):
        content_parts.append(f"Product: {structured_fields['product_description']}")
    if structured_fields.get("refusal_reason"):
        content_parts.append(f"Reason: {structured_fields['refusal_reason']}")
    if structured_fields.get("country"):
        content_parts.append(f"Country: {structured_fields['country']}")
    
    # Raw extracted content
    if data:
        content_parts.append(f"Extracted Content: {str(data)}")
    
    # Categories
    categories = enhanced_meta.get("content_categories", [])
    if categories:
        content_parts.append(f"Categories: {', '.join(categories)}")
    
    return "\n".join(content_parts)


def _build_api_refusals_content(record: Dict[str, Any], refusal: Dict[str, Any]) -> str:
    """
    Build content string for API-sourced refusals data.
    
    Args:
        record: Record data
        refusal: Individual refusal data
        
    Returns:
        Formatted content string
    """
    content = f"Country: {record['source_id']}\n"
    content += f"Firm: {refusal.get('firm_name', '')}\n"
    content += f"Product: {refusal.get('product_description', '')}\n"
    content += f"Reason: {refusal.get('refusal_reason', '')}\n"
    content += f"Date: {refusal.get('refusal_date', '')}"
    return content


def _build_crawled_sanctions_content(record: Dict[str, Any], data: Dict[str, Any], enhanced_meta: Dict[str, Any]) -> str:
    """
    Build content string for crawled sanctions data.
    
    Args:
        record: Record data
        data: Extracted data
        enhanced_meta: Enhanced metadata
        
    Returns:
        Formatted content string
    """
    content_parts = []
    
    # Source attribution
    content_parts.append(f"Source: {enhanced_meta.get('source_attribution', 'Web Crawled Sanctions')}")
    content_parts.append(f"URL: {record.get('source_id', '')}")
    
    # Structured fields
    structured_fields = enhanced_meta.get("structured_fields", {})
    if structured_fields.get("entity_name"):
        content_parts.append(f"Entity: {structured_fields['entity_name']}")
    if structured_fields.get("list_source"):
        content_parts.append(f"List Source: {structured_fields['list_source']}")
    if structured_fields.get("programs"):
        programs = structured_fields["programs"]
        if isinstance(programs, list):
            content_parts.append(f"Programs: {', '.join(programs)}")
        else:
            content_parts.append(f"Programs: {programs}")
    if structured_fields.get("country"):
        content_parts.append(f"Country: {structured_fields['country']}")
    
    # Raw extracted content
    if data:
        content_parts.append(f"Extracted Content: {str(data)}")
    
    # Categories
    categories = enhanced_meta.get("content_categories", [])
    if categories:
        content_parts.append(f"Categories: {', '.join(categories)}")
    
    return "\n".join(content_parts)


def _build_api_sanctions_content(record: Dict[str, Any], match: Dict[str, Any]) -> str:
    """
    Build content string for API-sourced sanctions data.
    
    Args:
        record: Record data
        match: Individual sanctions match
        
    Returns:
        Formatted content string
    """
    content = f"Entity: {record['source_id']}\n"
    content += f"Matched Name: {match.get('name', '')}\n"
    content += f"List Source: {match.get('source', '')}\n"
    content += f"Programs: {', '.join(match.get('programs', []))}"
    return content


@step
def initialize_collections() -> bool:
    """
    Step 1: Initialize compliance collections.
    
    Returns:
        True if successful
    """
    logger.info("Initializing compliance collections...")
    
    try:
        compliance_collections.initialize()
        logger.info("Compliance collections initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize collections: {e}")
        raise


@step(enable_cache=True)
def fetch_hts_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 2: Fetch HTS code updates and new notes using real API calls.
    
    Args:
        lookback_days: Number of days to look back for updates
        
    Returns:
        List of HTS update records
    """
    logger.info(f"Fetching HTS updates from last {lookback_days} days...")
    
    hts_tool = HTSTool()
    
    # Sample HTS codes to check - in production this would be from monitored SKUs
    sample_hts_codes = [
        "8517.12.00",
        "6203.42.40", 
        "8471.30.01",
        "9403.60.80",
        "8528.72.64"
    ]
    
    updates = []
    for hts_code in sample_hts_codes:
        try:
            # Use real tool that now calls USITC API and stores in Supabase
            result = hts_tool.run(hts_code=hts_code)
            
            if result:
                updates.append({
                    "hts_code": hts_code,
                    "description": result.get("description", ""),
                    "duty_rate": result.get("duty_rate", "Unknown"),
                    "notes": result.get("notes", []),
                    "fetched_at": datetime.utcnow().isoformat(),
                    "source": "usitc_api"
                })
                logger.info(f"Successfully fetched HTS data for {hts_code}")
        except Exception as e:
            logger.error(f"Failed to fetch HTS {hts_code}: {e}")
            # Continue with other codes on failure
            continue
    
    logger.info(f"Fetched {len(updates)} HTS updates")
    return updates


@step(enable_cache=True)
def fetch_sanctions_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 3: Fetch sanctions list updates using real API calls.
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of new sanctions entries
    """
    logger.info(f"Fetching sanctions updates from last {lookback_days} days...")
    
    sanctions_tool = SanctionsTool()
    
    # Sample entities to check - in production this would be from monitored entities
    sample_entities = [
        "Test Company Ltd",
        "Sample Corporation", 
        "Example Trading Co",
        "Demo Industries Inc"
    ]
    
    updates = []
    for entity_name in sample_entities:
        try:
            # Use real tool that now calls CSL API and stores in Supabase
            result = sanctions_tool.run(entity_name=entity_name)
            
            if result and result.get("matches"):
                for match in result["matches"][:3]:  # Limit to top 3 matches per entity
                    updates.append({
                        "entity_name": entity_name,
                        "matched_name": match.get("name", ""),
                        "list_source": match.get("source", "CSL"),
                        "match_score": match.get("score", 0),
                        "fetched_at": datetime.utcnow().isoformat(),
                        "source": "csl_api"
                    })
                logger.info(f"Found {len(result['matches'])} sanctions matches for {entity_name}")
        except Exception as e:
            logger.error(f"Failed to fetch sanctions for {entity_name}: {e}")
            # Continue with other entities on failure
            continue
    
    logger.info(f"Fetched {len(updates)} sanctions updates")
    return updates


@step(enable_cache=True)
def fetch_refusals_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 4: Fetch import refusals updates using real API calls.
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of new refusal records
    """
    logger.info(f"Fetching refusals from last {lookback_days} days...")
    
    refusals_tool = RefusalsTool()
    
    # Query recent refusals for key countries
    countries = ["China", "India", "Mexico", "Vietnam"]
    
    updates = []
    for country in countries:
        try:
            # Use real tool that now calls FDA API and stores in Supabase
            result = refusals_tool.run(country=country)
            
            if result and result.get("refusals"):
                for refusal in result["refusals"][:5]:  # Top 5 per country
                    updates.append({
                        "country": country,
                        "firm_name": refusal.get("firm_name", "Unknown"),
                        "product_description": refusal.get("product_description", ""),
                        "refusal_reason": refusal.get("refusal_reason", ""),
                        "refusal_date": refusal.get("refusal_date", ""),
                        "fetched_at": datetime.utcnow().isoformat(),
                        "source": "fda_api"
                    })
                logger.info(f"Successfully fetched {len(result['refusals'])} refusals for {country}")
        except Exception as e:
            logger.error(f"Failed to fetch refusals for {country}: {e}")
            # Continue with other countries on failure
            continue
    
    logger.info(f"Fetched {len(updates)} refusal records")
    return updates


@step(enable_cache=True)
def fetch_rulings_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 5: Fetch CBP rulings updates using real web scraping.
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of new rulings
    """
    logger.info(f"Fetching CBP rulings from last {lookback_days} days...")
    
    rulings_tool = RulingsTool()
    
    # Sample keywords to search - in production this would be from monitored products
    keywords = ["electronics", "textiles", "machinery", "furniture"]
    
    updates = []
    for keyword in keywords:
        try:
            # Use real tool that now scrapes CBP CROSS and stores in Supabase
            result = rulings_tool.run(search_term=keyword)
            
            if result and result.get("rulings"):
                for ruling in result["rulings"][:3]:  # Top 3 per keyword
                    updates.append({
                        "ruling_number": ruling.get("ruling_number", ""),
                        "description": ruling.get("description", ""),
                        "hts_code": ruling.get("hts_code", ""),
                        "ruling_date": ruling.get("ruling_date", ""),
                        "search_keyword": keyword,
                        "fetched_at": datetime.utcnow().isoformat(),
                        "source": "cbp_cross"
                    })
                logger.info(f"Successfully fetched {len(result['rulings'])} rulings for {keyword}")
        except Exception as e:
            logger.error(f"Failed to fetch rulings for {keyword}: {e}")
            # Continue with other keywords on failure
            continue
    
    logger.info(f"Fetched {len(updates)} rulings")
    return updates


@step
def read_supabase_data() -> Dict[str, List[Dict[str, Any]]]:
    """
    Step 6: Read processed compliance data from Supabase for vector storage.
    
    Returns:
        Dictionary of compliance data by source type
    """
    logger.info("Reading processed compliance data from Supabase...")
    
    data_by_source = {
        "hts": [],
        "sanctions": [],
        "refusals": [],
        "rulings": []
    }
    
    try:
        # Read data from each source type
        for source_type in data_by_source.keys():
            data = supabase_client.get_compliance_data(source_type)
            data_by_source[source_type] = data
            logger.info(f"Retrieved {len(data)} records for {source_type}")
            
    except Exception as e:
        logger.error(f"Failed to read Supabase data: {e}")
        # Return empty data on failure
        
    total_records = sum(len(records) for records in data_by_source.values())
    logger.info(f"Total records retrieved from Supabase: {total_records}")
    return data_by_source


@step
def enhance_metadata_tagging(
    supabase_data: Dict[str, List[Dict[str, Any]]],
    crawled_content: Dict[str, List[Dict[str, Any]]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Step 7: Enhance metadata tagging for better source attribution and searchability.
    
    Args:
        supabase_data: Raw compliance data from Supabase
        crawled_content: Crawled content from web scraping (optional)
        
    Returns:
        Enhanced data with enriched metadata including crawled content
    """
    logger.info("Enhancing metadata tagging for source attribution...")
    
    if crawled_content is None:
        crawled_content = {}
    
    enhanced_data = {}
    
    # Enhance HTS data metadata
    enhanced_data["hts"] = []
    for record in supabase_data.get("hts", []):
        data = record.get("data", {})
        enhanced_record = record.copy()
        enhanced_record["enhanced_metadata"] = {
            "doc_type": "hts_classification",
            "source": "usitc_api",
            "source_attribution": "USITC Harmonized Tariff Schedule REST API",
            "source_url": f"https://hts.usitc.gov/reststop/tariff/{record['source_id']}",
            "data_quality": "official",
            "update_frequency": "daily",
            "hts_chapter": record["source_id"][:2] if len(record["source_id"]) >= 2 else "",
            "classification_level": "10-digit" if len(record["source_id"]) == 10 else "partial",
            "last_seen_at": datetime.utcnow().isoformat(),
            "content_hash": hash(str(data))
        }
        enhanced_data["hts"].append(enhanced_record)
    
    # Enhance rulings data metadata
    enhanced_data["rulings"] = []
    for record in supabase_data.get("rulings", []):
        data = record.get("data", {})
        enhanced_record = record.copy()
        enhanced_record["enhanced_metadata"] = {
            "doc_type": "cbp_ruling",
            "source": "cbp_cross",
            "source_attribution": "CBP Customs Rulings Online Search System (CROSS)",
            "source_url": "https://rulings.cbp.gov/",
            "data_quality": "official",
            "update_frequency": "daily",
            "precedent_value": "binding",
            "jurisdiction": "united_states",
            "search_term": record["source_id"],
            "last_seen_at": datetime.utcnow().isoformat(),
            "content_hash": hash(str(data))
        }
        enhanced_data["rulings"].append(enhanced_record)
    
    # Enhance refusals data metadata
    enhanced_data["refusals"] = []
    for record in supabase_data.get("refusals", []):
        data = record.get("data", {})
        enhanced_record = record.copy()
        enhanced_record["enhanced_metadata"] = {
            "doc_type": "import_refusal",
            "source": "fda_api",
            "source_attribution": "FDA Import Refusals Report API",
            "source_url": "https://www.accessdata.fda.gov/scripts/importrefusals/",
            "data_quality": "official",
            "update_frequency": "weekly",
            "regulatory_authority": "fda",
            "country_of_origin": record["source_id"],
            "risk_category": "health_safety",
            "last_seen_at": datetime.utcnow().isoformat(),
            "content_hash": hash(str(data))
        }
        enhanced_data["refusals"].append(enhanced_record)
    
    # Enhance sanctions data metadata
    enhanced_data["sanctions"] = []
    for record in supabase_data.get("sanctions", []):
        data = record.get("data", {})
        enhanced_record = record.copy()
        enhanced_record["enhanced_metadata"] = {
            "doc_type": "sanctions_screening",
            "source": "csl_api",
            "source_attribution": "ITA Consolidated Screening List API",
            "source_url": "https://api.trade.gov/consolidated_screening_list/v1/search",
            "data_quality": "official",
            "update_frequency": "daily",
            "regulatory_authority": "multiple",
            "screening_type": "entity_name",
            "entity_searched": record["source_id"],
            "last_seen_at": datetime.utcnow().isoformat(),
            "content_hash": hash(str(data))
        }
        enhanced_data["sanctions"].append(enhanced_record)
    
    # Process crawled content with enhanced metadata
    for domain, crawled_items in crawled_content.items():
        if domain not in enhanced_data:
            enhanced_data[domain] = []
        
        for item in crawled_items:
            # Enhanced content categorization and regulatory authority identification
            enhanced_metadata = _enhance_crawled_metadata(item, domain)
            
            # Create enhanced record for crawled content
            enhanced_record = {
                "id": f"crawled_{hash(item['source_url'])}",
                "source_id": item["source_url"],
                "data": item["extracted_data"],
                "raw_content": item["raw_content"],
                "created_at": item["metadata"]["scraped_at"],
                "enhanced_metadata": enhanced_metadata
            }
            enhanced_data[domain].append(enhanced_record)
    
    total_enhanced = sum(len(records) for records in enhanced_data.values())
    crawled_count = sum(len(items) for items in crawled_content.values())
    logger.info(f"Enhanced metadata for {total_enhanced} records (including {crawled_count} crawled items)")
    return enhanced_data


@step
def ingest_to_collections(
    enhanced_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, int]:
    """
    Step 8: Ingest enhanced data into ChromaDB collections with comprehensive metadata,
    content deduplication, and change detection for crawled content.
    
    Args:
        enhanced_data: Compliance data with enhanced metadata (includes crawled content)
        
    Returns:
        Count of documents added per collection
    """
    logger.info("Ingesting enhanced data into ChromaDB collections with deduplication...")
    
    counts = {
        "hts_notes": 0,
        "rulings": 0,
        "refusals": 0,
        "policy": 0
    }
    
    # Track content hashes for deduplication
    existing_hashes = _get_existing_content_hashes()
    deduplicated_count = 0
    
    # Ingest HTS data with enhanced metadata and deduplication
    hts_collection = compliance_collections.get_collection(compliance_collections.HTS_NOTES)
    for record in enhanced_data.get("hts", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            
            # Check for content deduplication
            content_hash = enhanced_meta.get("content_hash")
            if content_hash and content_hash in existing_hashes:
                deduplicated_count += 1
                logger.debug(f"Skipping duplicate HTS content: {content_hash}")
                continue
            
            # Build content with enhanced structure for crawled vs API data
            if enhanced_meta.get("source") == "crawl4ai":
                content = _build_crawled_hts_content(record, data, enhanced_meta)
            else:
                content = _build_api_hts_content(record, data)
            
            # Enhanced metadata for ChromaDB with optimized indexing
            metadata = _build_chromadb_metadata(record, enhanced_meta, "hts")
            
            # Generate unique ID with source differentiation
            doc_id = _generate_document_id(record, enhanced_meta, "hts")
            
            hts_collection.add_texts(
                texts=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            counts["hts_notes"] += 1
            
            # Track hash for future deduplication
            if content_hash:
                existing_hashes.add(content_hash)
                
        except Exception as e:
            logger.error(f"Failed to ingest HTS record {record.get('id')}: {e}")
    
    # Ingest rulings data with enhanced metadata and deduplication
    rulings_collection = compliance_collections.get_collection(compliance_collections.RULINGS)
    for record in enhanced_data.get("rulings", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            
            # Check for content deduplication
            content_hash = enhanced_meta.get("content_hash")
            if content_hash and content_hash in existing_hashes:
                deduplicated_count += 1
                logger.debug(f"Skipping duplicate rulings content: {content_hash}")
                continue
            
            # Handle both API and crawled rulings data
            if enhanced_meta.get("source") == "crawl4ai":
                # Single crawled ruling
                content = _build_crawled_rulings_content(record, data, enhanced_meta)
                metadata = _build_chromadb_metadata(record, enhanced_meta, "rulings")
                doc_id = _generate_document_id(record, enhanced_meta, "rulings")
                
                rulings_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                counts["rulings"] += 1
            else:
                # API data with multiple rulings
                rulings = data.get("rulings", [])
                for i, ruling in enumerate(rulings):
                    content = _build_api_rulings_content(ruling)
                    
                    # Create metadata for individual ruling
                    ruling_metadata = _build_chromadb_metadata(record, enhanced_meta, "rulings")
                    ruling_metadata.update({
                        "ruling_number": ruling.get("ruling_number", ""),
                        "hts_code": ruling.get("hts_code", ""),
                        "ruling_date": ruling.get("ruling_date", ""),
                        "description": ruling.get("description", "")
                    })
                    
                    doc_id = f"ruling_api_{ruling.get('ruling_number', record['id'])}_{record['id']}_{i}"
                    
                    rulings_collection.add_texts(
                        texts=[content],
                        metadatas=[ruling_metadata],
                        ids=[doc_id]
                    )
                    counts["rulings"] += 1
            
            # Track hash for future deduplication
            if content_hash:
                existing_hashes.add(content_hash)
                
        except Exception as e:
            logger.error(f"Failed to ingest rulings record {record.get('id')}: {e}")
    
    # Ingest refusals data with enhanced metadata and deduplication
    refusals_collection = compliance_collections.get_collection(compliance_collections.REFUSALS)
    for record in enhanced_data.get("refusals", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            
            # Check for content deduplication
            content_hash = enhanced_meta.get("content_hash")
            if content_hash and content_hash in existing_hashes:
                deduplicated_count += 1
                logger.debug(f"Skipping duplicate refusals content: {content_hash}")
                continue
            
            # Handle both API and crawled refusals data
            if enhanced_meta.get("source") == "crawl4ai":
                # Single crawled refusal
                content = _build_crawled_refusals_content(record, data, enhanced_meta)
                metadata = _build_chromadb_metadata(record, enhanced_meta, "refusals")
                doc_id = _generate_document_id(record, enhanced_meta, "refusals")
                
                refusals_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                counts["refusals"] += 1
            else:
                # API data with multiple refusals
                refusals = data.get("refusals", [])
                for i, refusal in enumerate(refusals):
                    content = _build_api_refusals_content(record, refusal)
                    
                    # Create metadata for individual refusal
                    refusal_metadata = _build_chromadb_metadata(record, enhanced_meta, "refusals")
                    refusal_metadata.update({
                        "country": record["source_id"],
                        "firm_name": refusal.get("firm_name", ""),
                        "product_description": refusal.get("product_description", ""),
                        "refusal_reason": refusal.get("refusal_reason", ""),
                        "refusal_date": refusal.get("refusal_date", "")
                    })
                    
                    doc_id = f"refusal_api_{record['source_id']}_{refusal.get('refusal_date', '')}_{record['id']}_{i}"
                    
                    refusals_collection.add_texts(
                        texts=[content],
                        metadatas=[refusal_metadata],
                        ids=[doc_id]
                    )
                    counts["refusals"] += 1
            
            # Track hash for future deduplication
            if content_hash:
                existing_hashes.add(content_hash)
                
        except Exception as e:
            logger.error(f"Failed to ingest refusals record {record.get('id')}: {e}")
    
    # Ingest sanctions data into policy collection with enhanced metadata and deduplication
    policy_collection = compliance_collections.get_collection(compliance_collections.POLICY)
    for record in enhanced_data.get("sanctions", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            
            # Check for content deduplication
            content_hash = enhanced_meta.get("content_hash")
            if content_hash and content_hash in existing_hashes:
                deduplicated_count += 1
                logger.debug(f"Skipping duplicate sanctions content: {content_hash}")
                continue
            
            # Handle both API and crawled sanctions data
            if enhanced_meta.get("source") == "crawl4ai":
                # Single crawled sanctions entry
                content = _build_crawled_sanctions_content(record, data, enhanced_meta)
                metadata = _build_chromadb_metadata(record, enhanced_meta, "sanctions")
                doc_id = _generate_document_id(record, enhanced_meta, "sanctions")
                
                policy_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                counts["policy"] += 1
            else:
                # API data with multiple matches
                matches = data.get("matches", [])
                for i, match in enumerate(matches):
                    content = _build_api_sanctions_content(record, match)
                    
                    # Create metadata for individual match
                    match_metadata = _build_chromadb_metadata(record, enhanced_meta, "sanctions")
                    match_metadata.update({
                        "entity_name": record["source_id"],
                        "matched_name": match.get("name", ""),
                        "list_source": match.get("source", ""),
                        "programs": match.get("programs", [])
                    })
                    
                    doc_id = f"sanctions_api_{record['source_id']}_{match.get('id', record['id'])}_{i}"
                    
                    policy_collection.add_texts(
                        texts=[content],
                        metadatas=[match_metadata],
                        ids=[doc_id]
                    )
                    counts["policy"] += 1
            
            # Track hash for future deduplication
            if content_hash:
                existing_hashes.add(content_hash)
                
        except Exception as e:
            logger.error(f"Failed to ingest sanctions record {record.get('id')}: {e}")
    
    total_ingested = sum(counts.values())
    logger.info(f"ChromaDB ingestion complete: {total_ingested} documents ingested, {deduplicated_count} duplicates skipped")
    logger.info(f"Ingestion breakdown: {counts}")
    
    # Add deduplication metrics to counts
    counts["deduplicated"] = deduplicated_count
    counts["total_processed"] = total_ingested + deduplicated_count
    
    return counts


@step
def generate_ingestion_report(
    counts: Dict[str, int],
    crawled_content: Dict[str, List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Step 9: Generate comprehensive ingestion summary report.
    
    Args:
        counts: Document counts per collection
        crawled_content: Crawled content metrics (optional)
        
    Returns:
        Ingestion report with health, performance, and crawling metrics
    """
    total_docs = sum(counts.values())
    
    if crawled_content is None:
        crawled_content = {}
    
    # Calculate crawling metrics
    crawl_metrics = {}
    total_crawled = 0
    for domain, items in crawled_content.items():
        crawl_metrics[domain] = len(items)
        total_crawled += len(items)
    
    report = {
        "ingestion_date": datetime.utcnow().isoformat(),
        "total_documents": total_docs,
        "by_collection": counts,
        "status": "success" if total_docs > 0 else "no_updates",
        "pipeline_version": "crawl4ai_integrated",
        "data_sources": {
            "hts": "USITC HTS REST API + Web Crawling",
            "sanctions": "ITA Consolidated Screening List API + Web Crawling", 
            "refusals": "FDA Import Refusals API + Web Crawling",
            "rulings": "CBP CROSS Website + Enhanced Web Crawling"
        },
        "crawling_metrics": {
            "total_crawled_items": total_crawled,
            "by_domain": crawl_metrics,
            "crawling_enabled": total_crawled > 0
        },
        "storage": {
            "raw_data": "Supabase compliance_data table",
            "vectors": "ChromaDB collections"
        }
    }
    
    logger.info(f"Ingestion report: {report}")
    return report


@step(enable_cache=True)
def crawl_compliance_content(
    domains: List[str] = None,
    lookback_days: int = 7
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Step 2.5: Crawl compliance content from government websites using Crawl4AI.
    
    Args:
        domains: List of compliance domains to crawl (defaults to all)
        lookback_days: Number of days to look back for content discovery
        
    Returns:
        Dict mapping domain names to lists of crawled content
    """
    logger.info(f"Starting crawl operation for compliance content (lookback: {lookback_days} days)")
    
    if domains is None:
        domains = ["hts", "rulings", "sanctions", "refusals"]
    
    crawl_service = CrawlService()
    
    try:
        # Run crawling operation synchronously (ZenML step wrapper)
        import asyncio
        
        # Configure crawling parameters
        crawl_params = {
            "max_urls": 20,  # Limit URLs per domain for pipeline efficiency
            "content_freshness_days": lookback_days,
            "ai_extraction": True,
            "structured_parsing": True
        }
        
        # Execute crawling
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            crawl_results = loop.run_until_complete(
                crawl_service.crawl_compliance_sources(
                    domains=domains,
                    parameters=crawl_params
                )
            )
        finally:
            loop.close()
        
        # Convert CrawlResult objects to serializable dicts for ZenML
        serialized_results = {}
        for domain, results in crawl_results.items():
            serialized_results[domain] = []
            for result in results:
                if result.success:
                    serialized_results[domain].append({
                        "source_url": result.source_url,
                        "content_type": result.content_type.value,
                        "extracted_data": result.extracted_data,
                        "raw_content": result.raw_content[:5000],  # Truncate for storage
                        "metadata": {
                            "source_attribution": result.metadata.source_attribution,
                            "regulatory_authority": result.metadata.regulatory_authority,
                            "content_hash": result.metadata.content_hash,
                            "last_modified": result.metadata.last_modified.isoformat() if result.metadata.last_modified else None,
                            "extraction_method": result.metadata.extraction_method,
                            "rate_limit_applied": result.metadata.rate_limit_applied,
                            "change_detected": result.metadata.change_detected,
                            "extraction_confidence": result.extraction_confidence,
                            "scraped_at": result.scraped_at.isoformat()
                        }
                    })
        
        total_crawled = sum(len(results) for results in serialized_results.values())
        logger.info(f"Crawling completed: {total_crawled} items across {len(domains)} domains")
        
        return serialized_results
        
    except Exception as e:
        logger.error(f"Crawling operation failed: {e}")
        # Return empty results on failure to allow pipeline to continue
        return {domain: [] for domain in domains}


@step
def validate_pipeline_health() -> Dict[str, bool]:
    """
    Step 8: Validate pipeline health and external dependencies.
    
    Returns:
        Health status of various components
    """
    logger.info("Validating pipeline health...")
    
    health_status = {
        "supabase": False,
        "chromadb": False,
        "collections": False
    }
    
    try:
        # Check Supabase connection
        health_status["supabase"] = supabase_client.health_check()
        
        # Check ChromaDB collections
        health_status["collections"] = compliance_collections.health_check()
        health_status["chromadb"] = True  # If collections work, ChromaDB is healthy
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    logger.info(f"Pipeline health status: {health_status}")
    return health_status


@pipeline
def compliance_ingestion_pipeline(
    lookback_days: int = 7,
    enable_crawling: bool = True
):
    """
    Daily compliance data ingestion pipeline with Supabase integration, enhanced metadata, and web crawling.
    
    Steps:
    1. Validate pipeline health
    2. Initialize collections
    3. Parallel execution:
       - Fetch HTS updates via API (stores in Supabase)
       - Fetch sanctions updates via API (stores in Supabase)
       - Fetch refusals updates via API (stores in Supabase)
       - Fetch rulings updates via API (stores in Supabase)
       - Crawl compliance content from websites (Crawl4AI)
    4. Read processed data from Supabase
    5. Enhance metadata tagging for source attribution (including crawled content)
    6. Ingest to ChromaDB with comprehensive metadata
    7. Generate report
    
    Args:
        lookback_days: Number of days to look back for updates
        enable_crawling: Whether to enable web crawling (default: True)
    """
    # Validate health first
    health_status = validate_pipeline_health()
    
    # Initialize collections
    collections_ready = initialize_collections()
    
    # Parallel execution of API fetching and web crawling
    # These can run in parallel since they're independent
    try:
        hts_updates = fetch_hts_updates(lookback_days=lookback_days)
    except Exception as e:
        logger.error(f"HTS fetch failed: {e}")
        hts_updates = []
    
    try:
        sanctions_updates = fetch_sanctions_updates(lookback_days=lookback_days)
    except Exception as e:
        logger.error(f"Sanctions fetch failed: {e}")
        sanctions_updates = []
    
    try:
        refusals_updates = fetch_refusals_updates(lookback_days=lookback_days)
    except Exception as e:
        logger.error(f"Refusals fetch failed: {e}")
        refusals_updates = []
    
    try:
        rulings_updates = fetch_rulings_updates(lookback_days=lookback_days)
    except Exception as e:
        logger.error(f"Rulings fetch failed: {e}")
        rulings_updates = []
    
    # Web crawling step (runs in parallel with API fetching)
    crawled_content = {}
    if enable_crawling:
        try:
            crawled_content = crawl_compliance_content(
                domains=["hts", "rulings", "sanctions", "refusals"],
                lookback_days=lookback_days
            )
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            crawled_content = {}
    
    # Read processed data from Supabase for vector storage
    supabase_data = read_supabase_data()
    
    # Enhance metadata tagging for better source attribution (includes crawled content)
    enhanced_data = enhance_metadata_tagging(
        supabase_data=supabase_data,
        crawled_content=crawled_content
    )
    
    # Ingest to ChromaDB with comprehensive metadata
    counts = ingest_to_collections(enhanced_data=enhanced_data)
    
    # Generate report (includes crawling metrics)
    report = generate_ingestion_report(
        counts=counts,
        crawled_content=crawled_content
    )
    
    return report
