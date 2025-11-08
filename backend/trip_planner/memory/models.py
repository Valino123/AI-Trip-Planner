"""Data models for memory system."""
from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum


class MemoryType(str, Enum):
    """Memory type classification."""
    INTRA_SESSION = "intra_session"      # Within single conversation
    INTER_SESSION = "inter_session"      # Across conversations
    USER_PREFERENCE = "user_preference"  # Long-term user data
    PROFILE = "profile"                  # User profile info
    TURN = "turn"                        # Q&A turn


@dataclass
class MemoryItem:
    """Unified memory item structure."""
    id: str
    user_id: str
    session_id: Optional[str]
    memory_type: MemoryType
    content: str
    created_at: float
    updated_at: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else self.memory_type,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata or {},
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            session_id=data.get("session_id"),
            memory_type=MemoryType(data["memory_type"]),
            content=data["content"],
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            version=data.get("version", 1)
        )


