"""Unified production memory manager."""
from typing import Dict, Any, List, Tuple, Optional
from .mem_config import MemoryConfig, memory_config
from .models import MemoryItem
from .connections import RedisConnectionManager, MongoConnectionManager, QdrantConnectionManager
from .stores import IntraSessionMemoryStore
from .stores import InterSessionMemoryStore
from .stores import UserPreferenceStore


class ProductionMemoryManager:
    """
    Unified memory manager orchestrating all memory tiers:
    - Intra-session: Redis (fast, temporary)
    - Inter-session: MongoDB + Qdrant (persistent, searchable)
    - User preferences: MongoDB + Redis cache (consistent, fast)
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or memory_config
        
        # Connection managers
        self.redis_manager = RedisConnectionManager(self.config)
        self.mongo_manager = MongoConnectionManager(self.config)
        self.qdrant_manager = QdrantConnectionManager(self.config)
        
        # Memory stores
        self.intra_session = IntraSessionMemoryStore(self.redis_manager, self.config)
        self.inter_session = InterSessionMemoryStore(
            self.mongo_manager,
            self.qdrant_manager,
            self.config,
        )
        self.user_preferences = UserPreferenceStore(
            self.mongo_manager,
            self.redis_manager,
            self.config,
        )
    
    # ==================== Intra-session Operations ====================
    
    def save_message_to_session(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Save message to active session (Redis)."""
        return self.intra_session.save_message(session_id, message)
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from active session."""
        return self.intra_session.get_messages(session_id, limit)
    
    def refresh_session_ttl(self, session_id: str) -> bool:
        """Refresh session TTL (sliding window)."""
        return self.intra_session.refresh_ttl(session_id)
    
    # ==================== Inter-session Operations ====================
    
    def finalize_session(self, user_id: str, session_id: str) -> bool:
        """
        Finalize session: Move from Redis to MongoDB + queue embeddings.
        Called when session expires or is explicitly closed.
        """
        # 1. Get messages from Redis
        messages = self.intra_session.get_messages(session_id)
        if not messages:
            return True
        
        # 2. Save to MongoDB
        success = self.inter_session.save_conversation(user_id, session_id, messages)
        
        # 3. Queue embedding job if async is enabled
        if success and self.config.ENABLE_ASYNC_EMBEDDING:
            summary = self._create_conversation_summary(messages)
            self.inter_session.queue_embedding_job(user_id, session_id, summary)
        
        # 4. Clear from Redis
        self.intra_session.clear_session(session_id)
        
        return success
    
    def retrieve_relevant_memories(self, user_id: str, query: str, 
                                   k: Optional[int] = None, min_similarity: Optional[float] = None,
                                   verbose: bool = False) -> List[Tuple[MemoryItem, float]]:
        """Retrieve relevant memories from past conversations (filtered to this user)."""
        k_val = k if isinstance(k, int) and k > 0 else self.config.DEFAULT_RETRIEVAL_K
        min_sim = min_similarity if isinstance(min_similarity, (int, float)) else self.config.MIN_SIMILARITY
        return self.inter_session.retrieve_similar(
            user_id, query, k_val, min_sim, verbose
        )
    
    # ==================== User Preference Operations ====================
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences (cached)."""
        return self.user_preferences.get_preferences(user_id) or {}
    
    def update_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Update single preference."""
        return self.user_preferences.update_preference(user_id, key, value)
    
    # ==================== Helper Methods ====================
    
    def _create_conversation_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create conversation summary for embedding."""
        pairs = []
        for i in range(0, len(messages) - 1, 2):
            if i + 1 < len(messages):
                user_msg = messages[i].get("content", "")
                agent_msg = messages[i + 1].get("content", "")
                pairs.append(f"Q: {user_msg[:200]}\nA: {agent_msg[:200]}")
        return "\n\n".join(pairs)[:800]
    
    def format_memories_for_context(self, memories: List[Tuple[MemoryItem, float]], 
                                    max_chars: int = 800) -> str:
        """Format retrieved memories for injection into context."""
        if not memories:
            return ""
        
        lines = []
        for item, score in memories:
            memory_type = item.memory_type.value
            content_preview = item.content[:200]
            lines.append(f"- ({memory_type}, similarity={score:.2f}) {content_preview}")
            if sum(len(x) for x in lines) > max_chars:
                break
        
        return "Relevant context from past conversations:\n" + "\n".join(lines)
    
    def close(self):
        """Close all connections."""
        self.redis_manager.close()
        self.mongo_manager.close()
        self.qdrant_manager.close()


def create_memory_manager(use_production: bool = None) -> 'ProductionMemoryManager':
    """
    Factory function to create appropriate memory manager.
    
    Args:
        use_production: If None, uses config.USE_LEGACY_MEMORY to decide
                       If True, force production system
                       If False, force legacy system
    
    Returns:
        Memory manager instance
    """
    # Legacy system removed; always return production manager
    if memory_config.VERBOSE:
        print("[Memory] Initializing production memory system (MongoDB + Qdrant)...")
    return ProductionMemoryManager(memory_config)

