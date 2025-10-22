"""Metrics and observability for memory system."""

from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.application.chat_service.session_manager import session_manager


class MemoryMetrics:
    """
    Tracks and reports metrics for memory system.
    
    Metrics tracked:
    - Retrieval metrics (latency, cache hit rate, over-fetch ratio)
    - Memory metrics (total items, promotion rate, salience distribution)
    - Quality metrics (citation rate, precision@k, deduplication rate)
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Retrieval metrics
        self.retrieval_counts = defaultdict(int)  # {tier: count}
        self.retrieval_latencies = defaultdict(list)  # {tier: [latencies]}
        self.cache_hits = 0
        self.cache_misses = 0
        self.over_fetch_samples = []  # List of over-fetch ratios
        
        # Memory metrics
        self.distillation_count = 0
        self.facts_created = 0
        self.duplicates_merged = 0
        self.facts_promoted = 0
        
        # Quality metrics
        self.responses_with_citations = 0
        self.total_responses = 0
        self.citation_counts = []  # List of citation counts per response
        
        # Start time
        self.start_time = datetime.now()
        
        logger.info("MemoryMetrics initialized")
    
    def record_retrieval(
        self,
        tier: str,
        latency_ms: float,
        results_count: int,
        used_count: int = None
    ):
        """
        Record a retrieval operation.
        
        Args:
            tier: Memory tier (WM, EM, SM)
            latency_ms: Retrieval latency in milliseconds
            results_count: Number of results retrieved
            used_count: Number of results actually used (for over-fetch)
        """
        with self.lock:
            self.retrieval_counts[tier] += 1
            self.retrieval_latencies[tier].append(latency_ms)
            
            # Calculate over-fetch ratio if provided
            if used_count is not None and results_count > 0:
                over_fetch_ratio = 1 - (used_count / results_count)
                self.over_fetch_samples.append(over_fetch_ratio)
    
    def record_cache_hit(self):
        """Record a cache hit (e.g., intent classification cache)."""
        with self.lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        with self.lock:
            self.cache_misses += 1
    
    def record_distillation(self, facts_created: int, duplicates_merged: int):
        """
        Record a distillation operation.
        
        Args:
            facts_created: Number of new facts created
            duplicates_merged: Number of duplicates merged
        """
        with self.lock:
            self.distillation_count += 1
            self.facts_created += facts_created
            self.duplicates_merged += duplicates_merged
    
    def record_promotion(self, promoted_count: int):
        """
        Record facts promoted from EM to SM.
        
        Args:
            promoted_count: Number of facts promoted
        """
        with self.lock:
            self.facts_promoted += promoted_count
    
    def record_response(self, citation_count: int):
        """
        Record a generated response.
        
        Args:
            citation_count: Number of citations in the response
        """
        with self.lock:
            self.total_responses += 1
            self.citation_counts.append(citation_count)
            
            if citation_count >= 2:
                self.responses_with_citations += 1
    
    def get_retrieval_metrics(self) -> Dict[str, Any]:
        """Get retrieval performance metrics."""
        with self.lock:
            metrics = {}
            
            # Per-tier latencies
            for tier, latencies in self.retrieval_latencies.items():
                if latencies:
                    metrics[f"{tier}_latency_p50"] = self._percentile(latencies, 50)
                    metrics[f"{tier}_latency_p95"] = self._percentile(latencies, 95)
                    metrics[f"{tier}_latency_p99"] = self._percentile(latencies, 99)
                    metrics[f"{tier}_count"] = self.retrieval_counts[tier]
            
            # Cache metrics
            total_cache = self.cache_hits + self.cache_misses
            if total_cache > 0:
                metrics["cache_hit_rate"] = self.cache_hits / total_cache
            else:
                metrics["cache_hit_rate"] = 0.0
            
            # Over-fetch ratio
            if self.over_fetch_samples:
                metrics["over_fetch_ratio"] = sum(self.over_fetch_samples) / len(self.over_fetch_samples)
            else:
                metrics["over_fetch_ratio"] = 0.0
            
            return metrics
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory system metrics."""
        with self.lock:
            # Session stats
            session_stats = session_manager.get_stats()
            
            # Collection counts
            try:
                sm_count = chroma_client.get_collection().count() if chroma_client._collection else 0
            except:
                sm_count = 0
            
            try:
                em_store = chroma_client.get_episodic_store()
                em_count = em_store._collection.count() if em_store._collection else 0
            except:
                em_count = 0
            
            # Distillation metrics
            dedup_rate = 0.0
            if self.facts_created + self.duplicates_merged > 0:
                dedup_rate = self.duplicates_merged / (self.facts_created + self.duplicates_merged)
            
            # Promotion rate (per week)
            uptime_days = (datetime.now() - self.start_time).days
            promotion_rate_weekly = 0.0
            if uptime_days > 0 and em_count > 0:
                promotion_rate_weekly = (self.facts_promoted / max(1, uptime_days)) * 7 / max(1, em_count)
            
            return {
                "wm_sessions": session_stats["total_sessions"],
                "wm_max_sessions": session_stats["max_sessions"],
                "wm_utilization": session_stats["utilization"],
                "em_facts": em_count,
                "sm_documents": sm_count,
                "distillation_count": self.distillation_count,
                "facts_created": self.facts_created,
                "duplicates_merged": self.duplicates_merged,
                "deduplication_rate": dedup_rate,
                "facts_promoted": self.facts_promoted,
                "promotion_rate_weekly": promotion_rate_weekly
            }
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics."""
        with self.lock:
            # Citation rate
            citation_rate = 0.0
            if self.total_responses > 0:
                citation_rate = self.responses_with_citations / self.total_responses
            
            # Average citations per response
            avg_citations = 0.0
            if self.citation_counts:
                avg_citations = sum(self.citation_counts) / len(self.citation_counts)
            
            return {
                "total_responses": self.total_responses,
                "citation_rate": citation_rate,  # % with 2+ citations
                "avg_citations": avg_citations,
                "responses_with_citations": self.responses_with_citations
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in one call."""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "retrieval": self.get_retrieval_metrics(),
            "memory": self.get_memory_metrics(),
            "quality": self.get_quality_metrics(),
            "config": {
                "enable_memory_system": config.enable_memory_system,
                "enable_intent_classification": config.enable_intent_classification,
                "enable_em_distillation": config.enable_em_distillation,
                "enable_sm_promotion": config.enable_sm_promotion,
                "enable_reranking": config.enable_reranking
            }
        }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.retrieval_counts.clear()
            self.retrieval_latencies.clear()
            self.cache_hits = 0
            self.cache_misses = 0
            self.over_fetch_samples.clear()
            self.distillation_count = 0
            self.facts_created = 0
            self.duplicates_merged = 0
            self.facts_promoted = 0
            self.responses_with_citations = 0
            self.total_responses = 0
            self.citation_counts.clear()
            self.start_time = datetime.now()
            logger.info("Metrics reset")
    
    @staticmethod
    def _percentile(values: list, percentile: int) -> float:
        """Calculate percentile of a list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global singleton instance
memory_metrics = MemoryMetrics()
