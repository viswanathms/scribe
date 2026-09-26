#!/bin/bash
# One-time (or re-run anytime) backfill: fills in the one-line `summary` field
# for every already-reviewed paper that predates it. Safe to interrupt and
# re-run -- it only ever picks up papers still missing a summary.
#
# Runs detached (nohup) under `caffeinate -i` so it survives the terminal
# closing and won't stall if the Mac goes to sleep. Progress is real DB
# state, not just log lines -- check it anytime with:
#   venv/bin/python -m src.cli stats
#   sqlite3 ~/Library/Application\ Support/SCRIBE/scribe.db \
#     "SELECT COUNT(*) FROM papers WHERE importance_score IS NOT NULL AND summary IS NULL;"
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d venv ]; then
  echo "No venv found. Run setup first (see README)." >&2
  exit 1
fi

LOG_DIR="$HOME/Library/Application Support/SCRIBE/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backfill_summaries.log"

BATCH_SIZE="${1:-1}"  # 1 = most granular progress; raise it if your provider handles concurrency well

nohup caffeinate -i venv/bin/python -m src.cli backfill-summaries --loop --batch-size "$BATCH_SIZE" \
  >> "$LOG_FILE" 2>&1 &
disown

PID=$!
echo "Started (pid $PID). Logs: $LOG_FILE"
echo "Check progress:"
echo "  cd '$PROJECT_DIR' && venv/bin/python -m src.cli stats"
