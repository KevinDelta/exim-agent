# Mem0 Migration Plan

## Overview

This plan outlines the step-by-step migration from custom memory implementation to Mem0.

**Goal**: Reduce ~1,500 lines of custom memory code to ~100 lines using Mem0's built-in features.

---

## Pre-Migration Checklist

- [ ] Backup current codebase
- [ ] Document current memory behavior
- [ ] Test current system end-to-end
- [ ] Export existing memory data (if any)

---

## Phase 1: Install & Configure ✅

### Tasks

1. **Add Mem0 dependency**
   - Update `pyproject.toml`
   - Run `uv sync`

2. **Add Mem0 configuration**
   - Update `config.py` with Mem0 settings
   - Add feature flag for gradual rollout

3. **Verify installation**
   - Test Mem0 import
   - Verify ChromaDB compatibility

### Changes
- ✅ `pyproject.toml` - Add mem0ai dependency
- ✅ `config.py` - Add Mem0 configuration

### Testing
```bash
# Test import
python -c "from mem0 import Memory; print('Mem0 installed successfully')"
```

---

## Phase 2: Create Mem0 Wrapper ✅

### Tasks

1. **Create memory_service structure**
   - Create `mem0_client.py`
   - Create `memory_types.py` for type definitions

2. **Implement Mem0Client wrapper**
   - Initialize Mem0 with config
   - Wrap key operations (add, search, get_all, delete)
   - Add logging

3. **Test wrapper in isolation**
   - Test add/search/delete operations
   - Verify ChromaDB backend connection

### Changes
- ✅ `application/memory_service/mem0_client.py` (NEW)
- ✅ `application/memory_service/memory_types.py` (NEW)

### Testing
```python
# Test Mem0 client
from acc_llamaindex.application.memory_service.mem0_client import mem0_client

# Add memory
result = mem0_client.add(
    messages=[{"role": "user", "content": "Hello"}],
    user_id="test-user",
    session_id="test-session"
)
print("Memory added:", result)

# Search
memories = mem0_client.search(
    query="Hello",
    user_id="test-user",
    session_id="test-session"
)
print("Found memories:", len(memories))
```

---

## Phase 3: Simplify LangGraph ✅

### Tasks

1. **Backup current graph.py**
   - Copy to `graph.py.backup`

2. **Update state machine**
   - Reduce from 7 nodes to 4 nodes
   - Update `load_memories` to use Mem0
   - Update `update_memories` to use Mem0
   - Keep RAG and generation logic unchanged

3. **Test new graph**
   - Run sample queries
   - Compare outputs with old system
   - Verify memory persistence

### Changes

- ✅ `application/chat_service/graph.py` (UPDATED - simplified)
- ✅ `application/chat_service/graph.py.backup` (backup of old version)

### Testing

```python
# Test simplified graph
from acc_llamaindex.application.chat_service.graph import memory_graph

result = memory_graph.invoke({
    "query": "What is LangChain?",
    "user_id": "test-user",
    "session_id": "test-session"
})
print("Response:", result["response"])
```

---

## Phase 4: Remove Custom Code ⏳

### Tasks

