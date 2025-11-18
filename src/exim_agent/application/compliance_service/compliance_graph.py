"""Simple Compliance LangGraph implementation for MVP."""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from loguru import logger

from exim_agent.domain.tools import HTSTool, SanctionsTool, RefusalsTool, RulingsTool
from exim_agent.application.memory_service.mem0_client import mem0_client
from exim_agent.infrastructure.db.compliance_collections import compliance_collections
from exim_agent.domain.compliance.compliance_event import Tile, SnapshotResponse, Evidence
from exim_agent.domain.compliance.enums import TileStatus, RiskLevel

from exim_agent.infrastructure.llm_providers.langchain_provider import get_llm

# Safe default HTS code when none provided
DEFAULT_HTS_CODE = "8517.12.00"


class ComplianceState(TypedDict):
    """Minimal state for compliance graph with clear field purposes.
    
    Fields:
        client_id: Required client identifier for compliance context
        sku_id: Required SKU identifier for product being checked
        lane_id: Required trade lane identifier (origin-destination pair)
        question: Optional question for Q&A mode (None triggers snapshot mode)
        
        hts_result: HTS classification tool result with {success, data, error} structure
        sanctions_result: Sanctions screening tool result with {success, data, error} structure
        refusals_result: Import refusals tool result with {success, data, error} structure
        rulings_result: CBP rulings tool result with {success, data, error} structure
        
        rag_context: Retrieved document context from ChromaDB for grounding responses
        
        snapshot: Generated compliance snapshot (None in Q&A mode)
        answer: Generated answer to question (None in snapshot mode)
        citations: Source citations with URLs and timestamps
    """
    # Required inputs
    client_id: str
    sku_id: str
    lane_id: str
    
    # Optional mode selector
    question: Optional[str]
    
    # Tool results (singular form, consistent structure)
    hts_result: Dict[str, Any]
    sanctions_result: Dict[str, Any]
    refusals_result: Dict[str, Any]
    rulings_result: Dict[str, Any]
    
    # RAG context
    rag_context: List[Dict[str, Any]]
    
    # Outputs
    snapshot: Optional[Dict[str, Any]]
    answer: Optional[str]
    citations: List[Evidence]


def validate_inputs_node(state: ComplianceState) -> ComplianceState:
    """Validate required inputs are present.
    
    Checks for presence of client_id, sku_id, and lane_id.
    Returns structured error in snapshot/answer if fields are missing.
    """
    missing = []
    
    if not state.get("client_id"):
        missing.append("client_id")
    if not state.get("sku_id"):
        missing.append("sku_id")
    if not state.get("lane_id"):
        missing.append("lane_id")
    
    if missing:
        error_msg = f"Missing required fields: {', '.join(missing)}"
        logger.error(f"Input validation failed: {error_msg}")
        
        # Set error state for both modes
        state["snapshot"] = {
            "error": error_msg,
            "client_id": state.get("client_id", ""),
            "sku_id": state.get("sku_id", ""),
            "lane_id": state.get("lane_id", ""),
            "tiles": {},
            "active_alerts_count": 0,
            "sources": []
        }
        state["answer"] = error_msg
        state["citations"] = []
        
        # Initialize empty tool results
        state["hts_result"] = {"success": False, "data": {}, "error": error_msg}
        state["sanctions_result"] = {"success": False, "data": {}, "error": error_msg}
        state["refusals_result"] = {"success": False, "data": {}, "error": error_msg}
        state["rulings_result"] = {"success": False, "data": {}, "error": error_msg}
        state["rag_context"] = []
    else:
        logger.info(f"Input validation passed for client_id={state['client_id']}, sku_id={state['sku_id']}, lane_id={state['lane_id']}")
    
    return state


