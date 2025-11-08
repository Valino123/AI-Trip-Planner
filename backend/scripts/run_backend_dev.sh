#!/usr/bin/env bash
set -euo pipefail

# cd to backend root if executed from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

# Load env if present
if [[ -f ".env.memory.dev" ]]; then
  set -a
  source .env.memory.dev
  set +a
elif [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

echo "[memory-dev] Using:"
echo "  REDIS_HOST=${REDIS_HOST:-unset}  REDIS_PORT=${REDIS_PORT:-unset}"
echo "  MONGO_URI=${MONGO_URI:-unset}"
echo "  QDRANT_URL=${QDRANT_URL:-unset}"
echo "  ENABLE_ASYNC_EMBEDDING=${ENABLE_ASYNC_EMBEDDING:-unset}"

python dev_server.py


