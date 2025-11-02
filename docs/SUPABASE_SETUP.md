# Supabase Setup Guide

This guide walks you through setting up Supabase for the Compliance Intelligence Platform.

## Quick Setup

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose a project name and database password
3. Wait for the project to be created (usually takes 1-2 minutes)

### 2. Get Your Credentials
1. Go to Settings > API in your Supabase dashboard
2. Copy your Project URL and anon/public key
3. Add them to your `.env` file:

```bash
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_ANON_KEY="your-anon-key-here"
```

### 3. Create the Database Table
1. Go to the SQL Editor in your Supabase dashboard
2. Copy and paste the contents of `data/sql/create_compliance_table.sql`
3. Click "Run" to create the table and indexes

### 4. Test the Connection
Run the configuration tests to verify everything is working:

```bash
python -m pytest tests/test_supabase_config.py -v
```

## Database Schema

The system uses a single table for all compliance data:

```sql
CREATE TABLE compliance_data (
  id SERIAL PRIMARY KEY,
  source_type TEXT NOT NULL,  -- 'hts', 'sanctions', 'refusals', 'rulings'
  source_id TEXT NOT NULL,    -- hts_code, entity_name, etc.
  data JSONB NOT NULL,        -- the actual compliance data
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Usage

The compliance tools automatically store data in Supabase:

```python
from src.exim_agent.domain.tools.hts_tool import HTSTool

# This will fetch data from USITC and store in Supabase
tool = HTSTool()
result = tool.run(hts_code="8517.12.00")
```

## Monitoring

You can monitor the data in your Supabase dashboard:
1. Go to Table Editor > compliance_data
2. View all stored compliance records
3. Filter by source_type to see specific data types

## Troubleshooting

### Connection Issues
- Verify your SUPABASE_URL and SUPABASE_ANON_KEY are correct
- Check that your Supabase project is active
- Ensure the compliance_data table exists

### Permission Issues
- The anon key should have read/write access to the compliance_data table
- Check Row Level Security policies if enabled

### Data Not Appearing
- Check the application logs for Supabase errors
- Verify the tools are calling `_store_hts_data()` successfully
- Use the Supabase dashboard to check for data