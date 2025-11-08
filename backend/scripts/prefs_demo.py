#!/usr/bin/env python3
"""
Set and read user preferences via Mongo-backed store.
Usage:
  python backend/scripts/prefs_demo.py --user u_xxx --key travel_style --value luxury
  python backend/scripts/prefs_demo.py --user u_xxx --show
"""
from __future__ import annotations
import argparse
import json
import os
import sys

THIS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from trip_planner.memory import memory_config, RedisConnectionManager, MongoConnectionManager
from trip_planner.memory import UserPreferenceStore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="user_id")
    ap.add_argument("--key", help="preference key")
    ap.add_argument("--value", help="preference value")
    ap.add_argument("--show", action="store_true", help="only show preferences")
    args = ap.parse_args()

    cfg = memory_config
    prefs = UserPreferenceStore(MongoConnectionManager(cfg), RedisConnectionManager(cfg), cfg)

    if args.show or not args.key:
        current = prefs.get_preferences(args.user) or {}
        print(json.dumps(current, ensure_ascii=False, indent=2))
        return

    ok = prefs.update_preference(args.user, args.key, args.value)
    print("updated" if ok else "failed")
    current = prefs.get_preferences(args.user) or {}
    print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


