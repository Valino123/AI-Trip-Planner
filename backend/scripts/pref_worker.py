#!/usr/bin/env python3
"""
Preference extraction worker.
- Consumes jobs from Redis Streams (preference_queue)
- Loads conversation from MongoDB
- Extracts preferences via regex heuristics and optional LLM
- Upserts preferences into MongoDB and invalidates Redis cache
"""
import argparse
import json
import re
import sys
import time
from typing import Dict, Any, List, Optional

from trip_planner.memory.mem_config import memory_config
from trip_planner.memory.connections import RedisConnectionManager, MongoConnectionManager
from trip_planner.memory.stores.preferences import UserPreferenceStore

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except Exception:
    LLM_AVAILABLE = False


STREAM_KEY = memory_config.PREF_QUEUE
GROUP = "pref_extractors"


def ensure_consumer_group(r):
    try:
        r.xgroup_create(name=STREAM_KEY, groupname=GROUP, id="0-0", mkstream=True)
    except Exception:
        # Group may already exist
        pass


def extract_prefs_regex(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Very simple heuristics to extract preferences."""
    text = "\n".join(m.get("content", "") for m in messages if isinstance(m.get("content", ""), str))[:5000]
    prefs: Dict[str, Any] = {}

    # Budget: e.g., budget $1500, under 1000, around 2k
    m = re.search(r"\b(budget|under|around)\s*\$?\s*([0-9]{2,6})\b", text, flags=re.I)
    if m:
        try:
            prefs["budget"] = int(m.group(2))
        except Exception:
            pass

    # Departure city
    m = re.search(r"\bfrom\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b", text)
    if m:
        prefs["departure_city"] = m.group(1)

    # Likes/Dislikes keywords
    likes = []
    if re.search(r"\b(beach|island|coast)\b", text, flags=re.I):
        likes.append("beach")
    if re.search(r"\b(mountain|hiking|trail)\b", text, flags=re.I):
        likes.append("mountain")
    if re.search(r"\b(museum|art|history)\b", text, flags=re.I):
        likes.append("culture")
    if likes:
        prefs["likes"] = sorted(set(likes))

    if re.search(r"\b(crowd|crowded|busy areas)\b", text, flags=re.I):
        prefs["avoid_crowds"] = True

    return prefs


def extract_prefs_llm(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optional LLM-based extraction with a simple schema."""
    if not (LLM_AVAILABLE and memory_config.ENABLE_PREF_LLM_EXTRACTION):
        return {}
    try:
        llm = ChatOpenAI(
            model=getattr(memory_config, "QWEN_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=getattr(memory_config, "DASHSCOPE_API_KEY", None),
            base_url=getattr(memory_config, "BASE_URL", None),
        )
        convo = "\n".join(f"- {m.get('type','msg')}: {m.get('content','')}" for m in messages)[:8000]
        prompt = (
            "Extract stable user travel preferences from this conversation.\n"
            "Return STRICT JSON with keys among: budget (int), departure_city (str), likes (list[str]), avoid_crowds (bool).\n"
            "If unknown, omit the key. Conversation:\n"
            f"{convo}\n"
            "JSON only:"
        )
        result = llm.invoke(prompt)
        text = getattr(result, "content", "") or str(result)
        # try parse json
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(text[start:end+1])
            if isinstance(data, dict):
                return data
    except Exception as e:
        if memory_config.VERBOSE:
            print(f"[PrefWorker] LLM extraction failed: {e}")
    return {}


def merge_preferences(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(old or {})
    for k, v in (new or {}).items():
        merged[k] = v
    return merged


def process_job(pref_store: UserPreferenceStore, mongo: MongoConnectionManager, job: Dict[str, Any]) -> bool:
    user_id = job.get("user_id")
    session_id = job.get("session_id")
    if not user_id or not session_id:
        return True  # ack bad job
    db = mongo.get_db()
    if not db:
        return False
    try:
        doc = db[memory_config.MONGO_CONVERSATIONS_COLLECTION].find_one({"session_id": session_id})
        if not doc:
            return True
        messages = doc.get("messages", [])

        prefs_regex = extract_prefs_regex(messages)
        prefs_llm = extract_prefs_llm(messages)
        extracted = merge_preferences(prefs_regex, prefs_llm)
        if not extracted:
            return True

        current = pref_store.get_preferences(user_id) or {}
        version = current.get("_version")
        new_prefs = dict(current)
        new_prefs.pop("_version", None)
        new_prefs = merge_preferences(new_prefs, extracted)
        ok = pref_store.set_preferences(user_id, new_prefs, expected_version=version)
        if memory_config.VERBOSE:
            print(f"[PrefWorker] Updated prefs for user={user_id}: {extracted} | ok={ok}")
        return True
    except Exception as e:
        if memory_config.VERBOSE:
            print(f"[PrefWorker] Job failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default=GROUP)
    parser.add_argument("--consumer", default=f"c-{int(time.time())}")
    parser.add_argument("--poll-ms", type=int, default=2000)
    args = parser.parse_args()

    redis_mgr = RedisConnectionManager(memory_config)
    mongo_mgr = MongoConnectionManager(memory_config)
    pref_store = UserPreferenceStore(mongo_mgr, redis_mgr, memory_config)
    r = redis_mgr.get_client()
    if not r:
        print("[PrefWorker] Redis not available")
        sys.exit(1)

    ensure_consumer_group(r)

    while True:
        try:
            # First, claim pending
            resp = r.xreadgroup(groupname=args.group, consumername=args.consumer, streams={STREAM_KEY: ">"}, count=10, block=args.poll_ms)
            if not resp:
                continue
            for stream, messages in resp:
                for msg_id, fields in messages:
                    job = {k.decode() if isinstance(k, (bytes, bytearray)) else k:
                           v.decode() if isinstance(v, (bytes, bytearray)) else v for k, v in fields.items()}
                    ok = process_job(pref_store, mongo_mgr, job)
                    if ok:
                        try:
                            r.xack(STREAM_KEY, args.group, msg_id)
                        except Exception:
                            pass
        except KeyboardInterrupt:
            break
        except Exception as e:
            if memory_config.VERBOSE:
                print(f"[PrefWorker] Loop error: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    main()


