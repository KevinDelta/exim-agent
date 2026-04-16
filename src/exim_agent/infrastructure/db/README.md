# Database Infrastructure

## Overview

The database infrastructure provides a dual-storage architecture optimized for different data access patterns. Supabase serves as the primary transactional database for long-term storage and audit trails, while ChromaDB provides vector search capabilities for semantic retrieval and short-term memory.

## Purpose1

- **Long-term Storage**: Persist compliance data, digests, and analytics in Supabase
- **Vector Search**: Enable semantic search and RAG context retrieval via ChromaDB
- **Conversation Memory**: Store chat history and user context using Mem0 + ChromaDB
- **Audit Trail**: Maintain historical records for compliance and reporting
- **Performance**: Optimize query patterns for different use cases

## Storage Architecture

```yaml
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼────────┐      ┌──────▼──────┐
        │   Supabase     │      │  ChromaDB   │
        │  (PostgreSQL)  │      │   (Vector)  │
        └────────────────┘      └─────────────┘
                │                       │
        ┌───────┴────────┐      ┌──────┴──────────┐
        │ Long-term Data │      │ Short-term Data │
        │ - Digests      │      │ - Embeddings    │
        │ - Tool Results │      │ - RAG Context   │
        │ - Analytics    │      │ - Conversations │
        │ - Portfolios   │      │ - Mem0 Memory   │
        └────────────────┘      └─────────────────┘
```

## Supabase (Long-term Storage)

### Purpose

Supabase is the **source of truth** for all transactional and historical data:

- **Compliance Data**: Tool outputs, API responses, crawl results
- **Pulse Digests**: Weekly/daily compliance summaries
- **Client Portfolios**: SKU+Lane configurations
- **Memory Analytics**: Conversation quality metrics
- **Audit Logs**: Historical tracking for compliance

### Key Tables

#### compliance_data

Stores raw compliance data from domain tools.

```sql
CREATE TABLE compliance_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL,      -- 'hts', 'sanctions', 'refusals', 'rulings'
    source_id TEXT NOT NULL,        -- hts_code, party_name, etc.
    data JSONB NOT NULL,            -- Tool output
    crawl_metadata JSONB,           -- Crawl timestamp, source URL
    content_hash TEXT,              -- For change detection
    last_crawled_at TIMESTAMPTZ,
    change_detected BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);

CREATE INDEX idx_compliance_data_source ON compliance_data(source_type, source_id);
CREATE INDEX idx_compliance_data_hash ON compliance_data(content_hash);
CREATE INDEX idx_compliance_data_updated ON compliance_data(updated_at DESC);
```

**Usage**:

- Cache tool results (24h TTL)
- Track data changes over time
- Audit trail for compliance

#### weekly_pulse_digests

Stores generated pulse digests.

```sql
CREATE TABLE weekly_pulse_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    period_days INTEGER NOT NULL,   -- 1 for daily, 7 for weekly
    total_changes INTEGER NOT NULL,
    high_priority_changes INTEGER NOT NULL,
    medium_priority_changes INTEGER NOT NULL,
    low_priority_changes INTEGER NOT NULL,
    requires_action BOOLEAN NOT NULL,
    status TEXT NOT NULL,           -- 'action_required', 'monitoring', 'clear'
    digest_data JSONB NOT NULL,     -- Full digest with snapshots
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, period_end, period_days)
);

CREATE INDEX idx_pulse_client_period ON weekly_pulse_digests(client_id, period_end DESC);
CREATE INDEX idx_pulse_requires_action ON weekly_pulse_digests(client_id, requires_action);
CREATE INDEX idx_pulse_status ON weekly_pulse_digests(status);
```

**Usage**:

- Store pulse digests for retrieval
- Track compliance trends over time
- Support digest history queries

#### client_portfolios

Stores client SKU+Lane configurations.

```sql
CREATE TABLE client_portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    lane_id TEXT NOT NULL,
    hts_code TEXT,
    product_description TEXT,
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, sku_id, lane_id)
);

CREATE INDEX idx_portfolio_client ON client_portfolios(client_id, active);
CREATE INDEX idx_portfolio_sku ON client_portfolios(sku_id);
```

