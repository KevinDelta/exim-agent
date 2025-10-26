"""Memory analytics pipeline for Mem0 insights."""

from zenml import pipeline, step
from typing import Dict, List, Any
from loguru import logger

from exim_agent.application.memory_service.mem0_client import mem0_client


@step
def fetch_user_memories(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all memories for a user."""
    logger.info(f"Fetching memories for user: {user_id}")
    memories = mem0_client.get_all(user_id=user_id)
    logger.info(f"Fetched {len(memories)} memories")
    return memories


@step
def analyze_memory_patterns(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze memory usage patterns."""
    if not memories:
        return {
            "total_memories": 0,
            "memory_types": {},
            "avg_memory_length": 0
        }
    
    total = len(memories)
    
    # Extract stats
    memory_types = {}
    total_length = 0
    
    for mem in memories:
        # Count by type
        mem_type = mem.get("metadata", {}).get("type", "unknown")
        memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
        
        # Track length
        total_length += len(mem.get("memory", ""))
    
    avg_length = total_length / total if total > 0 else 0
    
    logger.info(f"Analyzed {total} memories, avg length: {avg_length:.0f}")
    
    return {
        "total_memories": total,
        "memory_types": memory_types,
        "avg_memory_length": avg_length
    }


@step
def generate_insights(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Generate actionable insights from memory stats."""
    insights = []
    recommendations = []
    
    total = stats["total_memories"]
    avg_length = stats["avg_memory_length"]
    
    # High memory usage
    if total > 100:
        insights.append("High memory usage detected")
        recommendations.append("Consider memory cleanup for inactive sessions")
    elif total == 0:
        insights.append("No memories found")
        recommendations.append("Start conversations to build memory")
    
    # Short memories
    if avg_length < 50 and total > 0:
        insights.append("Memories are very short - quality may be low")
        recommendations.append("Review memory extraction prompts")
    
    # Healthy state
    if total > 10 and total < 100 and avg_length > 50:
        insights.append("Memory system is healthy")
        recommendations.append("Continue current usage patterns")
    
    logger.info(f"Generated {len(insights)} insights")
    
    return {
        "stats": stats,
        "insights": insights,
        "recommendations": recommendations
    }


@pipeline
def memory_analytics_pipeline(user_id: str):
    """
    Analyze Mem0 memory patterns and generate insights.
    
    Args:
        user_id: User identifier to analyze memories for
        
    Returns:
        Dict containing stats, insights, and recommendations
    """
    memories = fetch_user_memories(user_id)
    stats = analyze_memory_patterns(memories)
    insights = generate_insights(stats)
    return insights
