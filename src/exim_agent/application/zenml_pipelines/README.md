# ZenML Pipelines

## Overview

ZenML pipelines orchestrate the automated generation of compliance digests (weekly/daily pulses) for client portfolios. These pipelines coordinate snapshot generation, delta computation, and digest creation to provide actionable compliance intelligence.

## Purpose

- **Pulse Orchestration**: Automate weekly and daily compliance digest generation
- **Portfolio Monitoring**: Track compliance status across multiple SKU+Lane combinations
- **Change Detection**: Identify and prioritize compliance changes over time
- **Digest Generation**: Create actionable summaries with top priority changes
- **Historical Tracking**: Store digests in Supabase for audit and trend analysis

## Architecture

```
Scheduler (Cron/ZenML)
    ↓
Load Client Portfolio
    ↓
Load Previous Snapshots (baseline)
    ↓
Generate Current Snapshots (parallel)
    ↓
Compute Deltas (tile-level comparison)
    ↓
Rank by Impact (priority scoring)
    ↓
Generate Digest (summary + top changes)
    ↓
Save to Supabase + Index in ChromaDB
    ↓
Notification (optional)
```

## Key Pipelines

### Weekly Pulse Pipeline (`weekly_pulse.py`)

The primary pipeline for generating weekly compliance digests.

#### Pipeline Steps

1. **load_client_sku_lanes**: Retrieve client's monitored SKU+Lane portfolio
2. **load_previous_snapshots**: Get baseline snapshots from last digest
3. **generate_current_snapshots**: Create fresh snapshots for all SKU+Lanes
4. **compute_deltas**: Compare current vs previous at tile level
5. **rank_by_impact**: Prioritize changes by risk and urgency
6. **generate_digest**: Create summary with top 10 changes
7. **save_digest**: Persist to Supabase and index in ChromaDB

#### Execution

```python
from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline

# Run pipeline for a client
pipeline = weekly_pulse_pipeline(
    client_id="acme_corp",
    period_days=7  # weekly
)

pipeline.run()
```

#### Via API

```bash
curl -X POST http://localhost:8000/compliance/pulse/acme_corp/weekly
```

#### Via CLI

```bash
python scripts/run_pulse.py --client-id acme_corp --weekly
```

### Daily Pulse Pipeline

Same pipeline as weekly, but with `period_days=1` for daily monitoring.

```python
pipeline = weekly_pulse_pipeline(
    client_id="acme_corp",
    period_days=1  # daily
)
```

## Pipeline Components

### Step 1: Load Client SKU+Lanes

**Purpose**: Retrieve the list of products and trade routes to monitor

**Data Source**: 
- Supabase `client_portfolios` table
- Fallback to configuration file if DB unavailable

**Output**:
```python
[
    {
        "sku_id": "WIDGET-001",
        "lane_id": "US-CN",
        "hts_code": "8471.30.01",
        "description": "Portable computers"
    },
    ...
]
```

### Step 2: Load Previous Snapshots

**Purpose**: Establish baseline for delta computation

**Data Source**: Supabase `weekly_pulse_digests` table

**Query Logic**:
- Find most recent digest for client
- Extract snapshot data from `digest_data` JSON field
- Build `Dict[sku_lane_key, snapshot]` for comparison

**Output**:
```python
{
    "WIDGET-001_US-CN": {
        "tiles": {...},
        "overall_risk_level": "medium",
        "timestamp": "2024-01-08T00:00:00Z"
    },
    ...
}
```

**Edge Case**: First run (no previous digest) returns empty dict

### Step 3: Generate Current Snapshots

**Purpose**: Create fresh compliance snapshots for all SKU+Lanes

**Execution**: Parallel processing using ComplianceService

**Performance**:
- Processes multiple SKU+Lanes concurrently
- Target: 100 SKU+Lanes in <15 minutes
- Average: 5-10 seconds per SKU+Lane

**Error Handling**:
- Individual failures don't block pipeline
- Failed SKU+Lanes logged and included in error summary
- Partial results still generate digest

**Output**:
```python
{
    "WIDGET-001_US-CN": {
        "tiles": {
            "hts": {...},
            "sanctions": {...},
            "refusals": {...},
            "rulings": {...}
        },
        "overall_risk_level": "high",
        "risk_score": 75.0,
        "timestamp": "2024-01-15T00:00:00Z"
    },
    ...
}
```

