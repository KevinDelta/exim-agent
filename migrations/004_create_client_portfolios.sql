-- Migration: Create client_portfolios table for storing client SKU+Lane configurations
-- Description: Stores the portfolio of SKU+Lane combinations that each client monitors
-- Author: Compliance Pulse System
-- Date: 2025-11-07

-- Create the client_portfolios table
CREATE TABLE IF NOT EXISTS client_portfolios (
  id BIGSERIAL PRIMARY KEY,
  client_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  lane_id TEXT NOT NULL,
  hts_code TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT unique_client_sku_lane UNIQUE (client_id, sku_id, lane_id),
  CONSTRAINT valid_hts_code CHECK (LENGTH(hts_code) >= 6)
);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_client_portfolios_client_active 
  ON client_portfolios(client_id, active) 
  WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_client_portfolios_sku 
  ON client_portfolios(sku_id);

CREATE INDEX IF NOT EXISTS idx_client_portfolios_lane 
  ON client_portfolios(lane_id);

CREATE INDEX IF NOT EXISTS idx_client_portfolios_hts 
  ON client_portfolios(hts_code);

-- Create trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_client_portfolios_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_client_portfolios_updated_at
  BEFORE UPDATE ON client_portfolios
  FOR EACH ROW
  EXECUTE FUNCTION update_client_portfolios_updated_at();

-- Add comments for documentation
COMMENT ON TABLE client_portfolios IS 'Stores client SKU+Lane portfolio configurations for compliance monitoring';
COMMENT ON COLUMN client_portfolios.client_id IS 'Unique client identifier';
COMMENT ON COLUMN client_portfolios.sku_id IS 'Stock Keeping Unit identifier';
COMMENT ON COLUMN client_portfolios.lane_id IS 'Trade lane identifier (e.g., CNSHA-USLAX-ocean)';
COMMENT ON COLUMN client_portfolios.hts_code IS 'Harmonized Tariff Schedule code for the SKU';
COMMENT ON COLUMN client_portfolios.active IS 'Whether this SKU+Lane combination is actively monitored';

-- Enable Row Level Security (RLS) for multi-tenant access
ALTER TABLE client_portfolios ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only see their own client's portfolio
CREATE POLICY client_portfolio_isolation_policy ON client_portfolios
  FOR SELECT
  USING (client_id = current_setting('app.current_client_id', TRUE)::TEXT);

-- Create policy for service role to access all portfolios
CREATE POLICY service_role_portfolio_policy ON client_portfolios
  FOR ALL
  USING (current_setting('request.jwt.claims', TRUE)::json->>'role' = 'service_role');

-- Insert sample data for testing
INSERT INTO client_portfolios (client_id, sku_id, lane_id, hts_code, active) VALUES
  ('test-client-001', 'SKU-001', 'CNSHA-USLAX-ocean', '8517.12.00', TRUE),
  ('test-client-001', 'SKU-002', 'CNSHA-USLAX-ocean', '6203.42.40', TRUE),
  ('test-client-001', 'SKU-003', 'MXNLD-USTX-truck', '8471.30.01', TRUE),
  ('test-client-001', 'SKU-004', 'VNSGN-USLAX-ocean', '9403.60.80', TRUE),
  ('test-client-001', 'SKU-005', 'CNSHA-USNYC-ocean', '8528.72.64', TRUE)
ON CONFLICT (client_id, sku_id, lane_id) DO NOTHING;
