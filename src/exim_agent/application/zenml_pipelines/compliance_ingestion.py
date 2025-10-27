"""ZenML pipeline for compliance data ingestion."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from loguru import logger

from zenml import pipeline, step

from exim_agent.infrastructure.db.compliance_collections import compliance_collections
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
    Step 2: Fetch HTS code updates and new notes.
    
    Args:
        lookback_days: Number of days to look back for updates
        
    Returns:
        List of HTS update records
    """
    logger.info(f"Fetching HTS updates from last {lookback_days} days...")
    
    # In production, this would query USITC API for recent updates
    # For MVP, we'll use sample data
    hts_tool = HTSTool()
    
    # Sample HTS codes to check
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
            result = hts_tool.run(
                hts_code=hts_code,
                lane_id="general"
            )
            
            if result:
                updates.append({
                    "hts_code": hts_code,
                    "notes": result.get("notes", []),
                    "headings": result.get("headings", []),
                    "duty_rate": result.get("duty_rate", "Unknown"),
                    "fetched_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.warning(f"Failed to fetch HTS {hts_code}: {e}")
    
    logger.info(f"Fetched {len(updates)} HTS updates")
    return updates


@step(enable_cache=True)
def fetch_sanctions_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 3: Fetch sanctions list updates.
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of new sanctions entries
    """
    logger.info(f"Fetching sanctions updates from last {lookback_days} days...")
    
    sanctions_tool = SanctionsTool()
    
    # In production, would fetch actual CSL updates
    # For MVP, return sample data structure
    updates = [
        {
            "entity_name": "Sample Sanctioned Entity",
            "list_source": "OFAC SDN",
            "added_date": datetime.utcnow().isoformat(),
            "reason": "Sanctions program update"
        }
    ]
    
    logger.info(f"Fetched {len(updates)} sanctions updates")
    return updates


@step(enable_cache=True)
def fetch_refusals_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 4: Fetch import refusals updates.
    
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
            result = refusals_tool.run(country=country, product_type="general")
            
            if result and result.get("refusals"):
                for refusal in result["refusals"][:5]:  # Top 5 per country
                    updates.append({
                        "country": country,
                        "product": refusal.get("product", "Unknown"),
                        "reason": refusal.get("reason", ""),
                        "date": refusal.get("date", ""),
                        "fetched_at": datetime.utcnow().isoformat()
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch refusals for {country}: {e}")
    
    logger.info(f"Fetched {len(updates)} refusal records")
    return updates


@step(enable_cache=True)
def fetch_rulings_updates(
    lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Step 5: Fetch CBP rulings updates.
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of new rulings
    """
    logger.info(f"Fetching CBP rulings from last {lookback_days} days...")
    
    rulings_tool = RulingsTool()
    
    # Sample keywords to search
    keywords = ["electronics", "textiles", "machinery", "furniture"]
    
    updates = []
    for keyword in keywords:
        try:
            result = rulings_tool.run(search_term=keyword)
            
            if result and result.get("rulings"):
                for ruling in result["rulings"][:3]:  # Top 3 per keyword
                    updates.append({
                        "ruling_number": ruling.get("ruling_number", ""),
                        "description": ruling.get("description", ""),
                        "hts_code": ruling.get("hts_code", ""),
                        "date": ruling.get("date", ""),
                        "keyword": keyword,
                        "fetched_at": datetime.utcnow().isoformat()
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch rulings for {keyword}: {e}")
    
    logger.info(f"Fetched {len(updates)} rulings")
    return updates


@step
def ingest_to_collections(
    hts_updates: List[Dict[str, Any]],
    sanctions_updates: List[Dict[str, Any]],
    refusals_updates: List[Dict[str, Any]],
    rulings_updates: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Step 6: Ingest all updates into ChromaDB collections.
    
    Args:
        hts_updates: HTS updates to ingest
        sanctions_updates: Sanctions updates to ingest
        refusals_updates: Refusals updates to ingest
        rulings_updates: Rulings updates to ingest
        
    Returns:
        Count of documents added per collection
    """
    logger.info("Ingesting updates into collections...")
    
    counts = {
        "hts_notes": 0,
        "rulings": 0,
        "refusals": 0,
        "policy": 0
    }
    
    # Ingest HTS notes
    hts_collection = compliance_collections.get_collection(compliance_collections.HTS_NOTES)
    for update in hts_updates:
        try:
            content = f"HTS Code: {update['hts_code']}\n"
            content += f"Duty Rate: {update['duty_rate']}\n"
            content += f"Notes: {', '.join(update.get('notes', []))}"
            
            hts_collection.add_texts(
                texts=[content],
                metadatas=[{
                    "hts_code": update["hts_code"],
                    "duty_rate": update["duty_rate"],
                    "source": "usitc",
                    "ingested_at": datetime.utcnow().isoformat()
                }],
                ids=[f"hts_{update['hts_code']}_{update['fetched_at']}"]
            )
            counts["hts_notes"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest HTS update: {e}")
    
    # Ingest rulings
    rulings_collection = compliance_collections.get_collection(compliance_collections.RULINGS)
    for ruling in rulings_updates:
        try:
            content = f"Ruling: {ruling['ruling_number']}\n"
            content += f"Description: {ruling['description']}\n"
            content += f"HTS Code: {ruling['hts_code']}"
            
            rulings_collection.add_texts(
                texts=[content],
                metadatas=[{
                    "ruling_number": ruling["ruling_number"],
                    "hts_code": ruling["hts_code"],
                    "keyword": ruling["keyword"],
                    "source": "cbp_cross",
                    "ingested_at": datetime.utcnow().isoformat()
                }],
                ids=[f"ruling_{ruling['ruling_number']}_{ruling['fetched_at']}"]
            )
            counts["rulings"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest ruling: {e}")
    
    # Ingest refusals
    refusals_collection = compliance_collections.get_collection(compliance_collections.REFUSALS)
    for refusal in refusals_updates:
        try:
            content = f"Country: {refusal['country']}\n"
            content += f"Product: {refusal['product']}\n"
            content += f"Reason: {refusal['reason']}"
            
            refusals_collection.add_texts(
                texts=[content],
                metadatas=[{
                    "country": refusal["country"],
                    "product": refusal["product"],
                    "reason": refusal["reason"],
                    "source": "fda_fsis",
                    "ingested_at": datetime.utcnow().isoformat()
                }],
                ids=[f"refusal_{refusal['country']}_{refusal['fetched_at']}"]
            )
            counts["refusals"] += 1
        except Exception as e:
            logger.error(f"Failed to ingest refusal: {e}")
    
    logger.info(f"Ingestion complete: {counts}")
    return counts


@step
def generate_ingestion_report(
    counts: Dict[str, int]
) -> Dict[str, Any]:
    """
    Step 7: Generate ingestion summary report.
    
    Args:
        counts: Document counts per collection
        
    Returns:
        Ingestion report
    """
    report = {
        "ingestion_date": datetime.utcnow().isoformat(),
        "total_documents": sum(counts.values()),
        "by_collection": counts,
        "status": "success" if sum(counts.values()) > 0 else "no_updates"
    }
    
    logger.info(f"Ingestion report: {report}")
    return report


@pipeline
def compliance_ingestion_pipeline(
    lookback_days: int = 7
):
    """
    Daily compliance data ingestion pipeline.
    
    Steps:
    1. Initialize collections
    2. Fetch HTS updates
    3. Fetch sanctions updates
    4. Fetch refusals updates
    5. Fetch rulings updates
    6. Ingest all to ChromaDB
    7. Generate report
    
    Args:
        lookback_days: Number of days to look back for updates
    """
    # Initialize
    collections_ready = initialize_collections()
    
    # Fetch updates from all sources (can run in parallel)
    hts_updates = fetch_hts_updates(lookback_days=lookback_days)
    sanctions_updates = fetch_sanctions_updates(lookback_days=lookback_days)
    refusals_updates = fetch_refusals_updates(lookback_days=lookback_days)
    rulings_updates = fetch_rulings_updates(lookback_days=lookback_days)
    
    # Ingest (depends on all fetches)
    counts = ingest_to_collections(
        hts_updates=hts_updates,
        sanctions_updates=sanctions_updates,
        refusals_updates=refusals_updates,
        rulings_updates=rulings_updates
    )
    
    # Report
    report = generate_ingestion_report(counts=counts)
    
    return report