def execute_tools_node(state: ComplianceState) -> ComplianceState:
    """Execute compliance tools sequentially with fail-soft behavior.
    
    Each tool is wrapped in individual try-except blocks.
    Tool errors are captured in result structure without raising exceptions.
    Continues executing remaining tools even if one fails.
    """
    client_id = state['client_id'] 
    sku_id = state['sku_id']
    lane_id = state['lane_id']
     
    logger.info(f"Executing compliance tools for client_id={client_id}, sku_id={sku_id}, lane_id={lane_id}")
    
    # Get HTS code from state with fallback
    hts_code = state.get('hts_code') or DEFAULT_HTS_CODE
    party_name = state.get('party_name', 'Test Supplier Co.')
    
    # HTS Tool - fail-soft execution
    try:
        logger.debug(f"Executing HTS tool with code: {hts_code}")
        hts_result = HTSTool().run(hts_code=hts_code, lane_id=state['lane_id'])
        state['hts_result'] = {
            'success': hts_result.success,
            'data': hts_result.data if hts_result.success else {},
            'error': hts_result.error
        }
        if hts_result.success:
            logger.info(f"HTS tool succeeded: {hts_result.data.get('hts_code', 'N/A')}")
        else:
            logger.warning(f"HTS tool returned failure: {hts_result.error}")
    except Exception as e:
        logger.error(f"HTS tool exception (continuing with remaining tools): {e}")
        state['hts_result'] = {'success': False, 'data': {}, 'error': str(e)}
    
    # Sanctions Tool - fail-soft execution
    try:
        logger.debug(f"Executing Sanctions tool for party: {party_name}")
        sanctions_result = SanctionsTool().run(party_name=party_name, lane_id=state['lane_id'])
        state['sanctions_result'] = {
            'success': sanctions_result.success,
            'data': sanctions_result.data if sanctions_result.success else {},
            'error': sanctions_result.error
        }
        if sanctions_result.success:
            logger.info(f"Sanctions tool succeeded: {sanctions_result.data.get('match_count', 0)} matches")
        else:
            logger.warning(f"Sanctions tool returned failure: {sanctions_result.error}")
    except Exception as e:
        logger.error(f"Sanctions tool exception (continuing with remaining tools): {e}", exc_info=True)
        state['sanctions_result'] = {'success': False, 'data': {}, 'error': str(e)}
    
    # Refusals Tool - fail-soft execution
    try:
        logger.debug(f"Executing Refusals tool with HTS code: {hts_code}")
        refusals_result = RefusalsTool().run(hts_code=hts_code, lane_id=state['lane_id'])
        state['refusals_result'] = {
            'success': refusals_result.success,
            'data': refusals_result.data if refusals_result.success else {},
            'error': refusals_result.error
        }
        if refusals_result.success:
            logger.info(f"Refusals tool succeeded: {refusals_result.data.get('total_refusals', 0)} refusals")
        else:
            logger.warning(f"Refusals tool returned failure: {refusals_result.error}")
    except Exception as e:
        logger.error(f"Refusals tool exception (continuing with remaining tools): {e}", exc_info=True)
        state['refusals_result'] = {'success': False, 'data': {}, 'error': str(e)}
    
    # Rulings Tool - fail-soft execution
    try:
        logger.debug(f"Executing Rulings tool with HTS code: {hts_code}")
        rulings_result = RulingsTool().run(hts_code=hts_code, lane_id=state['lane_id'])
        state['rulings_result'] = {
            'success': rulings_result.success,
            'data': rulings_result.data if rulings_result.success else {},
            'error': rulings_result.error
        }
        if rulings_result.success:
            logger.info(f"Rulings tool succeeded: {rulings_result.data.get('total_rulings', 0)} rulings")
        else:
            logger.warning(f"Rulings tool returned failure: {rulings_result.error}")
    except Exception as e:
        logger.error(f"Rulings tool exception (continuing with remaining tools): {e}", exc_info=True)
        state['rulings_result'] = {'success': False, 'data': {}, 'error': str(e)}
    
    # Log summary of tool execution
    success_count = sum(1 for result in [
        state['hts_result'], state['sanctions_result'], 
        state['refusals_result'], state['rulings_result']
    ] if result.get('success'))
    
    logger.info(f"Tool execution complete: {success_count}/4 tools succeeded")
    return state





