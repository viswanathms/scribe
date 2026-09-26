#!/bin/bash
# Runs the daily crawl+review job. Invoked by launchd (see com.scribe.daily.plist)
# or can be run by hand. Reads provider/criteria from
# ~/Library/Application Support/SCRIBE/config.json -- no .env needed.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

LOG_DIR="$HOME/Library/Application Support/SCRIBE/logs"
mkdir -p "$LOG_DIR"

source venv/bin/activate
python -m src.cli daily >> "$LOG_DIR/daily.log" 2>&1
