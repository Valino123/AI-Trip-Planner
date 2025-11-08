import os 
from dotenv import load_dotenv 
from typing import List

# Always load environment from CWD, then explicitly from backend/.env, and optional backend/.env.memory.dev
# so scripts run from repo root or backend both work without manual export
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# First: default search (CWD)
load_dotenv()
# Then: backend/.env
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
# Optional dev file overrides
_dev_path = os.path.join(_BACKEND_DIR, ".env.memory.dev")
if os.path.exists(_dev_path):
    load_dotenv(_dev_path, override=True)

class Config:
    
    def __init__(self):
        # Server Config
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8080"))
        # Chat backbone
        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
        self.BASE_URL = os.getenv("BASE_URL")
        self.QWEN_MODEL = os.getenv("QWEN_MODEL") 
        self.QWEN_TEMPERATURE = os.getenv("QWEN_TEMPERATURE") 
        self.QWEN_MAX_TOKENS = os.getenv("QWEN_MAX_TOKENS") 
        # Embedding
        self.EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT") 
        self.EMBEDDING_MODE = os.getenv("EMBEDDING_MODE") 
        self.EMBEDDING_AZURE_ENDPOINT = os.getenv("EMBEDDING_AZURE_ENDPOINT")
        self.EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") 
        self.EMBEDDING_API_VERSION = os.getenv("EMBEDDING_API_VERSION")
        # Chat config
        self.USE_LTM = os.getenv("USE_LTM", "True").lower() == "true"
        self.DATA_ROOT = os.getenv("DATA_ROOT", "./data")
        self.VERBOSE = os.getenv("VERBOSE", "True").lower() == "true"
        self.MAX_TURNS = int(os.getenv("MAX_TURNS", "16"))
        self.KEEP_SYSTEM = int(os.getenv("KEEP_SYSTEM", "2"))
        self.MAX_TURNS_IN_CONTEXT = int(os.getenv("MAX_TURNS_IN_CONTEXT", "5"))
        
        # ===== Production Memory Configuration =====
        # Redis (Intra-session memory)
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
        self.INTRA_SESSION_TTL = int(os.getenv("INTRA_SESSION_TTL", "7200"))  # 2 hours
        
        # MongoDB (Inter-session + Preferences)
        self.MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.MONGO_DB = os.getenv("MONGO_DB", "trip_planner")
        self.MONGO_CONVERSATIONS_COLLECTION = os.getenv("MONGO_CONVERSATIONS_COLLECTION", "conversations")
        self.MONGO_PREFERENCES_COLLECTION = os.getenv("MONGO_PREFERENCES_COLLECTION", "user_preferences")
        
        # PostgreSQL (Inter-session + Preferences)
        self.PG_HOST = os.getenv("PG_HOST", "localhost")
        self.PG_PORT = int(os.getenv("PG_PORT", "5432"))
        self.PG_USER = os.getenv("PG_USER", "postgres")
        self.PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
        self.PG_DATABASE = os.getenv("PG_DATABASE", "trip_planner")
        self.PG_POOL_SIZE = int(os.getenv("PG_POOL_SIZE", "10"))
        self.PG_MAX_OVERFLOW = int(os.getenv("PG_MAX_OVERFLOW", "20"))
        
        # Qdrant (Vector search)
        self.QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
        self.QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
        self.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "conversations")
        self.VECTOR_DIM = int(os.getenv("VECTOR_DIM", "1536"))
        
        # Memory Feature Flags
        self.USE_LEGACY_MEMORY = os.getenv("USE_LEGACY_MEMORY", "True").lower() == "true"  # Default to legacy for now
        self.ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "True").lower() == "true"
        self.ENABLE_ASYNC_EMBEDDING = os.getenv("ENABLE_ASYNC_EMBEDDING", "True").lower() == "true"

    def get(self, key: str, default=None):
        return getattr(self, key, default)
config = Config()