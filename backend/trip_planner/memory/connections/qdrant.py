"""Qdrant connection manager for vector search."""
from ..mem_config import MemoryConfig


class QdrantConnectionManager:
    """Manages Qdrant vector database connection."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._client = None

    def get_client(self):
        """Get or create Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams

                # Build connection preference:
                # - If QDRANT_URL is provided, use it directly
                # - Else if API key or explicit HTTPS requested, use https://
                # - Else default to http:// (local dev)
                url = None
                if getattr(self.config, "QDRANT_URL", None):
                    url = self.config.QDRANT_URL
                else:
                    use_https = bool(getattr(self.config, "QDRANT_HTTPS", False)) or bool(self.config.QDRANT_API_KEY)
                    scheme = "https" if use_https else "http"
                    url = f"{scheme}://{self.config.QDRANT_HOST}:{self.config.QDRANT_PORT}"

                self._client = QdrantClient(
                    url=url,
                    api_key=self.config.QDRANT_API_KEY,
                    timeout=10,
                )

                # Ensure collection exists (create only if 404 Not Found)
                try:
                    self._client.get_collection(self.config.QDRANT_COLLECTION)
                except Exception as e:
                    status = getattr(e, "status_code", None)
                    message = str(getattr(e, "content", "")) or str(e)
                    if status == 404 or "does not exist" in message.lower():
                        self._client.create_collection(
                            collection_name=self.config.QDRANT_COLLECTION,
                            vectors_config=VectorParams(
                                size=self.config.VECTOR_DIM,
                                distance=Distance.COSINE,
                            ),
                        )
                        if self.config.VERBOSE:
                            print(f"[Qdrant] Created collection: {self.config.QDRANT_COLLECTION}")
                    else:
                        # Any other error means server responded but not with Not Found, avoid creating to prevent 409
                        if self.config.VERBOSE:
                            print(f"[Qdrant] Skipping create; get_collection error: {e}")

                if self.config.VERBOSE:
                    print(f"[Qdrant] Connected to {url}")
            except ImportError:
                if self.config.VERBOSE:
                    print("[Qdrant] WARNING: qdrant-client not installed. Install: pip install qdrant-client")
                self._client = None
            except Exception as e:
                if self.config.VERBOSE:
                    print(f"[Qdrant] WARNING: Connection failed: {e}")
                self._client = None
        return self._client

    def close(self):
        """Close Qdrant connection."""
        if self._client:
            self._client.close()
            self._client = None


