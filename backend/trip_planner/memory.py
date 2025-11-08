# memory.py
"""
Memory system - re-exports from memory package.

Production multi-tier system (Redis + MongoDB + Qdrant):
    pip install redis pymongo qdrant-client

Usage:
    from trip_planner.memory import create_memory_manager
    mem = create_memory_manager()
"""

# Re-export everything from memory package
from .memory import *  # noqa: F401, F403

# Explicit re-exports for common symbols
from .memory import (
    memory_config,
    PRODUCTION_AVAILABLE,
    MemoryItem,
    MemoryType,
    ProductionMemoryManager,
    create_memory_manager,
)
