# Chat Service

## Overview

The Chat Service provides an interactive Q&A interface for compliance questions, leveraging conversational memory, RAG (Retrieval-Augmented Generation), and the Compliance Service to deliver contextual, accurate responses.

## Purpose

- **Interactive Q&A**: Answer user questions about compliance, regulations, and trade requirements
- **Conversation Memory**: Maintain context across multiple turns using Mem0
- **Context Enhancement**: Use reranking to improve retrieval relevance
- **Quality Monitoring**: Evaluate response quality with built-in metrics
- **Session Management**: Track conversations by user and session

## Architecture

The chat service orchestrates multiple components to deliver high-quality responses:

```
User Question
    ↓
Mem0 (retrieve conversation history)
    ↓
Compliance Service (execute tools + RAG)
    ↓
Reranking Service (optimize context)
    ↓
LLM Generation (answer with citations)
    ↓
Evaluation Service (quality metrics)
    ↓
Mem0 (store interaction)
    ↓
Response to User
```

## Key Components

### ChatService (`service.py`)

Main service class for managing chat interactions.

#### `chat(user_id: str, message: str, session_id: Optional[str] = None) -> Dict`

Process a chat message and return a response with context.

**Parameters**:
- `user_id`: Unique identifier for the user
- `message`: User's question or message
- `session_id`: Optional session identifier for conversation tracking

**Returns**:
```python
{
    "success": True,
    "response": "Based on your product's HTS code...",
    "citations": [...],
    "session_id": "sess_123",
    "metadata": {
        "tokens_used": 450,
        "response_time_ms": 1250,
        "sources_retrieved": 8,
        "evaluation_score": 0.87
    }
}
```

#### `get_history(user_id: str, session_id: str, limit: int = 10) -> List[Dict]`

Retrieve conversation history for a user session.

**Returns**:
```python
[
    {
        "role": "user",
        "content": "What is the duty rate for HTS 1234.56?",
        "timestamp": "2024-01-15T10:30:00Z"
    },
    {
        "role": "assistant",
        "content": "The duty rate for HTS 1234.56 is 5%...",
        "timestamp": "2024-01-15T10:30:02Z",
        "citations": [...]
    }
]
```

### ChatGraph (`graph.py`)

LangGraph state machine for chat processing:

1. **retrieve_memory_node**: Load conversation history from Mem0
2. **route_question_node**: Determine if question requires compliance tools
3. **compliance_query_node**: Execute compliance service for domain questions
4. **general_response_node**: Handle general conversation without tools
5. **rerank_context_node**: Optimize retrieved context relevance
6. **generate_response_node**: Create final answer with LLM
7. **evaluate_response_node**: Measure response quality
8. **store_memory_node**: Save interaction to Mem0

**State Schema**:
```python
class ChatState(TypedDict):
    # Input
    user_id: str
    session_id: str
    message: str
    
    # Memory
    conversation_history: List[Dict]
    user_context: Dict[str, Any]
    
    # Processing
    requires_compliance_tools: bool
    compliance_results: Optional[Dict]
    retrieved_context: List[Dict]
    reranked_context: List[Dict]
    
    # Output
    response: str
    citations: List[Evidence]
    evaluation_metrics: Dict[str, float]
```

## Usage

### Basic Chat Interaction

```python
from exim_agent.application.chat_service import ChatService

service = ChatService()

# First message in a conversation
result = service.chat(
    user_id="user_123",
    message="What are the import requirements for electronics from China?"
)

print(f"Response: {result['response']}")
print(f"Session ID: {result['session_id']}")

# Follow-up message in same conversation
result = service.chat(
    user_id="user_123",
    message="What about the duty rates?",
    session_id=result['session_id']
)
```

### Retrieving Conversation History

```python
history = service.get_history(
    user_id="user_123",
    session_id="sess_123",
    limit=20
)

for turn in history:
    print(f"{turn['role']}: {turn['content']}")
```

### Streaming Responses (Future)

```python
# Planned feature for real-time response streaming
async for chunk in service.chat_stream(user_id="user_123", message="..."):
    print(chunk, end="", flush=True)
```

## Integration Points

### Compliance Service
- Routes compliance-specific questions to ComplianceService
- Leverages domain tools (HTS, Sanctions, Refusals, Rulings)
- Retrieves structured snapshots for detailed answers

### Memory Service (Mem0)
- **Conversation History**: Stores and retrieves chat turns
- **User Context**: Maintains user preferences and profile
- **Semantic Search**: Finds relevant past conversations
- **Storage**: Uses ChromaDB backend for vector search