**Usage**:

- Define monitoring scope for pulse pipelines
- Support portfolio management UI
- Track active vs inactive products

#### memory_analytics

Stores conversation quality metrics.

```sql
CREATE TABLE memory_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    total_memories INTEGER NOT NULL,
    avg_memory_length FLOAT NOT NULL,
    memory_types JSONB,
    insights JSONB,
    recommendations JSONB,
    analyzed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_analytics_user ON memory_analytics(user_id, analyzed_at DESC);
```

**Usage**:

- Track conversation patterns
- Monitor memory system health
- Generate user insights

### Supabase Client (`supabase_client.py`)

Provides type-safe interface to Supabase:

```python
from exim_agent.infrastructure.db import SupabaseClient

client = SupabaseClient()

# Store compliance data
client.store_compliance_data(
    source_type="hts",
    source_id="8471.30.01",
    data={"duty_rate": "0%", ...}
)

# Retrieve cached data
cached = client.get_compliance_data(
    source_type="hts",
    source_id="8471.30.01",
    max_age_hours=24
)

# Store pulse digest
client.store_pulse_digest(
    client_id="acme_corp",
    period_start="2024-01-08T00:00:00Z",
    period_end="2024-01-15T00:00:00Z",
    digest_data={...}
)

# Get latest digest
digest = client.get_latest_digest(
    client_id="acme_corp",
    period_days=7
)

# Get client portfolio
portfolio = client.get_client_portfolio(
    client_id="acme_corp",
    active_only=True
)
```

## ChromaDB (Short-term Memory)

### Purpose3

ChromaDB provides **vector search** for semantic retrieval:

- **RAG Context**: Retrieve relevant documents for LLM context
- **Conversation Memory**: Store chat history via Mem0
- **Compliance Events**: Index digest summaries for search
- **Document Embeddings**: Enable semantic search across compliance docs

### Key Collections

#### compliance_policy_snippets

General compliance policy documents and regulations.

**Metadata Schema**:

```json
{
    "doc_type": "policy",
    "source": "CBP",
    "last_updated": "2024-01-15",
    "regulatory_authority": "US Customs",
    "topic": "classification"
}
```

**Usage**: General compliance questions, policy interpretation

#### compliance_hts_notes

HTS code descriptions and tariff information.

**Metadata Schema**:

```json
{
    "hts_code": "8471.30.01",
    "duty_rate": "0%",
    "unit": "No.",
    "source_url": "https://hts.usitc.gov/...",
    "chapter": "84"
}
```

**Usage**: HTS-specific queries, duty rate lookups

#### compliance_rulings

CBP customs rulings and interpretations.

**Metadata Schema**:

```json
{
    "ruling_number": "N123456",
    "hts_code": "8471.30.01",
    "issue_date": "2023-11-15",
    "summary": "Classification of portable computers",
    "ruling_type": "classification"
}
```

**Usage**: Classification guidance, precedent research

#### compliance_refusal_summaries

FDA/FSIS import refusal summaries.

**Metadata Schema**:

```json
{
    "hts_code": "0201.10.00",
    "refusal_reason": "Salmonella",
    "product_description": "Fresh beef",
    "country": "BR",
    "refusal_date": "2024-01-10"
}
```

**Usage**: Health/safety risk assessment, supplier screening

#### compliance_events

Historical compliance events and digest summaries.

**Metadata Schema**:

```json
{
    "event_type": "digest",
    "client_id": "acme_corp",
    "period_end": "2024-01-15",
    "status": "action_required",
    "priority": "high"
}
```

**Usage**: "What changed last week?" queries, trend analysis

#### mem0_conversations

Conversation memories managed by Mem0.

**Metadata Schema**:

```json
{
    "user_id": "user_123",
    "session_id": "sess_456",
    "timestamp": "2024-01-15T10:30:00Z",
    "memory_type": "conversation"
}
```

**Usage**: Chat context, personalization, conversation history

### ChromaDB Client (`chroma_client.py`)

Provides interface to ChromaDB:

