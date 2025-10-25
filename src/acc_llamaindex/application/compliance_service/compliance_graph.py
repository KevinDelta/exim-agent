"""Compliance LangGraph implementation."""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from loguru import logger

from acc_llamaindex.domain.tools import HTSTool, SanctionsTool, RefusalsTool, RulingsTool
from acc_llamaindex.application.memory_service.mem0_client import mem0_client
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.domain.compliance.compliance_event import Tile, SnapshotResponse, Evidence
from acc_llamaindex.domain.compliance.enums import TileStatus


class ComplianceState(TypedDict):
    """State for compliance graph."""
    # Input
    client_id: str
    sku_id: str
    lane_id: str
    
    # Context
    client_context: Dict[str, Any]
    sku_metadata: Dict[str, Any]
    
    # Tool results
    hts_results: Dict[str, Any]
    sanctions_results: Dict[str, Any]
    refusals_results: Dict[str, Any]
    rulings_results: Dict[str, Any]
    
    # RAG context
    rag_context: List[Dict[str, Any]]
    
    # Output
    snapshot: Dict[str, Any]
    citations: List[Evidence]


def load_client_context(state: ComplianceState) -> ComplianceState:
    """Load client profile and SKU metadata from mem0."""
    logger.info(f"Loading context for client: {state['client_id']}, SKU: {state['sku_id']}")
    
    if not mem0_client.is_enabled():
        logger.warning("mem0 not enabled")
        state["client_context"] = {}
        state["sku_metadata"] = {}
        return state
    
    # Query mem0 for client profile
    client_memories = mem0_client.search(
        query=f"client {state['client_id']} profile",
        user_id=state['client_id'],
        limit=5
    )
    
    # Query for SKU metadata
    sku_memories = mem0_client.search(
        query=f"SKU {state['sku_id']} details",
        user_id=state['client_id'],
        limit=5
    )
    
    state["client_context"] = {"memories": client_memories if isinstance(client_memories, list) else client_memories.get('results', [])}
    state["sku_metadata"] = {"memories": sku_memories if isinstance(sku_memories, list) else sku_memories.get('results', [])}
    
    logger.info(f"Loaded {len(state['client_context'].get('memories', []))} client memories")
    return state


def search_hts_node(state: ComplianceState) -> ComplianceState:
    """Search HTS code."""
    logger.info(f"Searching HTS for SKU: {state['sku_id']}")
    
    # Extract HTS code from SKU metadata (or default)
    hts_code = "8517.12.00"  # Mock - in production, extract from sku_metadata
    
    hts_tool = HTSTool()
    result = hts_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
    
    state["hts_results"] = result
    logger.info(f"HTS search complete: {result.get('success', False)}")
    return state


def screen_sanctions_node(state: ComplianceState) -> ComplianceState:
    """Screen for sanctions."""
    logger.info(f"Screening sanctions for lane: {state['lane_id']}")
    
    # Mock party name - in production, extract from lane/supplier data
    party_name = "Test Supplier Co."
    
    sanctions_tool = SanctionsTool()
    result = sanctions_tool.run(party_name=party_name, lane_id=state['lane_id'])
    
    state["sanctions_results"] = result
    logger.info(f"Sanctions screening complete: {result.get('success', False)}")
    return state


def fetch_refusals_node(state: ComplianceState) -> ComplianceState:
    """Fetch import refusals."""
    logger.info(f"Fetching refusals for SKU: {state['sku_id']}")
    
    hts_code = "8517.12.00"  # Mock
    
    refusals_tool = RefusalsTool()
    result = refusals_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
    
    state["refusals_results"] = result
    logger.info(f"Refusals fetch complete: {result.get('success', False)}")
    return state


