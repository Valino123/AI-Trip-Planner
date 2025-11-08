"""Memory system configuration - extends main config."""
import os
from config import config as main_config


class MemoryConfig:
    """Memory system configuration (extends main Config)."""
    
    def __init__(self):
        # Import settings from main config
        self.USE_LTM = main_config.USE_LTM
        self.VERBOSE = main_config.VERBOSE
        
        # Redis Configuration (Intra-session)
        self.REDIS_HOST = getattr(main_config, 'REDIS_HOST', 'localhost')
        self.REDIS_PORT = getattr(main_config, 'REDIS_PORT', 6379)
        self.REDIS_DB = getattr(main_config, 'REDIS_DB', 0)
        self.REDIS_PASSWORD = getattr(main_config, 'REDIS_PASSWORD', None)
        self.INTRA_SESSION_TTL = getattr(main_config, 'INTRA_SESSION_TTL', 7200)

        # MongoDB Configuration (Inter-session + Preferences)
        self.MONGO_URI = getattr(main_config, 'MONGO_URI', 'mongodb://localhost:27017')
        self.MONGO_DB = getattr(main_config, 'MONGO_DB', 'trip_planner')
        self.MONGO_CONVERSATIONS_COLLECTION = getattr(main_config, 'MONGO_CONVERSATIONS_COLLECTION', 'conversations')
        self.MONGO_PREFERENCES_COLLECTION = getattr(main_config, 'MONGO_PREFERENCES_COLLECTION', 'user_preferences')
        
        # Qdrant Configuration (Vector search)
        self.QDRANT_HOST = getattr(main_config, 'QDRANT_HOST', 'localhost')
        self.QDRANT_PORT = getattr(main_config, 'QDRANT_PORT', 6333)
        self.QDRANT_API_KEY = getattr(main_config, 'QDRANT_API_KEY', None)
        self.QDRANT_COLLECTION = getattr(main_config, 'QDRANT_COLLECTION', 'conversations')
        self.VECTOR_DIM = getattr(main_config, 'VECTOR_DIM', 1536)
        # Optional URL/HTTPS toggle. If QDRANT_URL is set, it takes precedence.
        self.QDRANT_URL = getattr(main_config, 'QDRANT_URL', None)
        self.QDRANT_HTTPS = getattr(main_config, 'QDRANT_HTTPS', False)
        
        # Feature Flags
        self.USE_LEGACY_MEMORY = getattr(main_config, 'USE_LEGACY_MEMORY', True)
        self.ENABLE_REDIS_CACHE = getattr(main_config, 'ENABLE_REDIS_CACHE', True)
        self.ENABLE_ASYNC_EMBEDDING = getattr(main_config, 'ENABLE_ASYNC_EMBEDDING', True)
        
        # Embedding Pipeline Configuration
        self.EMBEDDING_QUEUE = "embedding_queue"  # Redis Stream key
        self.EMBEDDING_BATCH_SIZE = 10
        
        # Retrieval Configuration
        self.DEFAULT_RETRIEVAL_K = 6
        self.MIN_SIMILARITY = 0.40


# Singleton instance
memory_config = MemoryConfig()

