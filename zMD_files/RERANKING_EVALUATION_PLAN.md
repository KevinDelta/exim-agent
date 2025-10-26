# Reranking & Evaluation Implementation Plan

## Executive Summary

This plan outlines adding **Cross-Encoder reranking** and **evaluation metrics** to your LangChain v1 RAG system to improve answer quality by 20-40% and provide measurable quality metrics.

**Timeline**: 1-2 days for full implementation
**Complexity**: Low-Medium (simple, focused architecture)
**Dependencies**: 1 package (sentence-transformers)
**Approach**: Direct implementation

---

## Part 1: Understanding the Problem

### Current State

Your RAG system:

1. Retrieves documents using vector similarity (ChromaDB)
2. Generates answers using LLM
3. No quality measurement
4. No refinement of retrieved documents

### Problems to Solve

Problem 1: Retrieval Quality

- Vector similarity ≠ semantic relevance
- Top-k documents may not be the most relevant
- No way to refine initial retrieval

Problem 2: No Quality Metrics

- Can't measure if answers are accurate
- Can't detect hallucinations
- Can't track system improvements

---

## Part 2: The Solution

### Solution 1: Reranking (Improves Retrieval)

**What it does**: Takes initial retrieved documents and re-scores them using a specialized model

**How it works**:

```bash
Query: "What is LangChain v1?"

Step 1: Retrieve 20 documents (vector similarity)
  → Doc 1: score 0.85
  → Doc 2: score 0.83
  → ...
  → Doc 20: score 0.65

Step 2: Rerank to 5 documents (semantic relevance)
  → Doc 7: score 0.95 ← Better match!
  → Doc 2: score 0.91
  → Doc 1: score 0.88
  → Doc 15: score 0.82
  → Doc 3: score 0.79

Step 3: Use top 5 for generation
```

**Why it works**: Reranking models are trained specifically for relevance, not just similarity

### Solution 2: Evaluation (Measures Quality)

**What it does**: Automatically scores each RAG response on key metrics

**Metrics**:

1. **Faithfulness** (0-1): Is the answer grounded in retrieved context?
2. **Answer Relevance** (0-1): Does the answer address the question?
3. **Context Precision** (0-1): Are retrieved docs relevant?

**How it works**:

```bash
Query: "What is RAG?"
Answer: "RAG is Retrieval-Augmented Generation..."
Context: ["RAG combines...", "It uses vector databases..."]

Evaluation:
  ✓ Faithfulness: 0.92 (claims supported by context)
  ✓ Relevance: 0.88 (directly answers question)
  ✓ Context Precision: 0.80 (4/5 docs relevant)
  
Overall Score: 0.87 (Good!)
```

---

## Part 3: Architecture Design

### New Components (Lean & Focused)

```bash
src/exim_agent/
├── application/
│   ├── reranking_service/          # NEW
│   │   ├── service.py              # Main service
│   │   └── rerankers/
│   │       ├── base_reranker.py    # Interface
│   │       └── cross_encoder_reranker.py  # Local
│   │
│   └── evaluation_service/         # NEW
│       ├── service.py              # Main service
│       ├── metrics/
│       │   ├── base_metric.py      # Interface
│       │   ├── faithfulness.py
│       │   ├── relevance.py
│       │   └── context_precision.py
│       └── evaluators/
│           └── rag_evaluator.py    # Orchestrates metrics
```

### Integration Flow

**Before** (Current):

```bash
User Query → Retrieve (5 docs) → Generate → Response
```

**After** (With Reranking + Evaluation):

```bash
User Query 
  → Retrieve (20 docs) 
  → Rerank (to 5 docs) 
  → Generate 
  → Evaluate 
  → Response + Metrics
```

---

## Part 4: Implementation Gameplan

### Phase 1: Reranking Service (4 hours)

**Goal**: Add Cross-Encoder reranking capability

**Steps**:

1. **Create base reranker interface** (30 min)
   - Create `application/reranking_service/rerankers/base_reranker.py`
   - Define abstract `BaseReranker` class
   - Define `rerank()` method signature
   - Define `get_reranker_name()` method

2. **Implement Cross-Encoder reranker** (1.5 hours)
   - Create `application/reranking_service/rerankers/cross_encoder_reranker.py`
   - Implement `CrossEncoderReranker` class extending `BaseReranker`
   - Use sentence-transformers library
   - Load model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Implement `rerank()` method: takes query + docs, returns ranked docs

