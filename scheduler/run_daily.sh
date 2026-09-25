#!/bin/bash
# Runs the daily crawl+review job. Invoked by launchd (see com.scribe.daily.plist)
# or can be run by hand / from cron.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

source venv/bin/activate
python -m src.cli daily >> logs/daily.log 2>&1
