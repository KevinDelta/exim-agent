-- Migration: Create memory_analytics table for tracking Mem0 usage patterns
-- Description: Optional table for time-series memory analytics (Supabase/Postgres)
-- Author: Memory Analytics Pipeline
-- Date: 2025-11-01
-- Status: OPTIONAL - Only needed if tracking memory trends over time

-- Create the memory_analytics table
CREATE TABLE IF NOT EXISTS memory_analytics (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  total_memories INT NOT NULL DEFAULT 0,
  avg_memory_length FLOAT NOT NULL DEFAULT 0,
  memory_types JSONB NOT NULL DEFAULT '{}'::jsonb,
  insights TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  recommendations TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  analyzed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT valid_memory_count CHECK (total_memories >= 0),
  CONSTRAINT valid_avg_length CHECK (avg_memory_length >= 0)
);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_memory_analytics_user_analyzed 
  ON memory_analytics(user_id, analyzed_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_analytics_analyzed_at 
  ON memory_analytics(analyzed_at DESC);

-- Create GIN index for JSONB queries on memory_types
CREATE INDEX IF NOT EXISTS idx_memory_analytics_memory_types 
  ON memory_analytics USING GIN (memory_types);

-- Add comments for documentation
COMMENT ON TABLE memory_analytics IS 'Tracks Mem0 memory usage patterns and insights over time';
COMMENT ON COLUMN memory_analytics.user_id IS 'User identifier from Mem0';
COMMENT ON COLUMN memory_analytics.total_memories IS 'Total number of memories at analysis time';
COMMENT ON COLUMN memory_analytics.avg_memory_length IS 'Average character length of memories';
COMMENT ON COLUMN memory_analytics.memory_types IS 'Breakdown of memory types as JSON';
COMMENT ON COLUMN memory_analytics.insights IS 'Generated insights from pattern analysis';
COMMENT ON COLUMN memory_analytics.recommendations IS 'Actionable recommendations based on patterns';
COMMENT ON COLUMN memory_analytics.analyzed_at IS 'Timestamp when analysis was performed';

-- Enable Row Level Security (RLS) for multi-tenant access
ALTER TABLE memory_analytics ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only see their own analytics
CREATE POLICY user_isolation_policy ON memory_analytics
  FOR SELECT
  USING (user_id = current_setting('app.current_user_id', TRUE)::TEXT);

-- Create policy for service role to access all analytics
CREATE POLICY service_role_policy ON memory_analytics
  FOR ALL
  USING (current_setting('request.jwt.claims', TRUE)::json->>'role' = 'service_role');

-- Sample queries for reference
-- 
-- Get user's analytics history:
-- SELECT * FROM memory_analytics WHERE user_id = 'user123' ORDER BY analyzed_at DESC;
--
-- Track memory growth over time:
-- SELECT analyzed_at::date, total_memories, avg_memory_length 
-- FROM memory_analytics 
-- WHERE user_id = 'user123' 
-- ORDER BY analyzed_at;
--
-- Find users with high memory usage:
-- SELECT DISTINCT ON (user_id) user_id, total_memories, analyzed_at
-- FROM memory_analytics
-- WHERE total_memories > 100
-- ORDER BY user_id, analyzed_at DESC;
