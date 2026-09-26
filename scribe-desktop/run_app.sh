#!/bin/bash
# Launches SCRIBE as a native desktop window (pywebview), the same way the
# packaged .app will. Ctrl+C to stop.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

source venv/bin/activate
python main.py
