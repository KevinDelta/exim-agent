# Compliance Service

## Overview

The Compliance Service is the core component responsible for generating compliance snapshots and answering compliance-related questions. It orchestrates the execution of domain tools, retrieves relevant context from vector storage, and produces structured compliance assessments for SKU+Lane combinations.

## Purpose

- **Snapshot Generation**: Create point-in-time compliance status reports for product-lane combinations
- **Q&A Support**: Answer specific compliance questions using RAG (Retrieval-Augmented Generation)
- **Tool Orchestration**: Coordinate parallel execution of HTS, Sanctions, Refusals, and Rulings tools
- **Risk Assessment**: Aggregate tool results into overall risk scores and actionable insights

## Architecture

The service uses **LangGraph** to implement a state machine that processes compliance requests through multiple stages:

```yaml
Input (client_id, sku_id, lane_id, question?)
    ↓
Execute Tools (parallel)
    ↓
Retrieve Context (ChromaDB)
    ↓
Generate Snapshot OR Answer Question
    ↓
Output (snapshot/answer + citations)
```

## Key Components

### ComplianceService (`service.py`)

Main service class with two primary methods:

#### `snapshot(client_id: str, sku_id: str, lane_id: str) -> Dict`

Generates a comprehensive compliance snapshot containing:

- **Tiles**: Individual compliance aspects (HTS, sanctions, refusals, rulings)
- **Overall Risk Level**: Aggregated risk assessment (low/medium/high)
- **Risk Score**: Numerical risk value (0-100)
- **Sources**: Evidence and citations supporting the assessment

**Example Response**:

```python
{
    "success": True,
    "snapshot": {
        "tiles": {
            "hts": {
                "status": "clear",
                "risk_level": "low",
                "headline": "HTS 1234.56.78 - Standard duty rate 5%",
                "details": {...}
            },
            "sanctions": {...},
            "refusals": {...},
            "rulings": {...}
        },
        "overall_risk_level": "medium",
        "risk_score": 45.0,
        "sources": [...]
    },
    "citations": [...]
}
```

#### `ask(client_id: str, question: str, sku_id: str, lane_id: str) -> Dict`

Answers compliance questions using RAG:

- Executes relevant tools based on question context
- Retrieves supporting documents from ChromaDB
- Generates natural language answer with citations

**Example Response**:

```python
{
    "success": True,
    "answer": "Based on HTS code 1234.56.78, the duty rate is 5%...",
    "citations": [...],
    "question": "What is the duty rate for this product?"
}
```

### ComplianceGraph (`compliance_graph.py`)

LangGraph state machine with fail-soft behavior and input validation:

1. **validate_inputs_node**: Validates required fields (client_id, sku_id, lane_id)
2. **execute_tools_failsoft**: Runs domain tools sequentially with fail-soft error handling
3. **retrieve_context_node**: Fetches relevant documents from ChromaDB collections
4. **generate_snapshot_partial**: Creates structured tiles even with partial tool results
5. **answer_question_node**: Generates natural language answers with graceful degradation

**State Schema**:

```python
class ComplianceState(TypedDict):
    # Required inputs
    client_id: str
    sku_id: str
    lane_id: str
    
    # Optional mode selector
    question: Optional[str]
    
    # Tool results (singular form, consistent {success, data, error} structure)
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
```

## Usage

### Generating a Snapshot

```python
from exim_agent.application.compliance_service import ComplianceService

service = ComplianceService()
service.initialize()

result = service.snapshot(
    client_id="acme_corp",
    sku_id="WIDGET-001",
    lane_id="US-CN"
)

if result["success"]:
    snapshot = result["snapshot"]
    print(f"Risk Level: {snapshot['overall_risk_level']}")
    print(f"Risk Score: {snapshot['risk_score']}")
```

### Asking a Question

```python
result = service.ask(
    client_id="acme_corp",
    question="What are the import restrictions for this product?",
    sku_id="WIDGET-001",
    lane_id="US-CN"
)

if result["success"]:
    print(f"Answer: {result['answer']}")
    print(f"Citations: {len(result['citations'])} sources")
```

## Integration Points

### Domain Tools

- **HTSTool**: Fetches tariff classification and duty rates
- **SanctionsTool**: Checks consolidated screening lists
- **RefusalsTool**: Queries FDA/FSIS import refusals
- **RulingsTool**: Retrieves CBP customs rulings

All tools support:

- Parallel execution for performance
- Automatic fallback to mock data on API failures
- Result caching in Supabase

### ChromaDB Collections

- `compliance_policy_snippets`: General compliance documents
- `compliance_hts_notes`: HTS-specific information
- `compliance_rulings`: CBP rulings database
- `compliance_refusal_summaries`: Import refusal data

### Supabase Storage

- Tool outputs stored in `compliance_data` table
- Snapshots can be persisted for historical tracking
- Supports audit trail and compliance reporting

## Performance Characteristics

- **Snapshot Generation**: ~5-10 seconds per SKU+Lane
- **Tool Execution**: Parallel execution reduces latency by 60-70%
- **Context Retrieval**: Top 5 documents per collection (~500ms)
- **LLM Calls**: Minimal usage for tile generation (cost optimization)

## Error Handling

The service implements graceful degradation:

1. **Tool Failures**: Individual tool failures don't block snapshot generation
2. **Fallback Data**: Mock data used when APIs are unavailable
3. **Partial Results**: Snapshots generated even with incomplete tool data
4. **Logging**: All errors logged with context for debugging

## Configuration

Environment variables:

```bash
# LLM Provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # optional

# Storage
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# API Keys for Tools
CSL_API_KEY=xxx  # ITA Consolidated Screening List
```

## Testing

Run compliance service tests:

```bash
pytest tests/test_compliance_service.py -v
```

Integration tests with real APIs:

```bash
pytest tests/test_compliance_service.py -v --integration
```

## Future Enhancements

- [ ] Caching layer for frequently requested snapshots
- [ ] Streaming responses for real-time updates
- [ ] Multi-language support for international clients
- [ ] Advanced risk scoring algorithms
- [ ] Compliance trend analysis over time

## Related Documentation

- [Domain Tools README](../../domain/tools/README.md) - Tool architecture and fallback strategies
- [ZenML Pipelines README](../zenml_pipelines/README.md) - Pulse pipeline orchestration
- [Chat Service README](../chat_service/README.md) - Interactive Q&A implementation
