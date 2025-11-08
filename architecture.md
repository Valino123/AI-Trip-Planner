{
    "intra_session": {
        "primary": "Redis",
        "config": {
            "TTL": "2 hours",
            "data_structure": "Redis Hashes/JSON"
        }
    },
    
    "inter_session": {
        "conversation_store": "MongoDB",      # Changed from PostgreSQL
        "vector_search": "Qdrant",           # Semantic search
        "message_queue": "Redis Streams",    # For async embedding
        "flow": [
            "Save full conversation to MongoDB",
            "Queue embedding job to Redis Streams",
            "Worker creates embeddings and stores in Qdrant",
            "Retrieval queries both Qdrant and MongoDB"
        ]
    },
    
    "user_preferences": {
        "primary": "MongoDB",  # Same database, different collection
        "cache": "Redis"       # Cache frequently accessed preferences
    }
}

---

Dev memory mode (no Docker)

Prereqs (Linux/WSL):
- Redis server on 127.0.0.1:6379
- MongoDB on 127.0.0.1:27017 (db: trip_planner)
- Qdrant on 127.0.0.1:6333 (HTTP)

Environment (set in backend/.env or export inline):
- USE_LTM=true
- ENABLE_ASYNC_EMBEDDING=false
- REDIS_HOST=127.0.0.1 REDIS_PORT=6379
- MONGO_URI=mongodb://127.0.0.1:27017
- QDRANT_URL=http://127.0.0.1:6333 QDRANT_HTTPS=false

Start backend:
- source backend/.venv/bin/activate
- cd backend && python dev_server.py
  (or: backend/scripts/run_backend_dev.sh which loads .env/.env.memory.dev if present)

Check memory layers:
- python backend/scripts/memory_diagnostics.py --user <uid> --session <sid> --last 10
- python backend/scripts/prefs_demo.py --user <uid> --key travel_style --value budget
