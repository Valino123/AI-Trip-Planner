#!/usr/bin/env python3
"""
Redis Streams → Embedding → Qdrant worker.

Consumes jobs from a Redis Stream (default: 'embedding_queue'), creates embeddings,
and upserts into Qdrant with user_id/session_id filtering payloads.

Usage (WSL/Linux):
  source backend/.venv/bin/activate
  python backend/scripts/embedding_worker.py --group embedder --consumer worker-1

Notes:
  - Uses backend/.env automatically (see backend/config.py for load order).
  - If ENABLE_ASYNC_EMBEDDING=false, your application may embed synchronously instead.
"""
from __future__ import annotations
import argparse
import os
import sys
import time
import uuid
from typing import Dict, Any, Optional, List

# Ensure backend on path
THIS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from trip_planner.memory import memory_config
from trip_planner.memory import RedisConnectionManager, QdrantConnectionManager
from trip_planner.llm import init_embedder


def ensure_group(redis, stream_key: str, group: str):
    try:
        # mkstream=True ensures stream is created if absent
        redis.xgroup_create(name=stream_key, groupname=group, id="0", mkstream=True)
        print(f"[worker] Created group '{group}' on stream '{stream_key}'")
    except Exception as e:
        # Already exists or other non-fatal
        if "BUSYGROUP" in str(e):
            pass
        else:
            print(f"[worker] xgroup_create warning: {e}")


def process_job(embedder, qdrant, collection: str, job: Dict[str, Any]) -> bool:
    user_id = job.get("user_id")
    session_id = job.get("session_id")
    content = job.get("content", "")
    created_at = float(job.get("created_at", time.time()))
    if not content:
        return True  # nothing to do, ack
    try:
        vector = embedder.embed_query(content)
        from qdrant_client.models import PointStruct
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "user_id": user_id,
                "session_id": session_id,
                "content": content[:500],
                "created_at": created_at,
                "source": "embedding_worker",
            },
        )
        qdrant.upsert(collection_name=collection, points=[point])
        return True
    except Exception as e:
        print(f"[worker] Upsert failed: {e}")
        return False


def run_worker(group: str, consumer: str, block_ms: int = 5000, batch: int = 10):
    cfg = memory_config
    stream_key = getattr(cfg, "EMBEDDING_QUEUE", "embedding_queue")

    # Connections
    redis = RedisConnectionManager(cfg).get_client()
    if not redis:
        print("[worker] Redis not available.")
        return 1
    qdrant = QdrantConnectionManager(cfg).get_client()
    if not qdrant:
        print("[worker] Qdrant not available.")
        return 1
    print(f"[worker] Connected. Stream='{stream_key}', group='{group}', consumer='{consumer}'")

    # Embedder
    embedder = init_embedder()
    ensure_group(redis, stream_key, group)

    while True:
        try:
            entries = redis.xreadgroup(group, consumer, streams={stream_key: ">"}, count=batch, block=block_ms)
            if not entries:
                continue
            for stream, messages in entries:
                for msg_id, fields in messages:
                    # fields is dict of {b'key': b'value'} with decode_responses=True it may be str
                    ok = process_job(embedder, qdrant, cfg.QDRANT_COLLECTION, fields)
                    if ok:
                        try:
                            redis.xack(stream_key, group, msg_id)
                        except Exception as e:
                            print(f"[worker] XACK failed for {msg_id}: {e}")
                    else:
                        # leave unacked; consider DLQ in future
                        print(f"[worker] Processing failed for {msg_id}, left unacked")
        except KeyboardInterrupt:
            print("\n[worker] Stopped by user.")
            break
        except Exception as e:
            print(f"[worker] Loop error: {e}")
            time.sleep(1.0)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="embedder", help="Redis stream consumer group")
    ap.add_argument("--consumer", default=f"worker-{os.getpid()}", help="Consumer name")
    ap.add_argument("--block", type=int, default=5000, help="xreadgroup BLOCK ms")
    ap.add_argument("--batch", type=int, default=10, help="max messages per fetch")
    args = ap.parse_args()
    code = run_worker(args.group, args.consumer, args.block, args.batch)
    raise SystemExit(code)


if __name__ == "__main__":
    main()


