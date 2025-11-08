"""Redis connection manager for intra-session memory and streams."""
from ..mem_config import MemoryConfig


class RedisConnectionManager:
    """Manages Redis connection pool for intra-session memory."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._client = None

    def get_client(self):
        """Get or create Redis client (lazy initialization)."""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(
                    host=self.config.REDIS_HOST,
                    port=self.config.REDIS_PORT,
                    db=self.config.REDIS_DB,
                    password=self.config.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                # Test connection
                self._client.ping()
                if self.config.VERBOSE:
                    print(f"[Redis] Connected to {self.config.REDIS_HOST}:{self.config.REDIS_PORT}")
            except ImportError:
                if self.config.VERBOSE:
                    print("[Redis] WARNING: redis-py not installed. Install: pip install redis")
                self._client = None
            except Exception as e:
                if self.config.VERBOSE:
                    print(f"[Redis] WARNING: Connection failed: {e}")
                self._client = None
        return self._client

    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None


