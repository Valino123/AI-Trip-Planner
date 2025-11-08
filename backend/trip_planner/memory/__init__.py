"""
Memory system for AI Trip Planner.

Production implementation (Redis + MongoDB + Qdrant):

Usage:
    from trip_planner.memory import ProductionMemoryManager, create_memory_manager
    mem = create_memory_manager()
"""

from .mem_config import MemoryConfig, memory_config
from .models import MemoryItem, MemoryType
from .manager import ProductionMemoryManager, create_memory_manager
from .connections import (
    RedisConnectionManager,
    MongoConnectionManager,
    QdrantConnectionManager,
)
from .stores import IntraSessionMemoryStore
from .stores import InterSessionMemoryStore
from .stores import UserPreferenceStore

PRODUCTION_AVAILABLE = True


# Export public API
__all__ = [
    # Configuration
    "MemoryConfig",
    "memory_config",

    # Production system
    "MemoryItem",
    "MemoryType",
    "ProductionMemoryManager",
    "create_memory_manager",
    
    # Connection managers
    "RedisConnectionManager",
    "MongoConnectionManager",
    "QdrantConnectionManager",
    
    # Memory stores
    "IntraSessionMemoryStore",
    "InterSessionMemoryStore",
    "UserPreferenceStore",
    
    # Feature flag
    "PRODUCTION_AVAILABLE",
]

