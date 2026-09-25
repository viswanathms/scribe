import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- arXiv crawl settings ---
ARXIV_CATEGORY = os.environ.get("ARXIV_CATEGORY", "cs.AI")
ARXIV_BASE_URL = "https://arxiv.org"
# arxiv.org/robots.txt: User-agent: * -> Allow: /catchup, /abs, /pdf, /list ; Crawl-delay: 15
CRAWL_DELAY_SECONDS = float(os.environ.get("CRAWL_DELAY_SECONDS", "15"))
USER_AGENT = os.environ.get(
    "SCRIBE_USER_AGENT",
    "scribe/0.1 (personal research tool; contact: sathananthviswanath@gmail.com)",
)
REQUEST_TIMEOUT_SECONDS = 30

# --- storage ---
DB_PATH = os.environ.get("SCRIBE_DB", str(BASE_DIR / "data" / "scribe.db"))

# --- Claude review settings ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
REVIEW_BATCH_SIZE = int(os.environ.get("REVIEW_BATCH_SIZE", "20"))

# --- web UI ---
WEB_HOST = os.environ.get("SCRIBE_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("SCRIBE_PORT", "8765"))