def retrieve_context_node(state: ComplianceState) -> ComplianceState:
    """Retrieve basic context from ChromaDB."""
    logger.info(f"Retrieving context for SKU: {state['sku_id']}")
    
    rag_context = []
    
    try:
        # Initialize collections if needed
        if not compliance_collections._initialized:
            compliance_collections.initialize()
        
        # Simple context retrieval - just get some relevant docs
        hts_code = state.get('hts_code', DEFAULT_HTS_CODE)
        
        # Search for relevant documents
        hts_notes = compliance_collections.search_hts_notes(
            query=f"HTS {hts_code}",
            hts_code=hts_code,
            limit=2
        )
        rag_context.extend([{"type": "hts_note", **note} for note in hts_notes])
        
        logger.info(f"Retrieved {len(rag_context)} context documents")
        
    except Exception as e:
        logger.warning(f"Context retrieval failed: {e}")
        rag_context = []
    
    state["rag_context"] = rag_context
    return state


def generate_snapshot_node(state: ComplianceState) -> ComplianceState:
    """Generate compliance snapshot even with partial tool results.
    
    Generates tiles for all tools, marking failed ones with "error" status.
    Calculates alert count excluding error tiles.
    Includes citations only from successful tools.
    """
    logger.info("Generating compliance snapshot with partial results support")
    
    tiles: Dict[str, Dict[str, Any]] = {}
    citations = []
    
    # HTS Tile - handle both success and failure
    hts = state.get("hts_result", {})
    if hts.get("success"):
        data = hts.get("data", {})
        
        tiles["hts"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"HTS {data.get('hts_code', 'N/A')} - {data.get('duty_rate', 'N/A')}",
            details_md=f"**Description:** {data.get('description', 'N/A')}\n**Duty Rate:** {data.get('duty_rate', 'N/A')}"
        ).model_dump()
        
        citations.append(Evidence(
            source="USITC HTS Database",
            url=data.get("source_url", ""),
            snippet=data.get("description", ""),
            last_updated=data.get("last_updated", "")
        ))
    else:
        # Failed tile with error status
        error_msg = hts.get("error", "Unknown error")
        tiles["hts"] = {
            "status": "error",
            "headline": "HTS Data Unavailable",
            "details_md": f"**Error:** {error_msg}"
        }
        logger.warning(f"HTS tile marked as error: {error_msg}")
    
    # Sanctions Tile - handle both success and failure
    sanctions = state.get("sanctions_result", {})
    if sanctions.get("success"):
        data = sanctions.get("data", {})
        matches_found = data.get("matches_found", False)
        
        status = TileStatus.ACTION_REQUIRED if matches_found else TileStatus.CLEAR
        headline = "Sanctions Issues Found" if matches_found else "No Sanctions Issues"
        
        tiles["sanctions"] = Tile(
            status=status,
            headline=headline,
            details_md=f"**Matches Found:** {data.get('match_count', 0)}"
        ).model_dump()
    else:
        # Failed tile with error status
        error_msg = sanctions.get("error", "Unknown error")
        tiles["sanctions"] = {
            "status": "error",
            "headline": "Sanctions Check Unavailable",
            "details_md": f"**Error:** {error_msg}"
        }
        logger.warning(f"Sanctions tile marked as error: {error_msg}")
    
    # Refusals Tile - handle both success and failure
    refusals = state.get("refusals_result", {})
    if refusals.get("success"):
        data = refusals.get("data", {})
        total_refusals = data.get("total_refusals", 0)
        
        status = TileStatus.ATTENTION if total_refusals > 0 else TileStatus.CLEAR
        headline = f"{total_refusals} Import Refusals" if total_refusals > 0 else "No Recent Refusals"
        
        tiles["health_safety"] = Tile(
            status=status,
            headline=headline,
            details_md=f"**Total Refusals:** {total_refusals}"
        ).model_dump()
    else:
        # Failed tile with error status
        error_msg = refusals.get("error", "Unknown error")
        tiles["health_safety"] = {
            "status": "error",
            "headline": "Refusal Data Unavailable",
            "details_md": f"**Error:** {error_msg}"
        }
        logger.warning(f"Refusals tile marked as error: {error_msg}")
    
    # Rulings Tile - handle both success and failure
    rulings = state.get("rulings_result", {})
    if rulings.get("success"):
        data = rulings.get("data", {})
        total_rulings = data.get("total_rulings", 0)
        
        tiles["rulings"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"{total_rulings} Relevant Rulings",
            details_md=f"**Relevant Rulings:** {total_rulings}"
        ).model_dump()
    else:
        # Failed tile with error status
        error_msg = rulings.get("error", "Unknown error")
        tiles["rulings"] = {
            "status": "error",
            "headline": "Rulings Data Unavailable",
            "details_md": f"**Error:** {error_msg}"
        }
        logger.warning(f"Rulings tile marked as error: {error_msg}")
    
    # Create snapshot with partial results
    snapshot = SnapshotResponse(
        client_id=state["client_id"],
        sku_id=state["sku_id"],
        lane_id=state["lane_id"],
        tiles=tiles,
        overall_risk_level=RiskLevel.LOW.value,
        risk_score=0.1,
        processing_time_ms=1000,
        sources=[c.model_dump() for c in citations]
    ).model_dump()
    
    # Normalize tile keys and statuses for frontend expectations
    tile_key_map = {
        "hts": "hts_classification",
        "sanctions": "sanctions_screening",
        "health_safety": "refusal_history",
        "rulings": "cbp_rulings",
    }
    normalized_tiles: Dict[str, Dict[str, Any]] = {}
    for raw_key, tile in snapshot["tiles"].items():
        normalized_key = tile_key_map.get(raw_key, raw_key)
        normalized_tile = dict(tile)
        status = normalized_tile.get("status")
        if status == TileStatus.ACTION_REQUIRED:
            normalized_tile["status"] = "action"
        normalized_tiles[normalized_key] = normalized_tile
    snapshot["tiles"] = normalized_tiles
    
    # Calculate alert count excluding error tiles (only attention/action count as alerts)
    snapshot["active_alerts_count"] = sum(
        1 for tile in normalized_tiles.values() 
        if tile.get("status") in {"attention", "action"}
    )
    
    # Log summary
    error_count = sum(1 for tile in normalized_tiles.values() if tile.get("status") == "error")
    logger.info(f"Snapshot generated: {len(normalized_tiles)} tiles, {snapshot['active_alerts_count']} alerts, {error_count} errors")
    
    state["snapshot"] = snapshot
    state["citations"] = citations
    
    return state


