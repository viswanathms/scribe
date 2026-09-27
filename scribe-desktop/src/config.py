"""App-wide settings, split into two kinds:
- Fixed constants (crawl behavior) that live in code.
- User-editable settings (provider/auth/category/criteria) that live in a JSON
  file under ~/Library/Application Support/SCRIBE, so they survive app
  reinstalls and are shared between the GUI and the background launchd job.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "SCRIBE"
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
SETTINGS_PATH = APP_SUPPORT_DIR / "config.json"
DB_PATH = APP_SUPPORT_DIR / "scribe.db"
LOG_DIR = APP_SUPPORT_DIR / "logs"

# --- arXiv crawl settings (fixed; robots.txt-driven, see crawler.py) ---
ARXIV_BASE_URL = "https://arxiv.org"
CRAWL_DELAY_SECONDS = float(os.environ.get("CRAWL_DELAY_SECONDS", "15"))
USER_AGENT = "scribe-desktop/0.1 (personal research tool; contact: sathananthviswanath@gmail.com)"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_CATEGORY = "cs.AI"

# --- user-editable settings ---
DEFAULT_SETTINGS = {
    "onboarded": False,
    "provider": None,  # "anthropic" | "openai" | "ollama"
    "base_url": None,  # required for ollama; optional override for anthropic/openai
    "api_key": None,  # not used for ollama
    "model": None,
    "categories": [DEFAULT_CATEGORY],  # arXiv categories/fields to track, e.g. ["cs.AI", "cs.LG"]
    "criteria": {
        "type": "",
        "function": "",
        "area": "",
        "other": "",
    },
    "report_threshold": 7,  # default min importance_score for the daily report
}

PROVIDER_DEFAULT_BASE_URL = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434",
}

CRITERIA_TYPE_SUGGESTIONS = [
    "AI Engineering",
    "LLM Implementation Details",
    "Research / Theory",
    "Infrastructure & Scaling",
    "Safety & Alignment",
    "Product & UX",
]
CRITERIA_FUNCTION_SUGGESTIONS = ["Engineering", "Research"]


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
    with open(SETTINGS_PATH) as f:
        data = json.load(f)
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    merged.update(data)
    merged["criteria"] = {**merged_criteria_default(), **(data.get("criteria") or {})}
    # Migrate the old single "category" string (pre-multi-category) into the list.
    if "categories" not in data and data.get("category"):
        merged["categories"] = [data["category"]]
    merged.pop("category", None)
    if not merged.get("categories"):
        merged["categories"] = [DEFAULT_CATEGORY]
    return merged


def merged_criteria_default() -> dict:
    return dict(DEFAULT_SETTINGS["criteria"])


def save_settings(settings: dict) -> None:
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
    # Contains an API key: keep it out of other users' reach on shared machines.
    os.chmod(SETTINGS_PATH, 0o600)


def ensure_dirs() -> None:
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
