"""Simple Compliance LangGraph implementation for MVP."""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from loguru import logger

from acc_llamaindex.domain.tools import HTSTool, SanctionsTool, RefusalsTool, RulingsTool
from acc_llamaindex.application.memory_service.mem0_client import mem0_client
from acc_llamaindex.infrastructure.db.compliance_collections import compliance_collections
from acc_llamaindex.domain.compliance.compliance_event import Tile, SnapshotResponse, Evidence
from acc_llamaindex.domain.compliance.enums import TileStatus, RiskLevel
from acc_llamaindex.infrastructure.llm_providers.openai_provider import OpenAIProvider


class ComplianceState(TypedDict):
    """Simple state for compliance graph MVP."""
    # Input
    client_id: str
    sku_id: str
    lane_id: str
    question: Optional[str]  # For Q&A mode
    
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
    answer: Optional[str]  # For Q&A mode


def execute_tools_node(state: ComplianceState) -> ComplianceState:
    """Execute compliance tools sequentially."""
    logger.info(f"Executing compliance tools for SKU: {state['sku_id']}")
    
    # Simple default values for MVP
    hts_code = "8517.12.00"  # Default for testing
    party_name = "Test Supplier Co."
    
    # Initialize tools
    hts_tool = HTSTool()
    sanctions_tool = SanctionsTool()
    refusals_tool = RefusalsTool()
    rulings_tool = RulingsTool()
    
    # Execute tools sequentially
    try:
        hts_result = hts_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
        state['hts_results'] = {
            'success': hts_result.success,
            'data': hts_result.data,
            'error': hts_result.error
        }
    except Exception as e:
        logger.error(f"HTS tool failed: {e}")
        state['hts_results'] = {'success': False, 'error': str(e)}
    
    try:
        sanctions_result = sanctions_tool.run(party_name=party_name, lane_id=state['lane_id'])
        state['sanctions_results'] = {
            'success': sanctions_result.success,
            'data': sanctions_result.data,
            'error': sanctions_result.error
        }
    except Exception as e:
        logger.error(f"Sanctions tool failed: {e}")
        state['sanctions_results'] = {'success': False, 'error': str(e)}
    
    try:
        refusals_result = refusals_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
        state['refusals_results'] = {
            'success': refusals_result.success,
            'data': refusals_result.data,
            'error': refusals_result.error
        }
    except Exception as e:
        logger.error(f"Refusals tool failed: {e}")
        state['refusals_results'] = {'success': False, 'error': str(e)}
    
    try:
        rulings_result = rulings_tool.run(hts_code=hts_code, lane_id=state['lane_id'])
        state['rulings_results'] = {
            'success': rulings_result.success,
            'data': rulings_result.data,
            'error': rulings_result.error
        }
    except Exception as e:
        logger.error(f"Rulings tool failed: {e}")
        state['rulings_results'] = {'success': False, 'error': str(e)}
    
    logger.info("Tool execution complete")
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
        hts_code = "8517.12.00"  # Default for MVP
        
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
    """Generate simple compliance snapshot."""
    logger.info("Generating compliance snapshot")
    
    tiles = {}
    citations = []
    
    # HTS Tile
    if state.get("hts_results", {}).get("success"):
        hts_data = state["hts_results"].get("data", {})
        
        tiles["hts"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"HTS {hts_data.get('hts_code', 'N/A')} - {hts_data.get('duty_rate', 'N/A')}",
            details_md=f"**Description:** {hts_data.get('description', 'N/A')}\n**Duty Rate:** {hts_data.get('duty_rate', 'N/A')}"
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
        
        status = TileStatus.ACTION_REQUIRED if matches_found else TileStatus.CLEAR
        headline = "Sanctions Issues Found" if matches_found else "No Sanctions Issues"
        
        tiles["sanctions"] = Tile(
            status=status,
            headline=headline,
            details_md=f"**Matches Found:** {sanctions_data.get('match_count', 0)}"
        ).model_dump()
    
    # Refusals Tile
    if state.get("refusals_results", {}).get("success"):
        refusals_data = state["refusals_results"].get("data", {})
        total_refusals = refusals_data.get("total_refusals", 0)
        
        status = TileStatus.ATTENTION if total_refusals > 0 else TileStatus.CLEAR
        headline = f"{total_refusals} Import Refusals" if total_refusals > 0 else "No Recent Refusals"
        
        tiles["health_safety"] = Tile(
            status=status,
            headline=headline,
            details_md=f"**Total Refusals:** {total_refusals}"
        ).model_dump()
    
    # Rulings Tile
    if state.get("rulings_results", {}).get("success"):
        rulings_data = state["rulings_results"].get("data", {})
        total_rulings = rulings_data.get("total_rulings", 0)
        
        tiles["rulings"] = Tile(
            status=TileStatus.CLEAR,
            headline=f"{total_rulings} Relevant Rulings",
            details_md=f"**Relevant Rulings:** {total_rulings}"
        ).model_dump()
    
    # Create simple snapshot
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
    
    state["snapshot"] = snapshot
    state["citations"] = citations
    
    logger.info("Snapshot generation complete")
    return state


def answer_question_node(state: ComplianceState) -> ComplianceState:
    """Answer compliance questions using simple RAG."""
    question = state.get('question')
    if not question:
        return state
    
    logger.info(f"Answering question: {question}")
    
    try:
        # Simple context preparation
        context_parts = []
        
        # Add tool results to context
        if state.get("hts_results", {}).get("success"):
            hts_data = state["hts_results"]["data"]
            context_parts.append(f"HTS: {hts_data.get('hts_code')} - {hts_data.get('description')}")
        
        if state.get("sanctions_results", {}).get("success"):
            sanctions_data = state["sanctions_results"]["data"]
            context_parts.append(f"Sanctions: {sanctions_data.get('match_count', 0)} matches found")
        
        # Add RAG context
        for doc in state.get("rag_context", []):
            context_parts.append(doc.get("content", "")[:200])
        
        context = "\n".join(context_parts)
        
        # Generate simple answer using LLM
        llm_provider = OpenAIProvider()
        
        prompt = f"""Based on the following compliance information, answer this question: {question}

Context:
{context}

Provide a clear, concise answer based on the available information."""
        
        answer = llm_provider.generate_response(
            system_prompt="You are a compliance expert. Provide accurate answers based on the given context.",
            user_prompt=prompt,
            max_tokens=500,
            temperature=0.1
        )
        
        state['answer'] = answer
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        state['answer'] = "I apologize, but I encountered an error while processing your question."
    
    return state


def build_compliance_graph() -> StateGraph:
    """Build simple compliance graph for MVP."""
    graph = StateGraph(ComplianceState)
    
    # Add nodes
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_snapshot", generate_snapshot_node)
    graph.add_node("answer_question", answer_question_node)
    
    # Simple routing based on whether it's Q&A or snapshot mode
    def route_after_context(state: ComplianceState) -> str:
        """Route to question answering if question is present, otherwise to snapshot."""
        if state.get('question'):
            return "answer_question"
        else:
            return "generate_snapshot"
    
    # Define simple flow
    graph.set_entry_point("execute_tools")
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


