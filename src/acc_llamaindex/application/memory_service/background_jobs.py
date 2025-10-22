"""Background jobs for memory maintenance."""

import threading
import time
from typing import Optional
from datetime import datetime
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.application.memory_service.promotion import memory_promoter
from acc_llamaindex.application.memory_service.salience_tracker import salience_tracker


class MemoryBackgroundJobs:
    """
    Manages background maintenance tasks for memory system.
    
    Jobs:
    - Promotion cycle: Run nightly to promote EM → SM
    - Salience decay: Apply weekly decay to all salience scores
    - TTL cleanup: Remove expired EM facts
    - Salience flush: Periodic batch updates
    """
    
    def __init__(self):
        self.running = False
        self.threads = []
        logger.info("MemoryBackgroundJobs initialized")
    
    def start(self):
        """Start all background jobs."""
        if self.running:
            logger.warning("Background jobs already running")
            return
        
        self.running = True
        logger.info("Starting memory background jobs...")
        
        # Start promotion cycle (daily)
        promotion_thread = threading.Thread(
            target=self._run_promotion_cycle,
            daemon=True,
            name="memory-promotion"
        )
        promotion_thread.start()
        self.threads.append(promotion_thread)
        
        # Start salience flush (every 5 minutes)
        flush_thread = threading.Thread(
            target=self._run_salience_flush,
            daemon=True,
            name="salience-flush"
        )
        flush_thread.start()
        self.threads.append(flush_thread)
        
        # Start TTL cleanup (every 6 hours)
        cleanup_thread = threading.Thread(
            target=self._run_ttl_cleanup,
            daemon=True,
            name="ttl-cleanup"
        )
        cleanup_thread.start()
        self.threads.append(cleanup_thread)
        
        # Start session cleanup (every 15 minutes)
        session_cleanup_thread = threading.Thread(
            target=self._run_session_cleanup,
            daemon=True,
            name="session-cleanup"
        )
        session_cleanup_thread.start()
        self.threads.append(session_cleanup_thread)
        
        logger.info(f"Started {len(self.threads)} background job threads")
    
    def stop(self):
        """Stop all background jobs."""
        logger.info("Stopping memory background jobs...")
        self.running = False
        
        # Threads are daemon, so they'll stop when main thread exits
        logger.info("Background jobs stopped")
    
    def _run_promotion_cycle(self):
        """Run promotion cycle daily."""
        logger.info("Promotion cycle thread started")
        
        while self.running:
            try:
                # Wait 24 hours between runs
                # First run happens after 24 hours
                time.sleep(24 * 60 * 60)  # 24 hours
                
                if not self.running:
                    break
                
                if not config.enable_sm_promotion:
                    continue
                
                logger.info("Running promotion cycle...")
                result = memory_promoter.run_promotion_cycle()
                
                logger.info(
                    f"Promotion cycle complete: {result.get('promoted', 0)} facts promoted"
                )
                
            except Exception as e:
                logger.error(f"Promotion cycle error: {e}")
                # Continue running despite errors
    
    def _run_salience_flush(self):
        """Flush salience updates periodically."""
        logger.info("Salience flush thread started")
        
        while self.running:
            try:
                # Wait 5 minutes between flushes
                time.sleep(5 * 60)  # 5 minutes
                
                if not self.running:
                    break
                
                # Flush pending salience updates
                salience_tracker.flush()
                
            except Exception as e:
                logger.error(f"Salience flush error: {e}")
    
    def _run_ttl_cleanup(self):
        """Clean up expired facts periodically."""
        logger.info("TTL cleanup thread started")
        
        while self.running:
            try:
                # Wait 6 hours between cleanups
                time.sleep(6 * 60 * 60)  # 6 hours
                
                if not self.running:
                    break
                
                logger.info("Running TTL cleanup...")
                removed = memory_promoter.cleanup_expired_facts()
                
                logger.info(f"TTL cleanup complete: {removed} facts removed")
                
            except Exception as e:
                logger.error(f"TTL cleanup error: {e}")
    
    def _run_session_cleanup(self):
        """Clean up expired sessions periodically."""
        logger.info("Session cleanup thread started")
        
        while self.running:
            try:
                # Wait 15 minutes between cleanups
                time.sleep(15 * 60)  # 15 minutes
                
                if not self.running:
                    break
                
                logger.info("Running session cleanup...")
                from acc_llamaindex.application.chat_service.session_manager import session_manager
                
                cleaned = session_manager.cleanup_expired_sessions()
                
                logger.info(f"Session cleanup complete: {cleaned} sessions removed")
                
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    def run_manual_promotion(self) -> dict:
        """Manually trigger a promotion cycle."""
        logger.info("Manual promotion cycle triggered")
        
        if not config.enable_sm_promotion:
            return {
                "status": "disabled",
                "message": "SM promotion is disabled in config"
            }
        
        try:
            result = memory_promoter.run_promotion_cycle()
            return result
        except Exception as e:
            logger.error(f"Manual promotion failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_manual_cleanup(self) -> dict:
        """Manually trigger TTL cleanup."""
        logger.info("Manual TTL cleanup triggered")
        
        try:
            removed = memory_promoter.cleanup_expired_facts()
            return {
                "status": "success",
                "removed": removed
            }
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_status(self) -> dict:
        """Get status of background jobs."""
        return {
            "running": self.running,
            "threads": len(self.threads),
            "thread_names": [t.name for t in self.threads if t.is_alive()],
            "config": {
                "enable_sm_promotion": config.enable_sm_promotion,
                "enable_em_distillation": config.enable_em_distillation
            }
        }


# Global singleton instance
background_jobs = MemoryBackgroundJobs()
