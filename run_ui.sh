#!/bin/bash
# Starts the SCRIBE web UI (backend API + frontend, one Flask process)
# and opens it in your browser. Ctrl+C to stop.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT="${SCRIBE_PORT:-8765}"

source venv/bin/activate

# Open the browser once the server is actually listening, in the background.
( for _ in $(seq 1 30); do
    curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 && open "http://127.0.0.1:${PORT}" && break
    sleep 1
  done ) &

python3 -m src.cli serve --port "$PORT"