### Step 4: Compute Deltas

**Purpose**: Identify changes at the tile level

**Comparison Logic**:
- Compare each tile's `status`, `risk_level`, and `headline`
- Detect status changes: `clear` → `attention` → `action`
- Detect risk escalations: `low` → `medium` → `high`
- Identify new tiles (didn't exist in previous snapshot)

**Change Categories**:
- `risk_escalation`: Risk level increased
- `new_requirement`: New compliance requirement detected
- `status_change`: Tile status changed
- `new_monitoring`: New tile added to snapshot

**Output**:
```python
[
    {
        "sku_id": "WIDGET-001",
        "lane_id": "US-CN",
        "tile_type": "sanctions",
        "change_type": "risk_escalation",
        "previous_risk": "low",
        "current_risk": "high",
        "headline": "New sanctions match detected",
        "priority": "high"
    },
    ...
]
```

### Step 5: Rank by Impact

**Purpose**: Prioritize changes for digest summary

**Ranking Criteria**:
1. Risk level (high > medium > low)
2. Change type (risk_escalation > new_requirement > status_change)
3. Tile type (sanctions > refusals > hts > rulings)
4. Recency (newer changes prioritized)

**Output**: Sorted list of changes with top 10 for digest

### Step 6: Generate Digest

**Purpose**: Create actionable summary for client

**Digest Structure**:
```python
{
    "client_id": "acme_corp",
    "period_start": "2024-01-08T00:00:00Z",
    "period_end": "2024-01-15T00:00:00Z",
    "total_changes": 45,
    "high_priority_changes": 8,
    "medium_priority_changes": 22,
    "low_priority_changes": 15,
    "requires_action": True,
    "status": "action_required",  # or "monitoring", "clear"
    "summary": "8 high-priority compliance changes detected...",
    "top_changes": [
        {
            "sku_id": "WIDGET-001",
            "lane_id": "US-CN",
            "change_type": "risk_escalation",
            "headline": "New sanctions match detected",
            "priority": "high",
            "details": {...}
        },
        ...  # top 10 changes
    ],
    "snapshots": {
        "WIDGET-001_US-CN": {...},
        ...
    },
    "errors": {
        "failed_sku_lanes": ["WIDGET-002_US-MX"],
        "error_count": 1,
        "success_rate": 0.95
    },
    "generated_at": "2024-01-15T10:30:00Z"
}
```

### Step 7: Save Digest

**Purpose**: Persist digest for retrieval and audit

**Storage Locations**:

1. **Supabase** (`weekly_pulse_digests` table):
   - Full digest JSON in `digest_data` field
   - Metadata fields for querying (client_id, period_end, requires_action)
   - Historical tracking and audit trail

2. **ChromaDB** (`compliance_events` collection):
   - Digest summary indexed for semantic search
   - Enables "What changed last week?" queries
   - Metadata: client_id, period_end, status

**Cleanup**: Old digests (>90 days) can be archived

## Pipeline Configuration

### Environment Variables

```bash
# ZenML Configuration
ZENML_STORE_URL=http://localhost:8080  # optional, uses local if not set

# Supabase (required)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx

# ChromaDB (required)
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# LLM Provider (required)
OPENAI_API_KEY=sk-...

# Compliance APIs (required for real data)
CSL_API_KEY=xxx  # ITA Consolidated Screening List

# Performance Tuning
MAX_PARALLEL_SNAPSHOTS=10
SNAPSHOT_TIMEOUT_SECONDS=30
TOOL_TIMEOUT_SECONDS=10
```

### Pipeline Parameters

```python
@pipeline
def weekly_pulse_pipeline(
    client_id: str,
    period_days: int = 7,
    parallel_workers: int = 10,
    include_errors: bool = True
):
    ...
```

## Execution Modes

### 1. On-Demand Execution

Run pipeline manually for testing or ad-hoc needs:

```bash
# Via Python script
python scripts/run_pulse.py --client-id acme_corp --weekly

# Via API
curl -X POST http://localhost:8000/compliance/pulse/acme_corp/weekly
```

### 2. Scheduled Execution

#### Using Cron

```bash
# Weekly pulse every Monday at 6 AM
0 6 * * 1 cd /app && python scripts/run_pulse.py --client-id acme_corp --weekly

# Daily pulse every day at 6 AM
0 6 * * * cd /app && python scripts/run_pulse.py --client-id acme_corp --daily
```

#### Using ZenML Schedules

```python
from zenml.pipelines import Schedule

schedule = Schedule(cron_expression="0 6 * * 1")  # Every Monday at 6 AM

weekly_pulse_pipeline.run(
    schedule=schedule,
    client_id="acme_corp"
)
```

### 3. Event-Driven Execution

Trigger pipeline on specific events:

```python
# Trigger on new compliance data ingestion
@event_trigger(event_type="compliance_data_updated")
def on_compliance_update(event):
    weekly_pulse_pipeline.run(
        client_id=event.client_id,
        period_days=1  # daily pulse
    )
```

## Monitoring and Observability

### Pipeline Metrics

Tracked in `pipeline_execution_metrics` table:

- **Execution Time**: Total pipeline duration
- **SKU+Lane Counts**: Total, successful, failed
- **Tool Stats**: Calls, successes, failures, avg duration
- **Digest Stats**: Total changes, high-priority count
- **Success Rate**: Percentage of successful snapshots

### Logging

Structured logs with correlation IDs:

```python
logger.info(
    "Pipeline started",
    extra={
        "correlation_id": "pulse_123",
        "client_id": "acme_corp",
        "period_days": 7
    }
)
```

### ZenML Dashboard

View pipeline runs, artifacts, and lineage:

```bash
zenml up  # Start ZenML dashboard
# Navigate to http://localhost:8080
```

## Error Handling

### Graceful Degradation

1. **Tool Failures**: Use fallback data, continue pipeline
2. **Snapshot Failures**: Log error, continue with other SKU+Lanes
3. **Storage Failures**: Log error, return digest (don't block)
4. **ChromaDB Failures**: Log warning, skip indexing (non-critical)

### Error Aggregation

Digest includes error summary:

```python
"errors": {
    "failed_sku_lanes": ["WIDGET-002_US-MX"],
    "error_messages": {
        "WIDGET-002_US-MX": "Tool timeout: HTSTool"
    },
    "error_count": 1,
    "success_rate": 0.95,
    "tool_failures": {
        "hts": 1,
        "sanctions": 0,
        "refusals": 0,
        "rulings": 0
    }
}
```

## Performance Optimization

### Parallel Processing

```python
# Process SKU+Lanes in parallel
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(generate_snapshot, sku_lane)
        for sku_lane in sku_lanes
    ]
    results = [f.result() for f in futures]
```

### Caching

- Tool results cached in Supabase (24-hour TTL)
- Previous snapshots cached for delta computation
- ChromaDB query results cached (5-minute TTL)

### Batching

- Batch Supabase writes (100 records per batch)
- Batch ChromaDB indexing (50 documents per batch)

## Testing

### Unit Tests

```bash
pytest tests/test_weekly_pulse.py -v
```

### Integration Tests

```bash
pytest tests/test_pulse_pipeline_integration.py -v --integration
```

### Performance Tests

```bash
pytest tests/test_pulse_performance.py -v --benchmark
```

## Troubleshooting

### Pipeline Fails to Start

- Check ZenML connection: `zenml status`
- Verify environment variables: `zenml stack describe`
- Check Supabase connectivity: `curl $SUPABASE_URL/rest/v1/`

### Slow Pipeline Execution

- Increase `MAX_PARALLEL_SNAPSHOTS`
- Check tool API response times
- Verify ChromaDB performance
- Review network latency

### Missing Previous Snapshots

- Verify digest exists in Supabase: `SELECT * FROM weekly_pulse_digests WHERE client_id = 'xxx'`
- Check digest_data JSON structure
- Ensure period_end matches expected format

### High Error Rate

- Check tool API availability
- Verify API keys are valid
- Review tool timeout settings
- Check network connectivity

## Related Documentation

- [Compliance Service README](../compliance_service/README.md) - Snapshot generation
- [Domain Tools README](../../domain/tools/README.md) - Tool architecture
- [Database README](../../infrastructure/db/README.md) - Storage architecture
- [PULSE_PIPELINE_MVP.md](../../../docs/PULSE_PIPELINE_MVP.md) - Product requirements