```python
from exim_agent.infrastructure.db import ChromaClient

client = ChromaClient()

# Add documents to collection
client.add_documents(
    collection_name="compliance_hts_notes",
    documents=["HTS 8471.30.01 covers portable computers..."],
    metadatas=[{"hts_code": "8471.30.01", "duty_rate": "0%"}],
    ids=["hts_8471.30.01"]
)

# Search collection
results = client.search(
    collection_name="compliance_hts_notes",
    query_text="What is the duty rate for laptops?",
    n_results=5
)

# Search multiple collections
results = client.search_multi_collection(
    collection_names=["compliance_hts_notes", "compliance_rulings"],
    query_text="laptop classification",
    n_results=5
)
```

### Compliance Collections (`compliance_collections.py`)

High-level interface for compliance-specific operations:

```python
from exim_agent.infrastructure.db import ComplianceCollections

collections = ComplianceCollections()

# Initialize all collections
collections.initialize_collections()

# Index compliance data
collections.index_hts_data(
    hts_code="8471.30.01",
    description="Portable computers",
    metadata={...}
)

collections.index_ruling(
    ruling_number="N123456",
    summary="Classification of portable computers",
    metadata={...}
)

# Search for context
context = collections.get_compliance_context(
    query="What are the import requirements for laptops?",
    collections=["hts_notes", "rulings", "policy"],
    top_k=5
)
```

## Data Flow Patterns

### Pattern 1: Tool Execution with Caching

```yaml
Tool.run()
    ↓
Check Supabase Cache
    ↓
Cache Hit? → Return from Supabase
    ↓
Cache Miss → Call External API
    ↓
Store in Supabase (long-term)
    ↓
Index in ChromaDB (short-term, optional)
    ↓
Return Result
```

### Pattern 2: Pulse Digest Generation

```yaml
Generate Snapshots
    ↓
Compute Deltas
    ↓
Create Digest
    ↓
Store in Supabase (primary)
    ↓
Index Summary in ChromaDB (for search)
    ↓
Return Digest
```

### Pattern 3: Chat Q&A

```yaml
User Question
    ↓
Retrieve from ChromaDB (RAG context)
    ↓
Retrieve from Mem0/ChromaDB (conversation history)
    ↓
Generate Answer
    ↓
Store in Mem0/ChromaDB (conversation memory)
    ↓
Return Answer
```

### Pattern 4: Compliance Data Ingestion

```yaml
Crawl External Source
    ↓
Store Raw Data in Supabase
    ↓
Process and Chunk
    ↓
Generate Embeddings
    ↓
Index in ChromaDB
    ↓
Mark as Indexed in Supabase
```

## Storage Decision Matrix

| Data Type | Primary Storage | Secondary Storage | Reason |
|-----------|----------------|-------------------|---------|
| Tool Results | Supabase | ChromaDB (optional) | Caching, audit trail |
| Pulse Digests | Supabase | ChromaDB (summary) | Historical tracking, search |
| Client Portfolios | Supabase | None | Transactional data |
| Compliance Docs | ChromaDB | None | Vector search only |
| Conversation History | ChromaDB (via Mem0) | None | Short-term memory |
| Analytics | Supabase | None | Reporting, dashboards |
| Embeddings | ChromaDB | None | Vector search only |

## Performance Optimization

### Supabase Optimization

1. **Indexes**: Create indexes on frequently queried columns
2. **JSONB Queries**: Use GIN indexes for JSONB columns
3. **Connection Pooling**: Reuse connections (max 20 connections)
4. **Batch Operations**: Insert/update in batches of 100
5. **RLS Policies**: Use Row Level Security for multi-tenancy

### ChromaDB Optimization

1. **Collection Size**: Keep collections under 1M documents
2. **Metadata Filtering**: Use metadata for pre-filtering
3. **Embedding Cache**: Cache embeddings for common queries
4. **Parallel Search**: Search multiple collections concurrently
5. **Cleanup**: Remove old embeddings (>90 days)

## Configuration

### Environment Variables

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx  # For client-side access
SUPABASE_SERVICE_KEY=xxx  # For server-side access

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
CHROMA_HOST=localhost  # For client-server mode
CHROMA_PORT=8000