3. **Create reranking service** (1 hour)
   - Create `application/reranking_service/service.py`
   - Implement `RerankingService` class
   - Initialize Cross-Encoder reranker
   - Provide simple `rerank()` interface
   - Global singleton instance

4. **Update configuration** (30 min)
   - Add to `config.py`:
     - `enable_reranking: bool = True`
     - `rerank_top_k: int = 5`
     - `cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"`

5. **Test reranking** (1.5 hours)
   - Unit test: verify reranking logic
   - Integration test: test with real ChromaDB documents
   - Performance test: measure latency
   - Quality test: compare with/without reranking

**Deliverable**: Production-ready reranking service with clean architecture

---

### Phase 2: Evaluation Service (6 hours)

**Goal**: Add production-ready quality measurement

**Steps**:

1. **Create base metric interface** (30 min)
   - Create `evaluation_service/metrics/base_metric.py`
   - Define abstract `BaseMetric` class
   - Define `compute()` method signature
   - Define `get_metric_name()` method

2. **Implement metric classes** (2.5 hours)
   - Create `evaluation_service/metrics/faithfulness.py`
     - `FaithfulnessMetric`: LLM-based claim verification
     - Extract claims from answer
     - Verify each claim against context
   - Create `evaluation_service/metrics/relevance.py`
     - `AnswerRelevanceMetric`: LLM-based relevance scoring
     - Rate answer relevance to question (1-10 scale)
   - Create `evaluation_service/metrics/context_precision.py`
     - `ContextPrecisionMetric`: Document relevance check
     - Check if each retrieved doc is relevant

3. **Create RAG evaluator** (1 hour)
   - Create `evaluation_service/evaluators/rag_evaluator.py`
   - `RAGEvaluator` class orchestrates all metrics
   - Async execution for parallel metric computation
   - Calculate overall score

4. **Create evaluation service** (1 hour)
   - Create `evaluation_service/service.py`
   - `EvaluationService` class with:
     - `evaluate_response()`: main interface
     - Returns structured results with scores
   - Global singleton: `evaluation_service`

5. **Test evaluation** (1 hour)
   - Unit tests for each metric
   - Integration test with real RAG responses
   - Verify metric accuracy
   - Test async execution

**Deliverable**: Production-ready evaluation harness with clean architecture

---

### Phase 3: Integration (4 hours)

**Goal**: Integrate into chat workflow

**Steps**:

1. **Update chat service** (2 hours)
   - Modify `chat_service/service.py`
   - Import `reranking_service`
   - Increase initial retrieval: 5 → 20 docs
   - Call `rerank()` before generation
   - Optionally call `evaluate_response()` after generation
   - Return metrics in response dict

2. **Add API endpoint** (30 min)
   - Add `/evaluate` POST endpoint to `main.py`
   - Accept: query, response, contexts
   - Return: evaluation metrics
   - Simple, direct implementation

3. **End-to-end testing** (1.5 hours)
   - Test full RAG flow with reranking
   - Test evaluation on various queries
   - Measure latency impact
   - Verify quality improvements

**Deliverable**: Fully integrated, production-ready system

**Total Files Created**: 12

**Reranking Service**:

- `application/reranking_service/__init__.py`
- `application/reranking_service/service.py`
- `application/reranking_service/rerankers/__init__.py`
- `application/reranking_service/rerankers/base_reranker.py`
- `application/reranking_service/rerankers/cross_encoder_reranker.py`

**Evaluation Service**:

- `application/evaluation_service/__init__.py`
- `application/evaluation_service/service.py`
- `application/evaluation_service/metrics/__init__.py`
- `application/evaluation_service/metrics/base_metric.py`
- `application/evaluation_service/metrics/faithfulness.py`
- `application/evaluation_service/metrics/relevance.py`
- `application/evaluation_service/metrics/context_precision.py`
- `application/evaluation_service/evaluators/__init__.py`
- `application/evaluation_service/evaluators/rag_evaluator.py`

---

## Part 5: Configuration Strategy

### Environment Variables

```bash
# Reranking
ENABLE_RERANKING=true
RERANK_TOP_K=5
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Evaluation
ENABLE_EVALUATION=false        # Auto-evaluate responses
EVALUATION_THRESHOLD=0.7       # Minimum acceptable score
```

### Config Class Updates

```python
class Settings(BaseSettings):
    # Reranking
    enable_reranking: bool = True
    rerank_top_k: int = 5
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Evaluation
    enable_evaluation: bool = False
    evaluation_threshold: float = 0.7
```

