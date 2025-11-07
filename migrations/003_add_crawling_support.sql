-- Migration: Add crawling support to compliance_data table
-- Description: Extends existing compliance_data table with crawling-specific columns
-- Author: Crawl4AI Integration
-- Date: 2025-11-04

-- Add crawling-specific columns to existing compliance_data table
ALTER TABLE compliance_data 
ADD COLUMN IF NOT EXISTS crawl_metadata JSONB,
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS last_crawled_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS change_detected BOOLEAN DEFAULT FALSE;

-- Create indexes for efficient crawled content queries and change detection
CREATE INDEX IF NOT EXISTS idx_compliance_data_crawl_metadata 
  ON compliance_data USING GIN (crawl_metadata);

CREATE INDEX IF NOT EXISTS idx_compliance_data_content_hash 
  ON compliance_data (content_hash);

CREATE INDEX IF NOT EXISTS idx_compliance_data_last_crawled_at 
  ON compliance_data (last_crawled_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_data_change_detected 
  ON compliance_data (change_detected, last_crawled_at DESC) 
  WHERE change_detected = TRUE;

-- Create composite index for crawling queries
CREATE INDEX IF NOT EXISTS idx_compliance_data_crawl_composite 
  ON compliance_data (source_type, last_crawled_at DESC, change_detected);

-- Add comments for documentation
COMMENT ON COLUMN compliance_data.crawl_metadata IS 'JSON metadata from crawling operations including source attribution, extraction confidence, and regulatory authority';
COMMENT ON COLUMN compliance_data.content_hash IS 'SHA-256 hash of content for change detection and deduplication';
COMMENT ON COLUMN compliance_data.last_crawled_at IS 'Timestamp when content was last crawled or updated';
COMMENT ON COLUMN compliance_data.change_detected IS 'Flag indicating if content changes were detected during last crawl';

-- Create content versioning table for audit trail support
CREATE TABLE IF NOT EXISTS compliance_content_versions (
  id BIGSERIAL PRIMARY KEY,
  compliance_data_id BIGINT NOT NULL REFERENCES compliance_data(id) ON DELETE CASCADE,
  version_number INT NOT NULL,
  content_hash VARCHAR(64) NOT NULL,
  data JSONB NOT NULL,
  crawl_metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT valid_version_number CHECK (version_number > 0),
  UNIQUE (compliance_data_id, version_number)
);

-- Create indexes for content versioning
CREATE INDEX IF NOT EXISTS idx_compliance_versions_data_id 
  ON compliance_content_versions (compliance_data_id, version_number DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_versions_content_hash 
  ON compliance_content_versions (content_hash);

CREATE INDEX IF NOT EXISTS idx_compliance_versions_created_at 
  ON compliance_content_versions (created_at DESC);

-- Create GIN index for crawl_metadata queries
CREATE INDEX IF NOT EXISTS idx_compliance_versions_crawl_metadata 
  ON compliance_content_versions USING GIN (crawl_metadata);

-- Add comments for versioning table
COMMENT ON TABLE compliance_content_versions IS 'Stores historical versions of compliance content for audit trail and change tracking';
COMMENT ON COLUMN compliance_content_versions.compliance_data_id IS 'Reference to main compliance_data record';
COMMENT ON COLUMN compliance_content_versions.version_number IS 'Sequential version number starting from 1';
COMMENT ON COLUMN compliance_content_versions.content_hash IS 'SHA-256 hash of the content at this version';
COMMENT ON COLUMN compliance_content_versions.data IS 'Full content data at this version';
COMMENT ON COLUMN compliance_content_versions.crawl_metadata IS 'Crawling metadata at time of version creation';

-- Create function to automatically create content versions
CREATE OR REPLACE FUNCTION create_content_version()
RETURNS TRIGGER AS $
BEGIN
  -- Only create version if content actually changed
  IF OLD.content_hash IS DISTINCT FROM NEW.content_hash THEN
    INSERT INTO compliance_content_versions (
      compliance_data_id,
      version_number,
      content_hash,
      data,
      crawl_metadata
    )
    SELECT 
      NEW.id,
      COALESCE(MAX(version_number), 0) + 1,
      NEW.content_hash,
      NEW.data,
      NEW.crawl_metadata
    FROM compliance_content_versions 
    WHERE compliance_data_id = NEW.id;
  END IF;
  
  RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Create trigger for automatic versioning
CREATE TRIGGER trigger_create_content_version
  AFTER UPDATE ON compliance_data
  FOR EACH ROW
  EXECUTE FUNCTION create_content_version();

-- Create crawling audit log table for operational monitoring
CREATE TABLE IF NOT EXISTS crawling_audit_log (
  id BIGSERIAL PRIMARY KEY,
  source_url TEXT NOT NULL,
  source_type TEXT NOT NULL,
  operation_type TEXT NOT NULL CHECK (operation_type IN ('discover', 'extract', 'store', 'error')),
  status TEXT NOT NULL CHECK (status IN ('success', 'failure', 'partial')),
  metadata JSONB,
  error_message TEXT,
  execution_time_ms INT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT valid_execution_time CHECK (execution_time_ms >= 0)
);

-- Create indexes for audit log queries
CREATE INDEX IF NOT EXISTS idx_crawling_audit_source_type 
  ON crawling_audit_log (source_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_crawling_audit_status 
  ON crawling_audit_log (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_crawling_audit_operation 
  ON crawling_audit_log (operation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_crawling_audit_url 
  ON crawling_audit_log (source_url, created_at DESC);

-- Create GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_crawling_audit_metadata 
  ON crawling_audit_log USING GIN (metadata);

-- Add comments for audit log table
COMMENT ON TABLE crawling_audit_log IS 'Audit trail for all crawling operations and their outcomes';
COMMENT ON COLUMN crawling_audit_log.source_url IS 'URL that was crawled or attempted';
COMMENT ON COLUMN crawling_audit_log.source_type IS 'Type of compliance source (hts, sanctions, rulings, refusals)';
COMMENT ON COLUMN crawling_audit_log.operation_type IS 'Type of operation performed (discover, extract, store, error)';
COMMENT ON COLUMN crawling_audit_log.status IS 'Outcome of the operation (success, failure, partial)';
COMMENT ON COLUMN crawling_audit_log.metadata IS 'Additional operation metadata including extraction confidence, rate limits, etc.';
COMMENT ON COLUMN crawling_audit_log.error_message IS 'Error details if operation failed';
COMMENT ON COLUMN crawling_audit_log.execution_time_ms IS 'Operation execution time in milliseconds';

-- Enable Row Level Security for new tables
ALTER TABLE compliance_content_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawling_audit_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for service role access
CREATE POLICY service_role_policy_versions ON compliance_content_versions
  FOR ALL
  USING (current_setting('request.jwt.claims', TRUE)::json->>'role' = 'service_role');

CREATE POLICY service_role_policy_audit ON crawling_audit_log
  FOR ALL
  USING (current_setting('request.jwt.claims', TRUE)::json->>'role' = 'service_role');

-- Sample queries for reference
--
-- Find content with recent changes:
-- SELECT * FROM compliance_data 
-- WHERE change_detected = TRUE 
-- AND last_crawled_at > NOW() - INTERVAL '24 hours'
-- ORDER BY last_crawled_at DESC;
--
-- Get content version history:
-- SELECT v.version_number, v.content_hash, v.created_at, v.crawl_metadata
-- FROM compliance_content_versions v
-- JOIN compliance_data d ON v.compliance_data_id = d.id
-- WHERE d.source_type = 'hts' AND d.source_id = '1234.56.78'
-- ORDER BY v.version_number DESC;
--
-- Monitor crawling performance:
-- SELECT source_type, operation_type, status, 
--        COUNT(*) as operations,
--        AVG(execution_time_ms) as avg_time_ms
-- FROM crawling_audit_log 
-- WHERE created_at > NOW() - INTERVAL '1 day'
-- GROUP BY source_type, operation_type, status
-- ORDER BY source_type, operation_type;