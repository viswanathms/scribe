"""SQLite storage for crawled arXiv papers and their Claude review scores."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id        TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    authors         TEXT NOT NULL,
    abstract        TEXT NOT NULL,
    comments        TEXT,
    subjects        TEXT,
    primary_subject TEXT,
    category        TEXT NOT NULL,
    published_date  TEXT NOT NULL,   -- arXiv announcement date, YYYY-MM-DD
    abs_url         TEXT NOT NULL,
    pdf_url         TEXT NOT NULL,
    crawled_at      TEXT NOT NULL DEFAULT (datetime('now')),
    importance_score    INTEGER,     -- 1-10, NULL until reviewed
    importance_reasoning TEXT,
    growth_impact       TEXT,
    review_tags          TEXT,       -- JSON list of short tags
    reviewed_at          TEXT,
    review_model          TEXT
);
CREATE INDEX IF NOT EXISTS idx_papers_published_date ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_papers_importance ON papers(importance_score);
"""


def _connect():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_paper(conn, paper: dict):
    """Insert a freshly-crawled paper; ignore if already present (never clobber a review)."""
    conn.execute(
        """
        INSERT INTO papers (
            arxiv_id, title, authors, abstract, comments, subjects,
            primary_subject, category, published_date, abs_url, pdf_url
        ) VALUES (:arxiv_id, :title, :authors, :abstract, :comments, :subjects,
                   :primary_subject, :category, :published_date, :abs_url, :pdf_url)
        ON CONFLICT(arxiv_id) DO NOTHING
        """,
        paper,
    )


def get_unreviewed(conn, limit: int = 100):
    rows = conn.execute(
        "SELECT * FROM papers WHERE importance_score IS NULL ORDER BY published_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_review(conn, arxiv_id: str, score: int, reasoning: str, growth_impact: str, tags_json: str, model: str):
    conn.execute(
        """
        UPDATE papers
        SET importance_score = ?, importance_reasoning = ?, growth_impact = ?,
            review_tags = ?, reviewed_at = datetime('now'), review_model = ?
        WHERE arxiv_id = ?
        """,
        (score, reasoning, growth_impact, tags_json, model, arxiv_id),
    )


def list_papers(sort_by: str = "published_date", order: str = "desc", date: str | None = None,
                 min_score: int | None = None, limit: int = 500):
    sort_by = sort_by if sort_by in ("published_date", "importance_score", "crawled_at", "title") else "published_date"
    order = "ASC" if order.lower() == "asc" else "DESC"
    query = f"SELECT * FROM papers WHERE 1=1"
    params: list = []
    if date:
        query += " AND published_date = ?"
        params.append(date)
    if min_score is not None:
        query += " AND importance_score >= ?"
        params.append(min_score)
    query += f" ORDER BY {sort_by} {order} NULLS LAST, published_date DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM papers").fetchone()["c"]
        reviewed = conn.execute("SELECT COUNT(*) AS c FROM papers WHERE importance_score IS NOT NULL").fetchone()["c"]
        days = conn.execute("SELECT COUNT(DISTINCT published_date) AS c FROM papers").fetchone()["c"]
        return {"total_papers": total, "reviewed": reviewed, "days_covered": days}
