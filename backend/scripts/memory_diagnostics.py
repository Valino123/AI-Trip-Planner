#!/usr/bin/env python3
"""
Diagnostic script for memory layers.
Usage:
  # Activate venv first
  # python backend/scripts/memory_diagnostics.py --user u_xxx --session s_xxx
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Optional

# Allow running from repo root or backend/
THIS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from trip_planner.memory import (
    memory_config,
    RedisConnectionManager,
    MongoConnectionManager,
    QdrantConnectionManager,
)


def pretty(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", dest="user_id", required=False, help="user_id (e.g., u_abcdef123456)")
    ap.add_argument("--session", dest="session_id", required=False, help="session_id (e.g., s_abcdef123456)")
    ap.add_argument("--redis-only", action="store_true", help="only check Redis")
    ap.add_argument("--mongo-only", action="store_true", help="only check MongoDB")
    ap.add_argument("--qdrant-only", action="store_true", help="only check Qdrant")
    ap.add_argument("--last", type=int, default=10, help="last N messages from Redis list")
    args = ap.parse_args()

    config = memory_config

    # Redis (Intra-session)
    if not args.mongo_only and not args.qdrant_only:
        print("\n=== Redis (Intra-session) ===")
        try:
            redis = RedisConnectionManager(config).get_client()
            if not redis:
                print("Redis client not available.")
            else:
                if not args.session_id:
                    print("Provide --session to inspect messages, e.g., s_xxx")
                else:
                    key = f"session:{args.session_id}"
                    ln = args.last
                    raw = redis.lrange(key, -ln, -1)
                    print(f"Key: {key} (last {ln})")
                    for i, r in enumerate(raw, 1):
                        try:
                            obj = json.loads(r)
                        except Exception:
                            obj = r
                        print(f"{i:02d}. {obj}")
        except Exception as e:
            print(f"Redis check failed: {e}")

    # MongoDB (Inter-session + Preferences)
    if not args.redis_only and not args.qdrant_only:
        print("\n=== MongoDB (Conversations) ===")
        try:
            db = MongoConnectionManager(config).get_db()
            if not db:
                print("Mongo client not available.")
            else:
                coll = db[config.MONGO_CONVERSATIONS_COLLECTION]
                q = {}
                if args.session_id:
                    q["session_id"] = args.session_id
                elif args.user_id:
                    q["user_id"] = args.user_id
                else:
                    print("Provide --session or --user to filter documents.")
                if q:
                    docs = list(coll.find(q).limit(3))
                    if not docs:
                        print("No conversation docs found.")
                    else:
                        for d in docs:
                            d["_id"] = str(d.get("_id"))
                            pretty(
                                {
                                    "user_id": d.get("user_id"),
                                    "session_id": d.get("session_id"),
                                    "summary": d.get("summary"),
                                    "message_count": (d.get("metadata") or {}).get("message_count"),
                                    "updated_at": d.get("updated_at"),
                                }
                            )
        except Exception as e:
            print(f"Mongo check failed: {e}")

        print("\n=== MongoDB (User Preferences) ===")
        try:
            db = MongoConnectionManager(config).get_db()
            if db and args.user_id:
                prefs = db[config.MONGO_PREFERENCES_COLLECTION].find_one({"user_id": args.user_id})
                if prefs:
                    prefs["_id"] = str(prefs.get("_id"))
                    pretty(prefs)
                else:
                    print("No preferences doc for this user.")
            else:
                print("Provide --user to check preferences.")
        except Exception as e:
            print(f"Mongo prefs check failed: {e}")

    # Qdrant (Vector search)
    if not args.redis_only and not args.mongo_only:
        print("\n=== Qdrant (Vectors) ===")
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            qdr = QdrantConnectionManager(config).get_client()
            if not qdr:
                print("Qdrant client not available.")
            else:
                flt = None
                if args.session_id:
                    flt = Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=args.session_id))])
                elif args.user_id:
                    flt = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=args.user_id))])
                if flt:
                    cnt = qdr.count(collection_name=config.QDRANT_COLLECTION, count_filter=flt, exact=True)
                    print(f"Points matched: {cnt.count}")
                else:
                    print("Provide --session or --user to filter Qdrant points.")
        except Exception as e:
            print(f"Qdrant check failed: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()


