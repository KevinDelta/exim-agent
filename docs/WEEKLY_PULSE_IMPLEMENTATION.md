# Weekly Pulse Implementation Summary

## Overview

Implemented a robust architecture for storing and retrieving weekly compliance pulse digests using **Supabase as primary storage** and **Chroma as optional semantic search index**.

## Architecture Decision

### Why Supabase Primary?

Weekly pulse digests are **structured transactional data**, not vector embeddings:

| Requirement | Supabase ✅ | ChromaDB ❌ |
|------------|-------------|-------------|
| SQL queries by date/client | Fast | No SQL support |
| Time-series analysis | Native | Requires workarounds |
| ACID guarantees | Yes | Eventually consistent |
| Relational integrity | Foreign keys | None |
| Primary use case | Transactional data | Vector similarity |

### Data Flow

```
Weekly Pulse Pipeline (ZenML)
  ↓
  ├─ Supabase (PRIMARY) ─────────────→ API Retrieval
  │  • weekly_pulse_digests table         GET /pulse/{client_id}/weekly
  │  • Full structured data
  │  • SQL queryable
  │  • Source of truth
  │
  └─ ChromaDB (OPTIONAL) ────────────→ Semantic Search
     • Digest summary text                "Find similar compliance patterns"
     • Linked via digest_id
     • For natural language queries
```

## Files Modified

### 1. Supabase Client (`infrastructure/db/supabase_client.py`)

**Added Methods:**
- `store_weekly_pulse_digest()` - Save digest to Supabase
- `get_weekly_pulse_digests()` - Retrieve digests with filters
- `get_latest_digest()` - Get most recent digest

```python
# Usage
from exim_agent.infrastructure.db.supabase_client import supabase_client

# Store digest
result = supabase_client.store_weekly_pulse_digest(
    client_id="ABC123",
    digest=digest_data
)

# Retrieve latest
latest = supabase_client.get_latest_digest(client_id="ABC123")

# Get action-required digests
action_digests = supabase_client.get_weekly_pulse_digests(
    client_id="ABC123",
    requires_action_only=True
)
```

### 2. Weekly Pulse Pipeline (`zenml_pipelines/weekly_pulse.py`)

**Updated `save_digest()` Step:**

```python
# 1. PRIMARY: Save to Supabase
result = supabase_client.store_weekly_pulse_digest(
    client_id=client_id,
    digest=digest
)

# 2. OPTIONAL: Index summary in Chroma for semantic search
policy_collection.add_texts(
    texts=[summary_text],
    metadatas=[{
        "digest_id": result.get('id'),  # Link back to Supabase
        "client_id": client_id,
        ...
    }]
)
```

### 3. API Routes (`infrastructure/api/routes/compliance_routes.py`)

**Updated Endpoint:**

```http
GET /compliance/pulse/{client_id}/weekly?limit=1&requires_action_only=false
```

**Response:**
```json
{
  "success": true,
  "client_id": "ABC123",
  "period_start": "2025-10-25T00:00:00Z",
  "period_end": "2025-11-01T00:00:00Z",
  "summary": {
    "total_changes": 12,
    "high_priority_changes": 3,
    "medium_priority_changes": 5,
    "low_priority_changes": 4
  },
  "changes": [...],
  "metadata": {
    "digest_id": 42,
    "generated_at": "2025-11-01T23:15:00Z",
    "requires_action": true,
    "status": "action_required"
  }
}
```

## Database Schema

### Table: `weekly_pulse_digests`

```sql
CREATE TABLE weekly_pulse_digests (
  id BIGSERIAL PRIMARY KEY,
  client_id TEXT NOT NULL,
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  total_changes INT NOT NULL,
  high_priority_changes INT NOT NULL,
  medium_priority_changes INT NOT NULL,
  low_priority_changes INT NOT NULL,
  requires_action BOOLEAN NOT NULL,
  status TEXT NOT NULL,
  digest_data JSONB NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
- `idx_weekly_pulse_client_period` - Fast client + date queries
- `idx_weekly_pulse_requires_action` - Action-required filtering
- `idx_weekly_pulse_digest_data` - GIN index for JSONB queries

**Row Level Security:** Enabled for multi-tenant isolation

## Setup Instructions

### 1. Run Database Migration

**Option A: Supabase Dashboard**
```bash
# Copy SQL from migrations/001_create_weekly_pulse_digests.sql
# Paste into Supabase Dashboard > SQL Editor > Run
```

**Option B: Migration Script**
```bash
uv run python scripts/run_migrations.py
```

### 2. Configure Environment

```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key  # For backend operations
```

### 3. Test Connection

```bash
uv run python -c "
from exim_agent.infrastructure.db.supabase_client import supabase_client
print('Connected:', supabase_client.health_check())
"
```

### 4. Run Weekly Pulse Pipeline

```bash
# Via Python
uv run python -c "
from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline
result = weekly_pulse_pipeline(client_id='test_client')
print('Digest generated:', result)
"

