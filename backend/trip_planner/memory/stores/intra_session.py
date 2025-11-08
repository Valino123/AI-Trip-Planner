"""Intra-session memory store using Redis."""
import json
from typing import Dict, Any, List, Optional
from ..connections import RedisConnectionManager
from ..mem_config import MemoryConfig


class IntraSessionMemoryStore:
    """
    Redis-based intra-session memory store.
    Stores temporary conversation state with TTL.
    """

    def __init__(self, redis_manager: RedisConnectionManager, config: MemoryConfig):
        self.redis_manager = redis_manager
        self.config = config

    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def save_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Save a message to session."""
        client = self.redis_manager.get_client()
        if not client:
            return False

        try:
            key = self._get_key(session_id)
            # Append message to list
            client.rpush(key, json.dumps(message, ensure_ascii=False))
            # Set/refresh TTL
            client.expire(key, self.config.INTRA_SESSION_TTL)
            return True
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[IntraSession] Save failed: {e}")
            return False

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from session."""
        client = self.redis_manager.get_client()
        if not client:
            return []

        try:
            key = self._get_key(session_id)
            if limit:
                raw_msgs = client.lrange(key, -limit, -1)  # Get last N messages
            else:
                raw_msgs = client.lrange(key, 0, -1)  # Get all messages
            return [json.loads(msg) for msg in raw_msgs]
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[IntraSession] Get failed: {e}")
            return []

    def clear_session(self, session_id: str) -> bool:
        """Clear session data."""
        client = self.redis_manager.get_client()
        if not client:
            return False

        try:
            key = self._get_key(session_id)
            client.delete(key)
            return True
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[IntraSession] Clear failed: {e}")
            return False

    def refresh_ttl(self, session_id: str) -> bool:
        """Refresh session TTL (sliding window)."""
        client = self.redis_manager.get_client()
        if not client:
            return False

        try:
            key = self._get_key(session_id)
            client.expire(key, self.config.INTRA_SESSION_TTL)
            return True
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[IntraSession] Refresh TTL failed: {e}")
            return False


