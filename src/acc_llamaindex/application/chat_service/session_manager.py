"""Session manager for working memory (WM)."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import threading
from loguru import logger

from acc_llamaindex.config import config


class SessionManager:
    """
    Manages in-memory conversation state for working memory.
    
    Features:
    - LRU eviction when max sessions reached
    - TTL-based cleanup
    - Thread-safe operations
    """
    
    def __init__(self):
        self.sessions: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.lock = threading.Lock()
        logger.info(
            f"SessionManager initialized (max_sessions={config.wm_max_sessions}, "
            f"ttl={config.wm_session_ttl_minutes}min)"
        )
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state or None if not found/expired.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session state dict or None
        """
        with self.lock:
            session = self.sessions.get(session_id)
            
            if session is None:
                return None
            
            # Check if expired
            ttl = timedelta(minutes=config.wm_session_ttl_minutes)
            if datetime.now() - session["last_accessed"] > ttl:
                logger.info(f"Session {session_id} expired")
                del self.sessions[session_id]
                return None
            
            # Move to end (LRU)
            self.sessions.move_to_end(session_id)
            session["last_accessed"] = datetime.now()
            
            return session
    
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            New session state dict
        """
        with self.lock:
            now = datetime.now()
            session = {
                "session_id": session_id,
                "turns": [],
                "created_at": now,
                "last_accessed": now,
                "turn_count": 0
            }
            
            # LRU eviction if at max capacity
            if len(self.sessions) >= config.wm_max_sessions:
                oldest_session_id, oldest_session = self.sessions.popitem(last=False)
                logger.info(
                    f"Evicting oldest session {oldest_session_id} "
                    f"(age: {(now - oldest_session['created_at']).seconds}s)"
                )
            
            self.sessions[session_id] = session
            logger.info(f"Created session {session_id}")
            
            return session
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a conversation turn to the session.
        
        Args:
            session_id: Unique session identifier
            user_message: User's message
            assistant_message: Assistant's response
            metadata: Optional metadata (citations, intent, etc.)
            
        Returns:
            Updated session state
        """
        session = self.get_session(session_id)
        
        if session is None:
            session = self.create_session(session_id)
        
        with self.lock:
            turn = {
                "turn_number": session["turn_count"] + 1,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            session["turns"].append(turn)
            session["turn_count"] += 1
            session["last_accessed"] = datetime.now()
            
            # Keep only last N turns
            if len(session["turns"]) > config.wm_max_turns:
                removed = session["turns"].pop(0)
                logger.debug(f"Removed turn {removed['turn_number']} from session {session_id}")
            
            logger.debug(f"Added turn {turn['turn_number']} to session {session_id}")
            
            return session
    
    def get_recent_turns(
        self,
        session_id: str,
        n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get last N turns from session.
        
        Args:
            session_id: Unique session identifier
            n: Number of turns to retrieve (default: all)
            
        Returns:
            List of turn dicts
        """
        session = self.get_session(session_id)
        
        if session is None:
            return []
        
        turns = session["turns"]
        if n is not None:
            turns = turns[-n:]
        
        return turns
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session {session_id}")
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        with self.lock:
            now = datetime.now()
            ttl = timedelta(minutes=config.wm_session_ttl_minutes)
            
            expired_ids = [
                sid for sid, session in self.sessions.items()
                if now - session["last_accessed"] > ttl
            ]
            
            for sid in expired_ids:
                del self.sessions[sid]
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
            
            return len(expired_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        with self.lock:
            return {
                "total_sessions": len(self.sessions),
                "max_sessions": config.wm_max_sessions,
                "utilization": len(self.sessions) / config.wm_max_sessions
            }


# Global singleton instance
session_manager = SessionManager()