def answer_question_node(state: ComplianceState) -> ComplianceState:
    """Answer compliance questions with fail-soft behavior.
    
    Includes only successful tool results in context.
    Acknowledges limited information when tools fail.
    Returns user-friendly error message on LLM failures.
    """
    question = state.get('question')
    if not question:
        return state
    
    logger.info(f"Answering question: {question}")
    
    try:
        # Prepare context from successful tool results only
        context_parts = []
        available_sources = []
        
        # Add HTS data if available
        if state.get("hts_result", {}).get("success"):
            hts_data = state["hts_result"]["data"]
            context_parts.append(f"HTS Classification: {hts_data.get('hts_code')} - {hts_data.get('description')}")
            context_parts.append(f"Duty Rate: {hts_data.get('duty_rate', 'N/A')}")
            available_sources.append("HTS")
        
        # Add Sanctions data if available
        if state.get("sanctions_result", {}).get("success"):
            sanctions_data = state["sanctions_result"]["data"]
            match_count = sanctions_data.get('match_count', 0)
            context_parts.append(f"Sanctions Screening: {match_count} matches found")
            available_sources.append("Sanctions")
        
        # Add Refusals data if available
        if state.get("refusals_result", {}).get("success"):
            refusals_data = state["refusals_result"]["data"]
            total_refusals = refusals_data.get('total_refusals', 0)
            context_parts.append(f"Import Refusals: {total_refusals} recent refusals")
            available_sources.append("Refusals")
        
        # Add Rulings data if available
        if state.get("rulings_result", {}).get("success"):
            rulings_data = state["rulings_result"]["data"]
            total_rulings = rulings_data.get('total_rulings', 0)
            context_parts.append(f"CBP Rulings: {total_rulings} relevant rulings")
            available_sources.append("Rulings")
        
        # Add RAG context if available
        for doc in state.get("rag_context", []):
            content = doc.get("content", "")
            if content:
                context_parts.append(content[:200])
                available_sources.append("Documents")
        
        # Check if we have any context
        if not context_parts:
            logger.warning("No successful tool results available for Q&A")
            state['answer'] = (
                "I apologize, but I don't have enough information to answer your question. "
                "All compliance data sources are currently unavailable."
            )
            return state
        
        context = "\n".join(context_parts)
        
        # Build prompt with acknowledgment of limited information if needed
        failed_tools = []
        if not state.get("hts_result", {}).get("success"):
            failed_tools.append("HTS")
        if not state.get("sanctions_result", {}).get("success"):
            failed_tools.append("Sanctions")
        if not state.get("refusals_result", {}).get("success"):
            failed_tools.append("Refusals")
        if not state.get("rulings_result", {}).get("success"):
            failed_tools.append("Rulings")
        
        limitation_note = ""
        if failed_tools:
            limitation_note = f"\n\nNote: The following data sources are unavailable: {', '.join(failed_tools)}. Answer based only on available information."
        
        prompt = (
            f"Based on the following compliance information, answer this question: {question}\n\n"
            f"Available Context:\n{context}"
            f"{limitation_note}\n\n"
            f"Provide a clear, concise answer based on the available information. "
            f"If the available information is insufficient, acknowledge this limitation."
        )
        
        # Generate answer using LLM with fail-soft
        try:
            llm = get_llm()
            result = llm.invoke(prompt)
            state['answer'] = result.content
            logger.info(f"Answer generated successfully using sources: {', '.join(available_sources)}")
        except Exception as llm_error:
            logger.error(f"LLM call failed while answering question: {llm_error}", exc_info=True)
            state['answer'] = (
                "I apologize, but I encountered an error while generating an answer. "
                "Please try again or rephrase your question."
            )
        
    except Exception as e:
        logger.error(f"Unexpected error in answer_question_node: {e}", exc_info=True)
        state['answer'] = (
            "I apologize, but I encountered an unexpected error while processing your question. "
            "Please try again later."
        )
    
    return state


