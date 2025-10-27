"""Mem0 client wrapper for memory operations."""

from typing import List, Dict, Any, Optional
from loguru import logger

from exim_agent.config import config


class Mem0Client:
    """
    Thin wrapper around Mem0 API for memory operations.
    Provides a clean interface for the application.
    """
    
    def __init__(self):
        """Initialize Mem0 client with config - deferred until initialize() is called."""
        self.memory = None
        self._initialized = False
    
    def initialize(self):
        """Initialize Mem0 with shared ChromaDB client."""
        if self._initialized:
            return
            
        if not config.mem0_enabled:
            logger.info("Mem0 is disabled via config")
            return
            
        try:
            from mem0 import Memory
            from exim_agent.infrastructure.db.chroma_client import chroma_client
            
            # Get shared ChromaDB client
            shared_client = chroma_client.get_client()
            
            # Mem0 will create its own collection on the shared client
            # Note: Must provide 'path' to satisfy Mem0's validation, even though 'client' takes precedence
            mem0_config = {
                "vector_store": {
                    "provider": config.mem0_vector_store,
                    "config": {
                        "collection_name": "mem0_memories",
                        "client": shared_client,
                        "path": config.chroma_db_path,  # Required for validation
                    }
                },
                "llm": {
                    "provider": config.mem0_llm_provider,
                    "config": {
                        "model": config.mem0_llm_model,
                        "temperature": config.llm_temperature,
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": config.mem0_embedder_model,
                    }
                },
                "history_db_path": config.mem0_history_db_path,
            }
            
            # Add API key if using OpenAI
            if config.mem0_llm_provider == "openai":
                mem0_config["llm"]["config"]["api_key"] = config.openai_api_key
            elif config.mem0_llm_provider == "anthropic" and config.anthropic_api_key:
                mem0_config["llm"]["config"]["api_key"] = config.anthropic_api_key
            elif config.mem0_llm_provider == "groq" and config.groq_api_key:
                mem0_config["llm"]["config"]["api_key"] = config.groq_api_key
            
            # Add API key for embedder (OpenAI embedder requires it)
            mem0_config["embedder"]["config"]["api_key"] = config.openai_api_key
            
            self.memory = Memory.from_config(mem0_config)
            self._initialized = True
            logger.info(
                f"Mem0 client initialized (provider={config.mem0_llm_provider}, "
                f"model={config.mem0_llm_model})"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Mem0 client: {e}")
            self.memory = None
            self._initialized = False
    
    def is_enabled(self) -> bool:
        """Check if Mem0 is enabled and initialized."""
        return self.memory is not None
    
    def add(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add conversation to memory.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            user_id: User identifier
            agent_id: Agent identifier
            session_id: Session identifier (mapped to run_id in Mem0)
            metadata: Additional metadata
            
        Returns:
            Memory addition result or empty dict if disabled
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping memory add")
            return {}
            
        try:
            result = self.memory.add(
                messages=messages,
                user_id=user_id,
                agent_id=agent_id,
                run_id=session_id,  # Mem0 uses run_id
                metadata=metadata or {}
            )
            logger.info(f"Added memory for user={user_id}, run={session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return {}
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories.
        
        Args:
            query: Search query
            user_id: Filter by user
            agent_id: Filter by agent
            session_id: Filter by session (mapped to run_id in Mem0)
            limit: Max results
            
        Returns:
            List of relevant memories or empty list if disabled
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping memory search")
            return []
            
        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
                run_id=session_id,  # Mem0 uses run_id
                limit=limit
            )
            logger.info(
                f"Found {len(results)} memories for query='{query[:50]}...', "
                f"user={user_id}, session={session_id}"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a user/agent/session.
        
        Args:
            user_id: Filter by user
            agent_id: Filter by agent
            session_id: Filter by session (mapped to run_id in Mem0)
            
        Returns:
            List of all memories or empty list if disabled
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping get_all")
            return []
            
        try:
            results = self.memory.get_all(
                user_id=user_id,
                agent_id=agent_id,
                run_id=session_id  # Mem0 uses run_id
            )
            logger.info(
                f"Retrieved {len(results)} memories for "
                f"user={user_id}, agent={agent_id}, session={session_id}"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping delete")
            return False
            
        try:
            self.memory.delete(memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    def update(self, memory_id: str, data: str) -> Dict[str, Any]:
        """
        Update a specific memory.
        
        Args:
            memory_id: Memory identifier
            data: New memory content
            
        Returns:
            Update result or empty dict if disabled
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping update")
            return {}
            
        try:
            result = self.memory.update(memory_id, data)
            logger.info(f"Updated memory {memory_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return {}
    
    def history(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Get history of changes for a memory.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            List of history entries or empty list if disabled
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping history")
            return []
            
        try:
            history = self.memory.history(memory_id)
            logger.info(f"Retrieved history for memory {memory_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get memory history {memory_id}: {e}")
            return []
    
    def reset(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Reset memories for user/agent/session.
        
        Args:
            user_id: Filter by user
            agent_id: Filter by agent
            session_id: Filter by session (mapped to run_id in Mem0)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Mem0 not enabled, skipping reset")
            return False
            
        try:
            self.memory.reset(
                user_id=user_id,
                agent_id=agent_id,
                run_id=session_id  # Mem0 uses run_id, not session_id
            )
            logger.info(
                f"Reset memories for user={user_id}, "
                f"agent={agent_id}, session={session_id}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset memories: {e}")
            return False


# Global singleton instance
mem0_client = Mem0Client()
