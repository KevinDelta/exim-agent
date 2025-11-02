#!/usr/bin/env python3
"""Run database migrations for Supabase/Postgres."""

import sys
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from exim_agent.infrastructure.db.supabase_client import supabase_client


def run_migration(migration_file: Path) -> bool:
    """
    Run a SQL migration file.
    
    Args:
        migration_file: Path to SQL migration file
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Running migration: {migration_file.name}")
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    try:
        # Read SQL content
        sql_content = migration_file.read_text()
        
        # Execute SQL using Supabase client
        if not supabase_client._client:
            logger.error("Supabase client not initialized. Check your configuration.")
            return False
        
        # Note: Supabase Python client doesn't directly support raw SQL execution
        # You'll need to run this through the dashboard or use psycopg2 directly
        logger.warning(
            "This script requires manual execution. "
            "Please run the SQL file through Supabase dashboard or psql."
        )
        
        logger.info(f"Migration file: {migration_file.absolute()}")
        logger.info("\nTo run manually:")
        logger.info("1. Copy the SQL from the file above")
        logger.info("2. Go to Supabase Dashboard > SQL Editor")
        logger.info("3. Paste and execute the SQL")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to read migration file: {e}")
        return False


def main():
    """Run all pending migrations."""
    logger.info("Starting database migrations...")
    
    # Check Supabase connection
    if not supabase_client.health_check():
        logger.error(
            "Supabase connection failed. "
            "Please check your SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
        )
        sys.exit(1)
    
    logger.info("✓ Supabase connection verified")
    
    # Get migrations directory
    migrations_dir = project_root / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    # Get all SQL files in order
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.warning("No migration files found")
        sys.exit(0)
    
    logger.info(f"Found {len(migration_files)} migration file(s)")
    
    # Run migrations
    success_count = 0
    for migration_file in migration_files:
        if run_migration(migration_file):
            success_count += 1
        else:
            logger.error(f"Migration failed: {migration_file.name}")
            sys.exit(1)
    
    logger.info(f"\n✓ Processed {success_count}/{len(migration_files)} migrations")
    logger.info("\nNext steps:")
    logger.info("1. Run the migrations manually through Supabase dashboard")
    logger.info("2. Verify tables were created successfully")
    logger.info("3. Test the weekly pulse pipeline")


if __name__ == "__main__":
    main()
