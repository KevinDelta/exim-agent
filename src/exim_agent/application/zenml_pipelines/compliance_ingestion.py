"""ZenML pipeline for compliance data ingestion."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from loguru import logger

from zenml import pipeline, step

from exim_agent.infrastructure.db.compliance_collections import compliance_collections
from exim_agent.infrastructure.db.supabase_client import supabase_client
from exim_agent.domain.tools.hts_tool import HTSTool
from exim_agent.domain.tools.sanctions_tool import SanctionsTool
from exim_agent.domain.tools.refusals_tool import RefusalsTool
from exim_agent.domain.tools.rulings_tool import RulingsTool


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
    supabase_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Step 7: Enhance metadata tagging for better source attribution and searchability.
    
    Args:
        supabase_data: Raw compliance data from Supabase
        
    Returns:
        Enhanced data with enriched metadata
    """
    logger.info("Enhancing metadata tagging for source attribution...")
    
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
    
    total_enhanced = sum(len(records) for records in enhanced_data.values())
    logger.info(f"Enhanced metadata for {total_enhanced} records")
    return enhanced_data


@step
def ingest_to_collections(
    enhanced_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, int]:
    """
    Step 8: Ingest enhanced data into ChromaDB collections with comprehensive metadata.
    
    Args:
        enhanced_data: Compliance data with enhanced metadata
        
    Returns:
        Count of documents added per collection
    """
    logger.info("Ingesting enhanced data into ChromaDB collections...")
    
    counts = {
        "hts_notes": 0,
        "rulings": 0,
        "refusals": 0,
        "policy": 0
    }
    
    # Ingest HTS data with enhanced metadata
    hts_collection = compliance_collections.get_collection(compliance_collections.HTS_NOTES)
    for record in enhanced_data.get("hts", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            
            content = f"HTS Code: {record['source_id']}\n"
            content += f"Description: {data.get('description', '')}\n"
            content += f"Duty Rate: {data.get('duty_rate', 'Unknown')}\n"
            content += f"Notes: {', '.join(data.get('notes', []))}"
            
            # Combine original and enhanced metadata
            metadata = {
                "hts_code": record["source_id"],
                "duty_rate": data.get("duty_rate", "Unknown"),
                "description": data.get("description", ""),
                "ingested_at": datetime.utcnow().isoformat(),
                **enhanced_meta  # Include all enhanced metadata
            }
            
            hts_collection.add_texts(
                texts=[content],
                metadatas=[metadata],
                ids=[f"hts_{record['source_id']}_{record['id']}"]
            )
            counts["hts_notes"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest HTS record {record.get('id')}: {e}")
    
    # Ingest rulings data with enhanced metadata
    rulings_collection = compliance_collections.get_collection(compliance_collections.RULINGS)
    for record in enhanced_data.get("rulings", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            rulings = data.get("rulings", [])
            
            for ruling in rulings:
                content = f"Ruling Number: {ruling.get('ruling_number', '')}\n"
                content += f"Description: {ruling.get('description', '')}\n"
                content += f"HTS Code: {ruling.get('hts_code', '')}\n"
                content += f"Date: {ruling.get('ruling_date', '')}"
                
                metadata = {
                    "ruling_number": ruling.get("ruling_number", ""),
                    "hts_code": ruling.get("hts_code", ""),
                    "ruling_date": ruling.get("ruling_date", ""),
                    "description": ruling.get("description", ""),
                    "ingested_at": datetime.utcnow().isoformat(),
                    **enhanced_meta  # Include all enhanced metadata
                }
                
                rulings_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[f"ruling_{ruling.get('ruling_number', record['id'])}_{record['id']}"]
                )
                counts["rulings"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest rulings record {record.get('id')}: {e}")
    
    # Ingest refusals data with enhanced metadata
    refusals_collection = compliance_collections.get_collection(compliance_collections.REFUSALS)
    for record in enhanced_data.get("refusals", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            refusals = data.get("refusals", [])
            
            for refusal in refusals:
                content = f"Country: {record['source_id']}\n"
                content += f"Firm: {refusal.get('firm_name', '')}\n"
                content += f"Product: {refusal.get('product_description', '')}\n"
                content += f"Reason: {refusal.get('refusal_reason', '')}\n"
                content += f"Date: {refusal.get('refusal_date', '')}"
                
                metadata = {
                    "country": record["source_id"],
                    "firm_name": refusal.get("firm_name", ""),
                    "product_description": refusal.get("product_description", ""),
                    "refusal_reason": refusal.get("refusal_reason", ""),
                    "refusal_date": refusal.get("refusal_date", ""),
                    "ingested_at": datetime.utcnow().isoformat(),
                    **enhanced_meta  # Include all enhanced metadata
                }
                
                refusals_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[f"refusal_{record['source_id']}_{refusal.get('refusal_date', '')}_{record['id']}"]
                )
                counts["refusals"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest refusals record {record.get('id')}: {e}")
    
    # Ingest sanctions data into policy collection with enhanced metadata
    policy_collection = compliance_collections.get_collection(compliance_collections.POLICY)
    for record in enhanced_data.get("sanctions", []):
        try:
            data = record.get("data", {})
            enhanced_meta = record.get("enhanced_metadata", {})
            matches = data.get("matches", [])
            
            for match in matches:
                content = f"Entity: {record['source_id']}\n"
                content += f"Matched Name: {match.get('name', '')}\n"
                content += f"List Source: {match.get('source', '')}\n"
                content += f"Programs: {', '.join(match.get('programs', []))}"
                
                metadata = {
                    "entity_name": record["source_id"],
                    "matched_name": match.get("name", ""),
                    "list_source": match.get("source", ""),
                    "programs": match.get("programs", []),
                    "ingested_at": datetime.utcnow().isoformat(),
                    **enhanced_meta  # Include all enhanced metadata
                }
                
                policy_collection.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[f"sanctions_{record['source_id']}_{match.get('id', record['id'])}"]
                )
                counts["policy"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest sanctions record {record.get('id')}: {e}")
    
    logger.info(f"ChromaDB ingestion complete with enhanced metadata: {counts}")
    return counts


@step
def generate_ingestion_report(
    counts: Dict[str, int]
) -> Dict[str, Any]:
    """
    Step 9: Generate comprehensive ingestion summary report.
    
    Args:
        counts: Document counts per collection
        
    Returns:
        Ingestion report with health and performance metrics
    """
    total_docs = sum(counts.values())
    
    report = {
        "ingestion_date": datetime.utcnow().isoformat(),
        "total_documents": total_docs,
        "by_collection": counts,
        "status": "success" if total_docs > 0 else "no_updates",
        "pipeline_version": "supabase_integrated",
        "data_sources": {
            "hts": "USITC HTS REST API",
            "sanctions": "ITA Consolidated Screening List API", 
            "refusals": "FDA Import Refusals API",
            "rulings": "CBP CROSS Website"
        },
        "storage": {
            "raw_data": "Supabase compliance_data table",
            "vectors": "ChromaDB collections"
        }
    }
    
    logger.info(f"Ingestion report: {report}")
    return report


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
    lookback_days: int = 7
):
    """
    Daily compliance data ingestion pipeline with Supabase integration and enhanced metadata.
    
    Steps:
    1. Validate pipeline health
    2. Initialize collections
    3. Fetch HTS updates (stores in Supabase)
    4. Fetch sanctions updates (stores in Supabase)
    5. Fetch refusals updates (stores in Supabase)
    6. Fetch rulings updates (stores in Supabase)
    7. Read processed data from Supabase
    8. Enhance metadata tagging for source attribution
    9. Ingest to ChromaDB with comprehensive metadata
    10. Generate report
    
    Args:
        lookback_days: Number of days to look back for updates
    """
    # Validate health first
    health_status = validate_pipeline_health()
    
    # Initialize collections
    collections_ready = initialize_collections()
    
    # Fetch updates from all sources (tools store data in Supabase)
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
    
    # Read processed data from Supabase for vector storage
    supabase_data = read_supabase_data()
    
    # Enhance metadata tagging for better source attribution
    enhanced_data = enhance_metadata_tagging(supabase_data=supabase_data)
    
    # Ingest to ChromaDB with comprehensive metadata
    counts = ingest_to_collections(enhanced_data=enhanced_data)
    
    # Generate report
    report = generate_ingestion_report(counts=counts)
    
    return report