def build_compliance_graph() -> StateGraph:
    """Build compliance graph with input validation and fail-soft behavior."""
    graph = StateGraph(ComplianceState)
    
    # Add nodes
    graph.add_node("validate_inputs", validate_inputs_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_snapshot", generate_snapshot_node)
    graph.add_node("answer_question", answer_question_node)
    
    # Routing function to check validation status
    def route_after_validation(state: ComplianceState) -> str:
        """Skip to END if validation failed, otherwise continue to tools."""
        # Check if validation set an error in the snapshot
        snapshot = state.get("snapshot")
        if snapshot and snapshot.get("error"):
            logger.info("Validation failed, skipping to END")
            return "end"
        return "execute_tools"
    
    # Routing function for mode selection (Q&A vs snapshot)
    def route_after_context(state: ComplianceState) -> str:
        """Route to question answering if question is present, otherwise to snapshot."""
        if state.get('question'):
            return "answer_question"
        else:
            return "generate_snapshot"
    
    # Define flow with validation as first step
    graph.set_entry_point("validate_inputs")
    
    # Add conditional edge after validation
    graph.add_conditional_edges(
        "validate_inputs",
        route_after_validation,
        {
            "end": END,
            "execute_tools": "execute_tools"
        }
    )
    
    # Continue with normal flow for valid inputs
    graph.add_edge("execute_tools", "retrieve_context")
    graph.add_conditional_edges(
        "retrieve_context",
        route_after_context,
        {
            "answer_question": "answer_question",
            "generate_snapshot": "generate_snapshot"
        }
    )
    graph.add_edge("answer_question", END)
    graph.add_edge("generate_snapshot", END)
    
    return graph.compile()

compliance_graph = build_compliance_graph()