# Via ZenML CLI (if configured)
zenml pipeline run weekly_pulse_pipeline --client_id=test_client
```

### 5. Retrieve via API

```bash
# Get latest digest
curl http://localhost:8000/compliance/pulse/test_client/weekly

# Get action-required digests only
curl "http://localhost:8000/compliance/pulse/test_client/weekly?requires_action_only=true"

# Get last 3 digests
curl "http://localhost:8000/compliance/pulse/test_client/weekly?limit=3"
```

## Benefits of This Architecture

### ✅ Structured Queries
```sql
-- Get all action-required digests in last 3 months
SELECT * FROM weekly_pulse_digests
WHERE client_id = 'ABC123'
  AND requires_action = true
  AND period_end > NOW() - INTERVAL '3 months'
ORDER BY period_end DESC;
```

### ✅ Time-Series Analysis
```sql
-- Track high-priority changes over time
SELECT 
  period_end::date,
  high_priority_changes,
  total_changes
FROM weekly_pulse_digests
WHERE client_id = 'ABC123'
ORDER BY period_end;
```

### ✅ API Performance
- Fast retrieval by ID: `O(1)` with primary key
- Indexed date range queries
- No vector similarity computation overhead

### ✅ Data Integrity
- Foreign key constraints (when adding client profiles)
- Check constraints on valid values
- Automatic timestamp updates

### ✅ Optional Semantic Search
```python
# When you need it: "Find weeks with similar compliance patterns"
similar_digests = chroma_collection.similarity_search(
    "Weeks with China sanctions issues",
    filter={"client_id": "ABC123"}
)
```

## Testing

```python
# Test digest storage
from exim_agent.infrastructure.db.supabase_client import supabase_client

digest = {
    "period_start": "2025-10-25T00:00:00Z",
    "period_end": "2025-11-01T00:00:00Z",
    "generated_at": "2025-11-01T23:00:00Z",
    "requires_action": True,
    "status": "action_required",
    "summary": {
        "total_changes": 5,
        "high_priority_changes": 2,
        "medium_priority_changes": 2,
        "low_priority_changes": 1
    },
    "top_changes": []
}

# Store
result = supabase_client.store_weekly_pulse_digest(
    client_id="test_client",
    digest=digest
)
print(f"Stored with ID: {result['id']}")

# Retrieve
latest = supabase_client.get_latest_digest(client_id="test_client")
print(f"Retrieved: {latest['period_end']}")
```

## Next Steps

1. **Schedule Pipeline**: Set up cron job or ZenML schedule for weekly runs
2. **Email Notifications**: Send digest emails to clients when `requires_action=true`
3. **Dashboard UI**: Build frontend component to display weekly pulse
4. **Historical Trends**: Add charts showing compliance metrics over time
5. **Client Profiles**: Link to client profile table with foreign key

## Files Created

- `migrations/001_create_weekly_pulse_digests.sql` - Database schema
- `migrations/README.md` - Migration instructions
- `scripts/run_migrations.py` - Automated migration runner
- `docs/WEEKLY_PULSE_IMPLEMENTATION.md` - This document

## Files Modified

- `infrastructure/db/supabase_client.py` - Added digest storage methods
- `zenml_pipelines/weekly_pulse.py` - Updated save_digest step
- `infrastructure/api/routes/compliance_routes.py` - Updated API endpoint

---

**Implementation Status:** ✅ Complete

**Architecture Pattern:** Supabase (Primary) + Chroma (Optional Index)

**Ready for Production:** After running migrations and configuring Supabase credentials
