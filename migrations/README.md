# Database Migrations

This directory contains SQL migrations for the Supabase/Postgres database.

## Running Migrations

### Option 1: Supabase Dashboard (Recommended for Development)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the migration SQL
4. Click **Run**

### Option 2: Supabase CLI

```bash
# Install Supabase CLI if not already installed
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run the migration
supabase db push --file migrations/001_create_weekly_pulse_digests.sql
```

### Option 3: Direct psql Connection

```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run the migration
\i migrations/001_create_weekly_pulse_digests.sql
```

### Option 4: Python Script (Automated)

```bash
# Run using the migration script
uv run python scripts/run_migrations.py
```

## Migration Files

| File | Description | Status | Date |
|------|-------------|--------|------|
| `001_create_weekly_pulse_digests.sql` | Creates weekly_pulse_digests table for compliance pulse storage | **Required** | 2025-11-01 |
| `002_create_memory_analytics_table.sql` | Creates memory_analytics table for Mem0 usage tracking | **Optional** | 2025-11-01 |
| `003_add_crawling_support.sql` | Adds crawling metadata and audit log tables | **Optional** | 2025-11-01 |
| `004_create_client_portfolios.sql` | Creates client_portfolios table for SKU+Lane configurations | **Required** | 2025-11-07 |

## Table Structure

### `weekly_pulse_digests`

Primary storage for weekly compliance pulse digests.

**Purpose**: Store structured transactional data for weekly compliance digests with fast SQL queries.

**Key Fields**:

- `client_id`: Client identifier
- `period_start` / `period_end`: Pulse period timeframe
- `total_changes`: Number of compliance changes
- `high_priority_changes`: Critical changes requiring action
- `requires_action`: Boolean flag for action items
- `status`: Overall digest status
- `digest_data`: Full JSON payload

**Indexes**:

- Fast queries by client + period
- Filtered index for action-required digests
- GIN index for JSON queries

**Row Level Security**: Enabled for multi-tenant isolation

### `client_portfolios`

Stores client SKU+Lane portfolio configurations for compliance monitoring.

**Purpose**: Define which SKU+Lane combinations each client monitors in the pulse pipeline.

**Key Fields**:

- `client_id`: Client identifier
- `sku_id`: Stock Keeping Unit identifier
- `lane_id`: Trade lane identifier (e.g., CNSHA-USLAX-ocean)
- `hts_code`: Harmonized Tariff Schedule code
- `active`: Whether this SKU+Lane is actively monitored

**Indexes**:

- Fast queries by client + active status
- Indexes on sku_id, lane_id, hts_code for lookups
- Unique constraint on (client_id, sku_id, lane_id)

**Row Level Security**: Enabled for multi-tenant isolation

**Sample Data**: Includes test data for `test-client-001` with 5 SKU+Lane combinations

### `memory_analytics` (Optional)

Time-series tracking of Mem0 memory usage patterns.

**Purpose**: Store analytics snapshots for trend analysis and memory health monitoring.

**Key Fields**:

- `user_id`: User identifier from Mem0
- `total_memories`: Memory count at analysis time
- `avg_memory_length`: Average memory content length
- `memory_types`: JSON breakdown by type
- `insights`: Array of generated insights
- `recommendations`: Array of actionable recommendations

**Indexes**:

- Fast queries by user + date
- GIN index for JSON type queries

**Row Level Security**: Enabled for user isolation

**When to Use**: Only if you need to track memory growth and patterns over time for dashboards/reports.

## Verification

After running migrations, verify the table was created:

```sql
-- Check table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name = 'weekly_pulse_digests';

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'weekly_pulse_digests';

-- Test insert
INSERT INTO weekly_pulse_digests (
  client_id, 
  period_start, 
  period_end, 
  total_changes, 
  high_priority_changes,
  requires_action,
  status,
  digest_data,
  generated_at
) VALUES (
  'test_client',
  NOW() - INTERVAL '7 days',
  NOW(),
  5,
  2,
  true,
  'action_required',
  '{"test": true}'::jsonb,
  NOW()
);

-- Verify
SELECT * FROM weekly_pulse_digests WHERE client_id = 'test_client';
```

## Rollback

To rollback this migration:

```sql
DROP TABLE IF EXISTS weekly_pulse_digests CASCADE;
DROP FUNCTION IF EXISTS update_weekly_pulse_updated_at() CASCADE;
```

## Next Steps

After running migrations:

1. Update your Supabase environment variables in `.env`:

   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key  # For backend operations
   ```

2. Test the connection:

   ```bash
   uv run python -c "from exim_agent.infrastructure.db.supabase_client import supabase_client; print(supabase_client.health_check())"
   ```

3. Run the weekly pulse pipeline:

   ```bash
   uv run python -c "from exim_agent.application.zenml_pipelines.weekly_pulse import weekly_pulse_pipeline; weekly_pulse_pipeline(client_id='test_client')"
   ```
