"""Memory management API routes using Mem0."""

from fastapi import APIRouter, HTTPException, status
from typing import Optional
from loguru import logger

from exim_agent.application.memory_service.mem0_client import mem0_client
from exim_agent.infrastructure.api.models import (
    AddMemoryRequest,
    ResetMemoryRequest,
    SearchMemoryRequest,
    UpdateMemoryRequest,
)

router = APIRouter(prefix="/memory", tags=["memory"])


# Routes

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_memory(request: AddMemoryRequest):
    """
    Add conversation to memory.
    
    Mem0 will automatically:
    - Deduplicate similar memories
    - Summarize conversations
    - Extract entities and intents
    - Manage temporal decay
    """
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        result = mem0_client.add(
            messages=request.messages,
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": "Memory added successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add memory: {str(e)}"
        )


@router.post("/search")
async def search_memory(request: SearchMemoryRequest):
    """
    Search memories by query.
    
    Returns relevant memories based on semantic similarity.
    Can filter by user_id, agent_id, or session_id.
    """
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        results = mem0_client.search(
            query=request.query,
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id,
            limit=request.limit
        )
        
        return {
            "status": "success",
            "count": len(results),
            "memories": results
        }
        
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}"
        )


@router.get("/all")
async def get_all_memories(
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Get all memories for a user/agent/session.
    
    If no filters provided, returns all memories (use with caution).
    """
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        results = mem0_client.get_all(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id
        )
        
        return {
            "status": "success",
            "count": len(results),
            "memories": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memories: {str(e)}"
        )


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        success = mem0_client.delete(memory_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found or could not be deleted"
            )
        
        return {
            "status": "success",
            "message": f"Memory {memory_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@router.put("/{memory_id}")
async def update_memory(memory_id: str, request: UpdateMemoryRequest):
    """Update a specific memory by ID."""
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        result = mem0_client.update(memory_id, request.data)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found or could not be updated"
            )
        
        return {
            "status": "success",
            "message": f"Memory {memory_id} updated successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@router.get("/{memory_id}/history")
async def get_memory_history(memory_id: str):
    """Get the change history for a specific memory."""
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        history = mem0_client.history(memory_id)
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Failed to get memory history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory history: {str(e)}"
        )


@router.post("/reset")
async def reset_memories(request: ResetMemoryRequest):
    """
    Reset memories for user/agent/session.
    
    WARNING: This will permanently delete memories.
    If no filters provided, resets ALL memories.
    """
    if not mem0_client.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mem0 is not enabled. Set mem0_enabled=True in config."
        )
    
    try:
        success = mem0_client.reset(
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset memories"
            )
        
        return {
            "status": "success",
            "message": "Memories reset successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset memories: {str(e)}"
        )


@router.get("/health")
async def memory_health():
    """Check if Mem0 is available and healthy."""
    is_enabled = mem0_client.is_enabled()
    
    return {
        "status": "healthy" if is_enabled else "disabled",
        "mem0_enabled": is_enabled,
        "message": "Mem0 is operational" if is_enabled else "Mem0 is not enabled in config"
    }