# Mem0 (uses ChromaDB backend)
MEM0_API_KEY=xxx  # Optional, can use local mode
MEM0_COLLECTION_NAME=mem0_conversations
```

### Connection Settings

```python
# In config.py
class DatabaseConfig:
    # Supabase
    supabase_max_connections: int = 20
    supabase_timeout: int = 30  # seconds
    
    # ChromaDB
    chroma_persist_directory: str = "./data/chroma_db"
    chroma_collection_metadata: Dict = {"hnsw:space": "cosine"}
    
    # Caching
    cache_ttl_hours: int = 24
    enable_cache: bool = True
```

## Migrations

### Supabase Migrations

Located in `migrations/` directory:

```bash
# Run migrations
python scripts/run_migrations.py

# Create new migration
python scripts/create_migration.py "add_client_portfolios_table"
```

### ChromaDB Migrations

ChromaDB collections are created on-demand:

```python
# Initialize collections
from exim_agent.infrastructure.db import ComplianceCollections

collections = ComplianceCollections()
collections.initialize_collections()
```

## Backup and Recovery

### Supabase Backup

- **Automatic**: Supabase provides daily backups (7-day retention)
- **Manual**: Export via pg_dump or Supabase dashboard
- **Point-in-Time Recovery**: Available on Pro plan

### ChromaDB Backup

- **Persist Directory**: Backup `data/chroma_db/` directory
- **Export**: Use ChromaDB export API
- **Rebuild**: Can rebuild from Supabase if needed

```bash
# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz data/chroma_db/

# Restore ChromaDB
tar -xzf chroma_backup_20240115.tar.gz
```

## Monitoring

### Metrics to Track

**Supabase**:

- Query latency (P50, P95, P99)
- Connection pool usage
- Table sizes and growth rate
- Cache hit rate

**ChromaDB**:

- Search latency
- Collection sizes
- Embedding generation time
- Memory usage

### Health Checks

```python
# Check Supabase connection
def check_supabase_health():
    try:
        client.table("compliance_data").select("id").limit(1).execute()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Check ChromaDB connection
def check_chroma_health():
    try:
        client.heartbeat()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Testing

### Unit Tests

```bash
# Test Supabase client
pytest tests/test_supabase_client.py -v

# Test ChromaDB client
pytest tests/test_chroma_client.py -v

# Test compliance collections
pytest tests/test_compliance_collections.py -v
```

### Integration Tests

```bash
# Test with real databases
pytest tests/test_db_integration.py -v --integration
```

## Troubleshooting

### Supabase Issues

**Connection Errors**:

- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Verify network connectivity
- Check connection pool limits

**Slow Queries**:

- Review query execution plans
- Add missing indexes
- Optimize JSONB queries

### ChromaDB Issues

**Collection Not Found**:

- Run `initialize_collections()`
- Check persist directory permissions

**Slow Searches**:

- Reduce collection size
- Use metadata filtering
- Increase `n_results` limit

**Memory Issues**:

- Reduce collection sizes
- Clear old embeddings
- Increase system memory

## Best Practices

### For Developers

1. **Use Supabase for Persistence**: All important data goes to Supabase
2. **Use ChromaDB for Search**: Vector search and short-term memory only
3. **Cache Aggressively**: Reduce API calls and improve performance
4. **Batch Operations**: Insert/update in batches for efficiency
5. **Handle Failures**: Graceful degradation when storage fails

### For Operators

1. **Monitor Storage Growth**: Track table and collection sizes
2. **Regular Cleanup**: Remove old data (>90 days)
3. **Backup Regularly**: Automated backups for both systems
4. **Optimize Indexes**: Review and update based on query patterns
5. **Scale Appropriately**: Increase resources as needed

## Related Documentation

- [Compliance Service README](../../application/compliance_service/README.md) - Storage usage patterns
- [Domain Tools README](../../domain/tools/README.md) - Caching strategy
- [MVP De-bloat Review](../../../docs/MVP_DEBLOAT_REVIEW.md) - Digest storage changes
- [Supabase Documentation](https://supabase.com/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)