def find_rulings_node(state: ComplianceState) -> ComplianceState:
    """Find CBP rulings."""
    logger.info(f"Finding rulings for SKU: {state['sku_id']}")
    
    hts_code = "8517.12.00"  # Mock
    
    rulings_tool = RulingsTool()
    result = rulings_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
    
    state["rulings_results"] = result
    logger.info(f"Rulings search complete: {result.get('success', False)}")
    return state


def reason_compliance_node(state: ComplianceState) -> ComplianceState:
    """Synthesize snapshot from all tool results."""
    logger.info("Generating compliance snapshot")
    
    tiles = {}
    citations = []
    
    # HTS Tile
    if state.get("hts_results", {}).get("success"):
        hts_data = state["hts_results"].get("data", {})
        tiles["hts"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"HTS {hts_data.get('hts_code', 'N/A')} - {hts_data.get('duty_rate', 'N/A')}",
            details_md=f"**Description:** {hts_data.get('description', 'N/A')}\n\n**Duty Rate:** {hts_data.get('duty_rate', 'N/A')}"
        ).model_dump()
        
        citations.append(Evidence(
            source="USITC HTS Database",
            url=hts_data.get("source_url", ""),
            snippet=hts_data.get("description", ""),
            last_updated=hts_data.get("last_updated", "")
        ))
    
    # Sanctions Tile 
    if state.get("sanctions_results", {}).get("success"):
        sanctions_data = state["sanctions_results"].get("data", {})
        matches_found = sanctions_data.get("matches_found", False)
        
        tiles["sanctions"] = Tile(
            status=TileStatus.ATTENTION if matches_found else TileStatus.CLEAR,
            headline="Sanctions Alert" if matches_found else "No Sanctions Issues",
            details_md="**Matches found:** " + str(sanctions_data.get("match_count", 0))
        ).model_dump()
    
    # Refusals Tile
    if state.get("refusals_results", {}).get("success"):
        refusals_data = state["refusals_results"].get("data", {})
        total_refusals = refusals_data.get("total_refusals", 0)
        
        tiles["health_safety"] = Tile(
            status=TileStatus.ATTENTION if total_refusals > 0 else TileStatus.CLEAR,
            headline=f"{total_refusals} Import Refusals" if total_refusals > 0 else "No Recent Refusals",
            details_md=f"FDA: {refusals_data.get('fda_refusals', 0)}, FSIS: {refusals_data.get('fsis_refusals', 0)}"
        ).model_dump()
    
    # Rulings Tile
    if state.get("rulings_results", {}).get("success"):
        rulings_data = state["rulings_results"].get("data", {})
        total_rulings = rulings_data.get("total_rulings", 0)
        
        tiles["rulings"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"{total_rulings} Relevant Rulings",
            details_md=f"Found {total_rulings} CBP classification rulings"
        ).model_dump()
    
    snapshot = SnapshotResponse(
        client_id=state["client_id"],
        sku_id=state["sku_id"],
        lane_id=state["lane_id"],
        tiles=tiles,
        sources=[c.model_dump() for c in citations]
    ).model_dump()
    
    state["snapshot"] = snapshot
    state["citations"] = citations
    
    logger.info("Snapshot generation complete")
    return state


def build_compliance_graph() -> StateGraph:
    """Build and compile the compliance graph."""
    graph = StateGraph(ComplianceState)
    
    # Add nodes
    graph.add_node("load_context", load_client_context)
    graph.add_node("search_hts", search_hts_node)
    graph.add_node("screen_sanctions", screen_sanctions_node)
    graph.add_node("fetch_refusals", fetch_refusals_node)
    graph.add_node("find_rulings", find_rulings_node)
    graph.add_node("reason", reason_compliance_node)
    
    # Define flow
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "search_hts")
    graph.add_edge("search_hts", "screen_sanctions")
    graph.add_edge("screen_sanctions", "fetch_refusals")
    graph.add_edge("fetch_refusals", "find_rulings")
    graph.add_edge("find_rulings", "reason")
    graph.add_edge("reason", END)
    
    return graph.compile()
