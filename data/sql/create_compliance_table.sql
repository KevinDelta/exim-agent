-- Create compliance_data table for storing all compliance data
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS compliance_data (
  id SERIAL PRIMARY KEY,
  source_type TEXT NOT NULL CHECK (source_type IN ('hts', 'sanctions', 'refusals', 'rulings')),
  source_id TEXT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique index to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS compliance_data_unique_source 
ON compliance_data (source_type, source_id);

-- Create index for faster queries by source_type
CREATE INDEX IF NOT EXISTS compliance_data_source_type_idx 
ON compliance_data (source_type);

-- Create index for faster queries by created_at
CREATE INDEX IF NOT EXISTS compliance_data_created_at_idx 
ON compliance_data (created_at);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_compliance_data_updated_at ON compliance_data;
CREATE TRIGGER update_compliance_data_updated_at
    BEFORE UPDATE ON compliance_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (optional - for production)
-- ALTER TABLE compliance_data ENABLE ROW LEVEL SECURITY;

-- Create policy for authenticated users (optional - for production)
-- CREATE POLICY "Enable all operations for authenticated users" ON compliance_data
--   FOR ALL USING (auth.role() = 'authenticated');