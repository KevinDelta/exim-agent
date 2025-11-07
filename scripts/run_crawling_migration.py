#!/usr/bin/env python3
"""
Migration script to add crawling support to Supabase schema.
Run this script to apply the crawling-specific database changes.
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client
from exim_agent.config import config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Execute the crawling support migration."""
    
    # Check if Supabase is configured
    if not config.supabase_url or not config.supabase_service_key:
        logger.error("Supabase URL and service key must be configured to run migrations")
        logger.error("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        return False
    
    # Create Supabase client with service role key
    try:
        client: Client = create_client(config.supabase_url, config.supabase_service_key)
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return False
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / "migrations" / "003_add_crawling_support.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        logger.info(f"Loaded migration from {migration_file}")
    except Exception as e:
        logger.error(f"Failed to read migration file: {e}")
        return False
    
    # Execute migration
    try:
        # Split migration into individual statements and execute
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                logger.info(f"Executing statement {i+1}/{len(statements)}")
                client.rpc('exec_sql', {'sql': statement}).execute()
        
        logger.info("Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def verify_migration():
    """Verify that the migration was applied correctly."""
    
    if not config.supabase_url or not config.supabase_service_key:
        logger.error("Supabase not configured for verification")
        return False
    
    try:
        client: Client = create_client(config.supabase_url, config.supabase_service_key)
        
        # Check if new columns exist
        result = client.rpc('exec_sql', {
            'sql': """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'compliance_data' 
            AND column_name IN ('crawl_metadata', 'content_hash', 'last_crawled_at', 'change_detected')
            ORDER BY column_name;
            """
        }).execute()
        
        expected_columns = {'change_detected', 'content_hash', 'crawl_metadata', 'last_crawled_at'}
        found_columns = {row['column_name'] for row in result.data}
        
        if expected_columns.issubset(found_columns):
            logger.info("✓ All new columns added to compliance_data table")
        else:
            missing = expected_columns - found_columns
            logger.error(f"✗ Missing columns: {missing}")
            return False
        
        # Check if new tables exist
        result = client.rpc('exec_sql', {
            'sql': """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('compliance_content_versions', 'crawling_audit_log')
            ORDER BY table_name;
            """
        }).execute()
        
        expected_tables = {'compliance_content_versions', 'crawling_audit_log'}
        found_tables = {row['table_name'] for row in result.data}
        
        if expected_tables.issubset(found_tables):
            logger.info("✓ All new tables created")
        else:
            missing = expected_tables - found_tables
            logger.error(f"✗ Missing tables: {missing}")
            return False
        
        logger.info("Migration verification completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    print("Crawl4AI Compliance Integration - Database Migration")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        success = verify_migration()
    else:
        success = run_migration()
        if success:
            print("\nRunning verification...")
            success = verify_migration()
    
    if success:
        print("\n✓ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Migration failed!")
        sys.exit(1)