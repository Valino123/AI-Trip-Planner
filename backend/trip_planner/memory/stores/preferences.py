"""User preferences store using MongoDB (primary) + Redis cache."""
import json
from typing import Dict, Any, Optional
from ..connections import MongoConnectionManager, RedisConnectionManager
from ..mem_config import MemoryConfig


class UserPreferenceStore:
    """
    MongoDB + Redis cache for user preferences.
    Supports versioning and optimistic locking (version field in document).
    """

    def __init__(self, mongo_manager: MongoConnectionManager,
                 redis_manager: RedisConnectionManager,
                 config: MemoryConfig):
        self.mongo_manager = mongo_manager
        self.redis_manager = redis_manager
        self.config = config

    def _get_cache_key(self, user_id: str) -> str:
        """Generate cache key."""
        return f"pref:{user_id}"

    def get_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences (Redis cache -> MongoDB).
        """
        # Try cache first
        if self.config.ENABLE_REDIS_CACHE:
            client = self.redis_manager.get_client()
            if client:
                try:
                    cached = client.get(self._get_cache_key(user_id))
                    if cached:
                        if self.config.VERBOSE:
                            print(f"[Preferences] Cache hit for user={user_id}")
                        return json.loads(cached)
                except Exception as e:
                    if self.config.VERBOSE:
                        print(f"[Preferences] Cache read failed: {e}")

        # Fallback to MongoDB
        db = self.mongo_manager.get_db()
        if not db:
            return None
        try:
            doc = db[self.config.MONGO_PREFERENCES_COLLECTION].find_one({"user_id": user_id})
            if not doc:
                return None
            prefs = doc.get("preferences", {})
            version = doc.get("version", 1)
            out = {**prefs, "_version": version}
            # warm cache
            if self.config.ENABLE_REDIS_CACHE:
                client = self.redis_manager.get_client()
                if client:
                    client.set(self._get_cache_key(user_id), json.dumps(out, ensure_ascii=False), ex=3600)
            return out
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[Preferences] MongoDB read failed: {e}")
            return None

    def set_preferences(self, user_id: str, preferences: Dict[str, Any],
                        expected_version: Optional[int] = None) -> bool:
        """
        Set user preferences with optimistic locking.
        """
        db = self.mongo_manager.get_db()
        if not db:
            return False
        try:
            coll = db[self.config.MONGO_PREFERENCES_COLLECTION]
            if expected_version is None:
                # Upsert without version check, bump version
                coll.update_one(
                    {"user_id": user_id},
                    {"$set": {"preferences": preferences}, "$inc": {"version": 1}, "$setOnInsert": {"version": 1}},
                    upsert=True,
                )
            else:
                res = coll.update_one(
                    {"user_id": user_id, "version": expected_version},
                    {"$set": {"preferences": preferences}, "$inc": {"version": 1}},
                    upsert=False,
                )
                if res.matched_count == 0:
                    if self.config.VERBOSE:
                        print(f"[Preferences] Version conflict for user={user_id}")
                    return False
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[Preferences] MongoDB write failed: {e}")
            return False

        # Invalidate cache
        if self.config.ENABLE_REDIS_CACHE:
            client = self.redis_manager.get_client()
            if client:
                try:
                    client.delete(self._get_cache_key(user_id))
                except Exception:
                    pass

        return True

    def update_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Update single preference key."""
        prefs = self.get_preferences(user_id) or {}
        prefs[key] = value
        return self.set_preferences(user_id, prefs)

    # ---------------------- Async Extraction Queue ----------------------

    def queue_extraction_job(self, user_id: str, session_id: str) -> bool:
        """
        Queue a preference extraction job to Redis Streams.
        The worker will fetch conversation from MongoDB and extract preferences.
        """
        if not self.config.ENABLE_PREF_EXTRACTION:
            return False

        client = self.redis_manager.get_client()
        if not client:
            return False

        try:
            job = {
                "user_id": user_id,
                "session_id": session_id,
            }
            client.xadd(self.config.PREF_QUEUE, job)
            if self.config.VERBOSE:
                print(f"[Preferences] ✓ Queued extraction job: user={user_id}, session={session_id}")
            return True
        except Exception as e:
            if self.config.VERBOSE:
                print(f"[Preferences] Queue extraction failed: {e}")
            return False


