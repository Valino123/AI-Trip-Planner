"""MongoDB connection manager for inter-session conversations and user preferences."""
from typing import Optional
from ..mem_config import MemoryConfig


class MongoConnectionManager:
    """Manages MongoDB client and database handle."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._client = None
        self._db = None

    def get_client(self):
        if self._client is None:
            try:
                from pymongo import MongoClient
                self._client = MongoClient(
                    self.config.MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                )
                # Test connection
                self._client.admin.command("ping")
                if self.config.VERBOSE:
                    print(f"[MongoDB] Connected to {self.config.MONGO_URI}")
            except ImportError:
                if self.config.VERBOSE:
                    print("[MongoDB] WARNING: pymongo not installed. Install: pip install pymongo")
                self._client = None
            except Exception as e:
                if self.config.VERBOSE:
                    print(f"[MongoDB] WARNING: Connection failed: {e}")
                self._client = None
        return self._client

    def get_db(self):
        if self._db is None:
            client = self.get_client()
            if client is not None:
                self._db = client[self.config.MONGO_DB]
                # Ensure indexes
                try:
                    conv = self._db[self.config.MONGO_CONVERSATIONS_COLLECTION]
                    conv.create_index("session_id", unique=True)
                    conv.create_index([("user_id", 1), ("updated_at", -1)])
                    prefs = self._db[self.config.MONGO_PREFERENCES_COLLECTION]
                    prefs.create_index("user_id", unique=True)
                except Exception:
                    pass
        return self._db

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None


