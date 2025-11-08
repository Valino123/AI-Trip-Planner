"""Inter-session memory store using MongoDB + Qdrant + Redis Streams."""
import time
import json
import uuid
from typing import Dict, Any, List, Tuple, Optional

# Qdrant imports (may not be available)
try:
    from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    Filter = None
    FieldCondition = None
    MatchValue = None
    PointStruct = None
    QDRANT_AVAILABLE = False

from ..connections import MongoConnectionManager, QdrantConnectionManager
from ..mem_config import MemoryConfig
from ..models import MemoryItem, MemoryType
from ...llm import init_embedder


class InterSessionMemoryStore:
    """
    MongoDB + Qdrant based inter-session memory store.
    Stores full conversations in MongoDB; embeddings in Qdrant.
    Async embedding via Redis Streams (if enabled), with immediate fallback.
    """

    def __init__(self, mongo_manager: MongoConnectionManager,
                 qdrant_manager: QdrantConnectionManager,
                 config: MemoryConfig):
        self.mongo_manager = mongo_manager
        self.qdrant_manager = qdrant_manager
        self.config = config
        self._embedder = None

    def get_embedder(self):
        """Lazy load embedder."""
        if self._embedder is None:
            self._embedder = init_embedder()
        return self._embedder

    def save_conversation(self, user_id: str, session_id: str,
                          messages: List[Dict[str, Any]]) -> bool:
        """
        Save full conversation to MongoDB (upsert by session_id).
        """
        db = self.mongo_manager.get_db()
        if not db:
            if self.config.VERBOSE:
                print(f"[InterSession] MongoDB not available, skipping save")
            return False

        try:
            # Create summary for the conversation
            summary = self._create_summary(messages)

            conv = {
                "user_id": user_id,
                "session_id": session_id,
                "messages": messages,
                "summary": summary,
                "metadata": {"message_count": len(messages)},
                "updated_at": time.time(),
                "created_at": time.time(),
            }

            conversations = db[self.config.MONGO_CONVERSATIONS_COLLECTION]
            # Upsert by session_id
            conversations.update_one(
                {"session_id": session_id},
                {"$set": conv, "$setOnInsert": {"created_at": time.time()}},
                upsert=True,
            )

            if self.config.VERBOSE:
                print(f"[InterSession] ✓ Saved conversation (MongoDB): user={user_id}, session={session_id}, msgs={len(messages)}")
            return True

        except Exception as e:
            if self.config.VERBOSE:
                print(f"[InterSession] Save failed: {e}")
            return False

    def _create_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create a text summary from messages."""
        parts = []
        for msg in messages[:10]:  # Limit to first 10 messages
            msg_type = msg.get("type", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                # Truncate long messages
                content_preview = content[:150] if len(content) > 150 else content
                parts.append(f"[{msg_type}] {content_preview}")

        summary = " | ".join(parts)
        return summary[:800]  # Limit total summary length

    def queue_embedding_job(self, user_id: str, session_id: str, content: str) -> bool:
        """
        Queue embedding job to Redis Streams.
        Falls back to immediate embedding if async is disabled or Redis unavailable.
        """
        # If async embedding is disabled, do it immediately
        if not self.config.ENABLE_ASYNC_EMBEDDING:
            return self._embed_and_store_immediately(user_id, session_id, content)

        # Try Redis Streams for async processing
        redis_client = None
        try:
            # Prefer a Redis manager attached on the mongo_manager for convenience if present
            redis_client = getattr(self.mongo_manager, 'redis_manager', None)
            if redis_client is not None:
                redis_client = redis_client.get_client()
        except Exception:
            redis_client = None
        if not redis_client:
            # Fallback: try to get from qdrant manager's config
            try:
                from ..connections import RedisConnectionManager
                _redis_manager = RedisConnectionManager(self.config)
                redis_client = _redis_manager.get_client()
            except Exception:
                redis_client = None

        if not redis_client:
            # Redis not available, do immediate embedding
            if self.config.VERBOSE:
                print("[InterSession] Redis not available, doing immediate embedding")
            return self._embed_and_store_immediately(user_id, session_id, content)

        try:
            # Add job to Redis Stream
            job_data = {
                "user_id": user_id,
                "session_id": session_id,
                "content": content,
                "created_at": time.time(),
                "status": "pending"
            }

            stream_key = self.config.EMBEDDING_QUEUE if hasattr(self.config, 'EMBEDDING_QUEUE') else "embedding_queue"
            redis_client.xadd(stream_key, job_data)

            if self.config.VERBOSE:
                print(f"[InterSession] ✓ Queued embedding job: user={user_id}, session={session_id}")
            return True

        except Exception as e:
            if self.config.VERBOSE:
                print(f"[InterSession] Failed to queue, doing immediate embedding: {e}")
            return self._embed_and_store_immediately(user_id, session_id, content)

    def _embed_and_store_immediately(self, user_id: str, session_id: str, content: str) -> bool:
        """
        Fallback: Create embedding immediately and store to Qdrant.
        Used when async processing is unavailable.
        """
        if not QDRANT_AVAILABLE:
            if self.config.VERBOSE:
                print("[InterSession] Qdrant not available, skipping embedding")
            return False

        qdrant = self.qdrant_manager.get_client()
        if not qdrant:
            return False

        try:
            # Create embedding
            embedder = self.get_embedder()
            vector = embedder.embed_query(content)

            # Store in Qdrant
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "content": content[:500],  # Store preview
                    "created_at": time.time()
                }
            )

            qdrant.upsert(
                collection_name=self.config.QDRANT_COLLECTION,
                points=[point]
            )

            if self.config.VERBOSE:
                print(f"[InterSession] ✓ Embedded and stored immediately: user={user_id}, session={session_id}")
            return True

        except Exception as e:
            if self.config.VERBOSE:
                print(f"[InterSession] Immediate embedding failed: {e}")
            return False

    def retrieve_similar(self, user_id: str, query: str,
                         k: int = 4, min_similarity: float = 0.55,
                         verbose: bool = False) -> List[Tuple[MemoryItem, float]]:
        """
        Retrieve similar conversations using Qdrant + MongoDB.
        """
        qdrant = self.qdrant_manager.get_client()
        if not qdrant:
            return []

        if not QDRANT_AVAILABLE:
            if verbose or self.config.VERBOSE:
                print("[InterSession] Qdrant client not available")
            return []

        try:
            # 1. Embed query
            embedder = self.get_embedder()
            query_vector = embedder.embed_query(query)

            # 2. Search Qdrant
            search_results = qdrant.search(
                collection_name=self.config.QDRANT_COLLECTION,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=k * 2,  # Get more candidates
                score_threshold=min_similarity
            )

            # 3. Fetch full content from MongoDB
            db = self.mongo_manager.get_db()
            results = []
            for hit in search_results[:k]:
                payload = getattr(hit, 'payload', {}) or {}
                session_id = payload.get("session_id")
                content_preview = payload.get("content", "")
                full_content = content_preview
                created_at = payload.get("created_at", time.time())

                if db and session_id:
                    try:
                        doc = db[self.config.MONGO_CONVERSATIONS_COLLECTION].find_one(
                            {"session_id": session_id}, {"summary": 1, "messages": 1, "updated_at": 1}
                        )
                        if doc:
                            full_content = doc.get("summary") or content_preview
                            created_at = doc.get("updated_at", created_at)
                    except Exception:
                        pass
                memory_item = MemoryItem(
                    id=str(hit.id),
                    user_id=user_id,
                    session_id=session_id,
                    memory_type=MemoryType.INTER_SESSION,
                    content=full_content,
                    created_at=created_at,
                    metadata=payload
                )
                results.append((memory_item, hit.score))

            if verbose and results:
                print(f"\n[InterSession] Retrieved {len(results)} similar memories")
                for i, (item, score) in enumerate(results, 1):
                    preview = item.content[:80].replace("\n", " ")
                    print(f"[InterSession]  {i}. score={score:.3f} | {preview}...")

            return results
        except Exception as e:
            if verbose or self.config.VERBOSE:
                print(f"[InterSession] Retrieve failed: {e}")
            return []