1. **Deprecate custom memory files**
   - Move to `_deprecated/` folder first (don't delete yet)
   - Update imports to use Mem0

2. **Files to deprecate**:
   - `session_manager.py` → Mem0 session memory
   - `deduplication.py` → Mem0 built-in deduplication
   - `conversation_summarizer.py` → Mem0 built-in summarization
   - `promotion.py` → Mem0 automatic promotion
   - `intent_classifier.py` → Mem0 built-in intent
   - `entity_extractor.py` → Mem0 built-in entity extraction
   - `salience_tracker.py` → Mem0 relevance scoring
   - `background_jobs.py` → No longer needed
   - `metrics.py` → Move to analytics if needed

3. **Clean up ChromaDB client**
   - Remove episodic memory collection initialization
   - Keep document collection for RAG

### Changes

- ✅ Move files to `application/memory_service/_deprecated/`
- ✅ `infrastructure/db/chroma_client.py` (SIMPLIFIED)

### Testing

```bash
# Verify no imports break
pytest tests/
```

---

## Phase 5: Add Memory Routes ✅

### Tasks

1. **Create memory routes**
   - Create `memory_routes.py` with CRUD endpoints
   - Add search, get_all, delete, reset operations

2. **Integrate with FastAPI**
   - Add routes to main app
   - Update API documentation

3. **Test endpoints**
   - Test each CRUD operation
   - Verify error handling

### Changes

- ✅ `infrastructure/api/routes/memory_routes.py` (NEW)
- ✅ `infrastructure/api/main.py` (UPDATED - add routes)

### Testing

```bash
# Test endpoints
curl -X POST http://localhost:8000/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "user-123", "session_id": "session-1"}'

curl -X GET http://localhost:8000/memory/all?user_id=user-123
```

---

## Phase 6: Adapt ZenML Pipelines ✅

### Tasks

1. **Keep document ingestion pipeline**
   - No changes needed (RAG documents separate from Mem0)

2. **Remove distillation pipeline**
   - Mem0 handles this automatically
   - Deprecate `distillation_pipeline.py`

3. **Remove promotion pipeline**
   - Mem0 handles this automatically
   - Deprecate `promotion_pipeline.py`

4. **Create memory analytics pipeline**
   - Add new pipeline for memory insights
   - Track usage patterns

5. **Update runner**
   - Remove distillation/promotion from runner
   - Add analytics pipeline

### Changes
- ✅ `application/zenml_pipelines/memory_analytics_pipeline.py` (NEW)
- ✅ Move `distillation_pipeline.py` to `_deprecated/`
- ✅ Move `promotion_pipeline.py` to `_deprecated/`
- ✅ `application/zenml_pipelines/runner.py` (UPDATED)

### Testing
```python
# Test analytics pipeline
from acc_llamaindex.application.zenml_pipelines.memory_analytics_pipeline import (
    run_memory_analytics
)

stats = run_memory_analytics(user_id="test-user")
print("Memory stats:", stats)
```

---

## Phase 7: Update Chat Service ✅

### Tasks

1. **Update chat service**
   - Use new graph with Mem0
   - Remove old memory service calls
   - Simplify orchestration

2. **Update service.py**
   - Remove session_manager imports
   - Use Mem0 via graph

### Changes

- ✅ `application/chat_service/service.py` (UPDATED)

---

## Phase 8: Testing & Validation 🧪

### Unit Tests

```bash
# Test Mem0 client
pytest tests/test_mem0_client.py -v

# Test simplified graph
pytest tests/test_graph.py -v

# Test memory routes
pytest tests/test_memory_routes.py -v
```

### Integration Tests

```bash
# End-to-end conversation test
pytest tests/integration/test_conversation_flow.py -v

# Memory persistence test
pytest tests/integration/test_memory_persistence.py -v
```

### Performance Tests

```bash
# Compare old vs new performance
pytest tests/performance/test_memory_performance.py -v
```

---

## Phase 9: Documentation 📝

### Tasks

1. **Update README**
   - Document Mem0 integration
   - Update architecture diagram
   - Update setup instructions

2. **Update API docs**
   - Document new memory endpoints
   - Add examples

3. **Create runbook**
   - Common operations
   - Troubleshooting
   - Rollback procedures

### Changes
- ✅ `README.md` (UPDATED)
- ✅ `docs/MEMORY_API.md` (NEW)
- ✅ `docs/RUNBOOK.md` (NEW)

---

## Phase 10: Deployment 🚀

### Tasks

1. **Update Docker configuration**
   - Ensure Mem0 dependencies included
   - Update environment variables

2. **Update docker-compose**
   - No changes needed (Mem0 uses existing Chroma)

3. **Deploy to staging**
   - Test in staging environment
   - Monitor for issues

4. **Gradual rollout**
   - 10% traffic → Mem0
   - 50% traffic → Mem0
   - 100% traffic → Mem0

### Changes
- ✅ `Dockerfile` (UPDATED if needed)
- ✅ `docker-compose.yaml` (verify)

---

## Rollback Plan

If issues arise:

1. **Immediate rollback**
   ```python
   # In config.py
   mem0_enabled = False  # Switch back to custom implementation
   ```

2. **Restore deprecated files**
   ```bash
   mv application/memory_service/_deprecated/* application/memory_service/
   ```

3. **Revert graph.py**
   ```bash
   cp application/chat_service/graph.py.backup application/chat_service/graph.py
   ```

---

## Success Metrics

### Code Quality
- ✅ Code reduction: 1,500 lines → 100 lines
- ✅ Files reduced: 9 → 2
- ✅ Graph nodes: 7 → 4

### Performance
- ✅ Response time: Similar or better
- ✅ Memory usage: Similar or lower
- ✅ Query accuracy: Maintained or improved

### Functionality
- ✅ All features working
- ✅ Memory persistence verified
- ✅ No data loss
- ✅ API endpoints functional

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1. Install & Configure | 1 hour | ⏳ Ready |
| 2. Create Wrapper | 2 hours | ⏳ Ready |
| 3. Simplify LangGraph | 3 hours | ⏳ Ready |
| 4. Remove Custom Code | 1 hour | ⏳ Ready |
| 5. Add Memory Routes | 2 hours | ⏳ Ready |
| 6. Adapt ZenML | 2 hours | ⏳ Ready |
| 7. Update Chat Service | 1 hour | ⏳ Ready |
| 8. Testing | 4 hours | ⏳ Ready |
| 9. Documentation | 2 hours | ⏳ Ready |
| 10. Deployment | Varies | ⏳ Ready |

**Total Estimated Time**: 18-20 hours

---

## Risk Assessment

### High Risk
- ❌ None identified (feature flag allows instant rollback)

### Medium Risk
- ⚠️ **Performance**: Mem0 may have different performance characteristics
  - **Mitigation**: Test thoroughly in staging
- ⚠️ **Data migration**: Existing memory data needs migration
  - **Mitigation**: Export before migration, verify after

### Low Risk
- ✅ **Breaking changes**: All behind feature flag
- ✅ **Dependencies**: Mem0 is well-maintained
- ✅ **Compatibility**: Uses existing ChromaDB

---

## Next Steps

1. **Review this plan** - Ensure all stakeholders agree
2. **Start Phase 1** - Install and configure Mem0
3. **Execute phases sequentially** - Don't skip ahead
4. **Test after each phase** - Catch issues early
5. **Document learnings** - Update plan as needed

---

**Status**: Ready to begin implementation
**Last Updated**: 2025-10-21