### Evaluation Frequency Options

| Option | When to Use |
|--------|-------------|
| **Every request** | Development, debugging |
| **Sampling (10%)** | Production monitoring |
| **On-demand** | User feedback, testing |
| **Disabled** | Performance-critical |

**Recommendation**: On-demand via API endpoint for production

---

## Part 6: Testing Strategy

### Unit Tests

- Test Cross-Encoder reranking logic
- Test each metric independently
- Mock LLM calls for speed
- Verify score calculations

### Integration Tests

- Test reranking with real ChromaDB documents
- Test evaluation with real RAG responses
- Measure latency impact
- End-to-end RAG flow test

### Quality Tests

- Compare answer quality with/without reranking
- Verify metric accuracy against manual evaluation
- Test edge cases (empty docs, errors, timeouts)

---

## Part 7: Expected Outcomes

### Performance Improvements

**Reranking**:

- ✅ 20-40% better answer quality
- ✅ Fewer hallucinations
- ✅ Better handling of complex queries
- ⚠️ +50-200ms latency (local model, CPU-dependent)

**Evaluation**:

- ✅ Quantifiable quality metrics
- ✅ Detect regressions automatically
- ✅ Track improvements over time
- ⚠️ +2-3s latency (LLM-based metrics, async)

### Monitoring Capabilities

You'll be able to answer:

- "Is my RAG system getting better?"
- "Which queries produce low-quality answers?"
- "Are my documents relevant?"
- "Is reranking helping?"

---

## Part 8: Rollout Plan

### Step 1: Development (1-2 days)

- Implement reranking service (4 hours)
- Implement evaluation service (6 hours)
- Integration and testing (4 hours)
- Total: 14 hours

### Step 2: Production Deployment

- Deploy with reranking enabled by default
- Evaluation available on-demand via API
- Monitor latency and quality
- No gradual rollout needed (simple, low-risk changes)

---

## Part 9: Success Metrics

### Technical Metrics

- [ ] Reranking service operational
- [ ] Evaluation service operational
- [ ] <200ms reranking latency (CPU-dependent)
- [ ] <3s evaluation latency
- [ ] Zero errors in production
- [ ] 12 new files created with clean architecture

### Quality Metrics

- [ ] Faithfulness score > 0.8
- [ ] Answer relevance > 0.7
- [ ] Context precision > 0.6
- [ ] 20%+ improvement vs baseline

---

## Part 10: Next Steps

### Immediate Actions

1. Review this plan
2. Install dependency: `uv add sentence-transformers`
3. Create feature branch: `git checkout -b feature/reranking-evaluation`
4. Start Phase 1 (reranking service)

### Implementation Order

1. **Day 1 Morning**: Reranking service (4 hours)
2. **Day 1 Afternoon**: Evaluation metrics (3 hours)
3. **Day 2 Morning**: Evaluation service (3 hours)
4. **Day 2 Afternoon**: Integration & testing (4 hours)

---

## Part 11: Risk Mitigation

### Risk 1: Latency Impact

**Mitigation**:

- Reranking can be toggled via config
- Model loads once at startup
- Async evaluation doesn't block responses

### Risk 2: Model Download Size

**Mitigation**:

- Cross-encoder model is ~400MB
- Downloads once, cached locally
- Can pre-download in Docker build

### Risk 3: Evaluation Accuracy

**Mitigation**:

- Use multiple metrics (not just one)
- Validate against manual evaluation
- Metrics are guidance, not absolute truth

---

## Summary

This streamlined implementation adds two capabilities to your RAG system:

1. **Cross-Encoder Reranking**: Improves retrieval quality by 20-40%
2. **Evaluation Harness**: Provides measurable quality metrics

**Key Design Principles**:

- ✅ **Clean Architecture**: Proper separation of concerns with base classes
- ✅ **Extensible**: Easy to add new rerankers or metrics in the future
- ✅ **Production-ready**: Well-structured, testable, maintainable
- ✅ **Focused**: Cross-Encoder only for reranking
- ✅ **Integrated**: Seamless integration with existing LangChain v1 architecture

**Total Effort**: 14 hours (1-2 days)
**Dependencies**: 1 package (sentence-transformers)
**Files Created**: 12 (organized in proper directory structure)
**Risk**: Low (well-structured implementation)

Ready to proceed? Start with Phase 1 (Reranking Service).