### Reranking Service
- **Cross-Encoder Models**: Re-scores retrieved documents
- **Relevance Optimization**: Improves context quality
- **Configurable**: Can be disabled for faster responses
- **Top-K Selection**: Returns most relevant documents

### Evaluation Service
- **Faithfulness**: Measures answer grounding in context
- **Relevance**: Assesses context relevance to question
- **Context Precision**: Evaluates retrieval quality
- **Async Execution**: Non-blocking quality monitoring

### ChromaDB Collections
- `mem0_conversations`: Conversation memory storage
- `compliance_policy_snippets`: General compliance docs
- `compliance_hts_notes`: HTS-specific information
- `compliance_rulings`: CBP rulings database

## Performance Characteristics

- **Response Time**: 1-3 seconds for typical questions
- **Memory Retrieval**: <500ms for conversation history
- **Context Retrieval**: ~500ms for top 10 documents
- **Reranking**: +200-300ms when enabled
- **Evaluation**: Async, doesn't block response

## Configuration

Environment variables:
```bash
# LLM Provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # optional
GROQ_API_KEY=gsk_...  # optional for fast inference

# Memory
MEM0_API_KEY=xxx  # or use local mode
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Optional Features
ENABLE_RERANKING=true
ENABLE_EVALUATION=true
RERANKING_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Performance
MAX_CONTEXT_DOCS=10
RERANKING_TOP_K=5
MEMORY_SEARCH_LIMIT=5
```

## Conversation Flow Examples

### Compliance Question Flow

```
User: "What is the duty rate for HTS 8471.30.01?"
    ↓
Memory: Load user context (previous HTS queries)
    ↓
Router: Detect compliance question → route to ComplianceService
    ↓
Compliance: Execute HTSTool, retrieve HTS notes from ChromaDB
    ↓
Reranking: Score and select top 5 most relevant docs
    ↓
LLM: Generate answer with citations
    ↓
Evaluation: Score faithfulness (0.92), relevance (0.88)
    ↓
Memory: Store Q&A pair for future context
    ↓
Response: "HTS 8471.30.01 has a duty rate of 0% under MFN..."
```

### General Conversation Flow

```
User: "Thanks for your help!"
    ↓
Memory: Load conversation history
    ↓
Router: Detect general message → skip compliance tools
    ↓
LLM: Generate conversational response
    ↓
Memory: Store interaction
    ↓
Response: "You're welcome! Let me know if you have more questions."
```

## Error Handling

The service implements robust error handling:

1. **Memory Failures**: Continue without history if Mem0 unavailable
2. **Tool Failures**: Fallback to general knowledge if tools fail
3. **Reranking Failures**: Use original context if reranking fails
4. **Evaluation Failures**: Log error but return response
5. **LLM Failures**: Retry with exponential backoff

## Quality Monitoring

Built-in evaluation metrics:

- **Faithfulness**: Answer grounded in retrieved context (0-1)
- **Relevance**: Context relevance to question (0-1)
- **Context Precision**: Quality of retrieved documents (0-1)
- **Response Time**: Latency tracking for performance
- **Token Usage**: Cost monitoring for LLM calls

Metrics are logged to Supabase for historical analysis.

## Testing

Run chat service tests:
```bash
pytest tests/test_chat_service.py -v
```

Test with real LLM (requires API key):
```bash
pytest tests/test_chat_service.py -v --integration
```

## Best Practices

### For Developers

1. **Session Management**: Always pass session_id for multi-turn conversations
2. **User Context**: Use consistent user_id for personalization
3. **Error Handling**: Check `success` field before using response
4. **Rate Limiting**: Implement client-side rate limiting for API calls
5. **Streaming**: Use streaming for better UX (when available)

### For Operators

1. **Memory Cleanup**: Periodically prune old conversations (>90 days)
2. **Evaluation Monitoring**: Track quality metrics over time
3. **Cost Optimization**: Monitor token usage and adjust context limits
4. **Performance Tuning**: Disable reranking/evaluation if latency is critical
5. **Model Selection**: Use Groq for fast inference, Claude for quality

## Future Enhancements

- [ ] Streaming response support for real-time UX
- [ ] Multi-modal support (images, documents)
- [ ] Voice input/output integration
- [ ] Conversation summarization for long sessions
- [ ] Proactive suggestions based on user context
- [ ] Multi-language support
- [ ] Fine-tuned models for compliance domain

## Related Documentation

- [Compliance Service README](../compliance_service/README.md) - Snapshot generation and tool orchestration
- [Memory Service README](../memory_service/README.md) - Mem0 integration details
- [Reranking Service README](../reranking_service/README.md) - Context optimization
- [Evaluation Service README](../evaluation_service/README.md) - Quality metrics
