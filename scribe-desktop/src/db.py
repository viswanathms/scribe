"""SQLite storage for crawled arXiv papers and their review scores."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

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
    reviewed_at           TEXT,
    review_model           TEXT,
    review_provider          TEXT,   -- anthropic | openai | ollama
    criteria_snapshot         TEXT,  -- JSON: the Type/Function/Area/Other active at review time
    summary                   TEXT,  -- one-line plain-English "what this paper does"
    interest_marked_at         TEXT, -- non-NULL = user bookmarked this as "read later"
    interest_read_at            TEXT -- non-NULL = user has since marked it read
);
CREATE INDEX IF NOT EXISTS idx_papers_published_date ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_papers_importance ON papers(importance_score);
"""

# Columns added after the original release. init_db() adds any that are
# missing from an existing DB file -- CREATE TABLE IF NOT EXISTS above only
# covers a brand-new DB.
MIGRATIONS = [
    ("summary", "TEXT"),
    ("interest_marked_at", "TEXT"),
    ("interest_read_at", "TEXT"),
]


def _connect():
    config.APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
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
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(papers)")}
        for col_name, col_type in MIGRATIONS:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_type}")


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


def save_review(
    conn,
    arxiv_id: str,
    score: int,
    reasoning: str,
    growth_impact: str,
    tags_json: str,
    model: str,
    provider: str,
    criteria_snapshot_json: str,
    summary: str | None = None,
):
    conn.execute(
        """
        UPDATE papers
        SET importance_score = ?, importance_reasoning = ?, growth_impact = ?,
            review_tags = ?, reviewed_at = datetime('now'), review_model = ?,
            review_provider = ?, criteria_snapshot = ?, summary = ?
        WHERE arxiv_id = ?
        """,
        (score, reasoning, growth_impact, tags_json, model, provider, criteria_snapshot_json, summary, arxiv_id),
    )


def get_missing_summaries(conn, limit: int = 100):
    """Already-reviewed papers that predate the summary field."""
    rows = conn.execute(
        "SELECT * FROM papers WHERE importance_score IS NOT NULL AND summary IS NULL "
        "ORDER BY published_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_summary(conn, arxiv_id: str, summary: str):
    conn.execute("UPDATE papers SET summary = ? WHERE arxiv_id = ?", (summary, arxiv_id))


def get_report(date: str, min_score: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT arxiv_id, title, summary, importance_score, abs_url, pdf_url, published_date, "
            "primary_subject, interest_marked_at, interest_read_at "
            "FROM papers WHERE published_date = ? AND importance_score >= ? "
            "ORDER BY importance_score DESC, title ASC",
            (date, min_score),
        ).fetchall()
        return [dict(r) for r in rows]


def set_interest(conn, arxiv_id: str, marked: bool):
    """Toggling the bookmark on clears any prior read state -- re-marking
    something starts it fresh in the unread list."""
    if marked:
        conn.execute(
            "UPDATE papers SET interest_marked_at = datetime('now'), interest_read_at = NULL WHERE arxiv_id = ?",
            (arxiv_id,),
        )
    else:
        conn.execute(
            "UPDATE papers SET interest_marked_at = NULL, interest_read_at = NULL WHERE arxiv_id = ?",
            (arxiv_id,),
        )


def set_interest_read(conn, arxiv_id: str, read: bool):
    conn.execute(
        "UPDATE papers SET interest_read_at = ? WHERE arxiv_id = ?",
        (dt_now_or_none(read), arxiv_id),
    )


def dt_now_or_none(flag: bool):
    import datetime as _dt

    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if flag else None


def get_interests(unread_only: bool = True, limit: int = 500):
    query = "SELECT * FROM papers WHERE interest_marked_at IS NOT NULL"
    if unread_only:
        query += " AND interest_read_at IS NULL"
    query += " ORDER BY interest_marked_at DESC LIMIT ?"
    with get_conn() as conn:
        rows = conn.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]


def count_by_subject(limit: int = 15):
    """Paper counts grouped by arXiv's own primary_subject, most common first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT primary_subject, COUNT(*) AS c FROM papers "
            "WHERE primary_subject IS NOT NULL AND primary_subject != '' "
            "GROUP BY primary_subject ORDER BY c DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"subject": r["primary_subject"], "count": r["c"]} for r in rows]


def get_calendar_data(year: int, month: int):
    """Per-day paper count + average score for one calendar month (YYYY, MM)."""
    month_prefix = f"{year:04d}-{month:02d}"
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT published_date, COUNT(*) AS total, AVG(importance_score) AS avg_score, "
            "SUM(CASE WHEN importance_score IS NOT NULL THEN 1 ELSE 0 END) AS scored "
            "FROM papers WHERE published_date LIKE ? || '%' "
            "GROUP BY published_date",
            (month_prefix,),
        ).fetchall()
        return [
            {
                "date": r["published_date"],
                "total": r["total"],
                "scored": r["scored"],
                "avg_score": round(r["avg_score"], 2) if r["avg_score"] is not None else None,
            }
            for r in rows
        ]


def _papers_where(date: str | None, min_score: int | None, query_text: str | None):
    clauses = ["1=1"]
    params: list = []
    if date:
        clauses.append("published_date = ?")
        params.append(date)
    if min_score is not None:
        clauses.append("importance_score >= ?")
        params.append(min_score)
    if query_text:
        clauses.append("(title LIKE ? OR abstract LIKE ? OR summary LIKE ? OR authors LIKE ?)")
        like = f"%{query_text}%"
        params.extend([like, like, like, like])
    return " AND ".join(clauses), params


def list_papers(
    sort_by: str = "published_date",
    order: str = "desc",
    date: str | None = None,
    min_score: int | None = None,
    query_text: str | None = None,
    page: int = 1,
    page_size: int = 25,
):
    """Server-side paginated + searchable paper listing. Returns (rows, total_count)."""
    sort_by = sort_by if sort_by in ("published_date", "importance_score", "crawled_at", "title") else "published_date"
    order = "ASC" if order.lower() == "asc" else "DESC"
    where_sql, params = _papers_where(date, min_score, query_text)

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM papers WHERE {where_sql}", params).fetchone()["c"]
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            f"SELECT * FROM papers WHERE {where_sql} "
            f"ORDER BY {sort_by} {order} NULLS LAST, published_date DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [dict(r) for r in rows], total


def get_date_bounds():
    """(earliest, latest) published_date with any data, or (None, None) if empty."""
    with get_conn() as conn:
        row = conn.execute("SELECT MIN(published_date) AS lo, MAX(published_date) AS hi FROM papers").fetchone()
        return row["lo"], row["hi"]


def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM papers").fetchone()["c"]
        reviewed = conn.execute("SELECT COUNT(*) AS c FROM papers WHERE importance_score IS NOT NULL").fetchone()["c"]
        days = conn.execute("SELECT COUNT(DISTINCT published_date) AS c FROM papers").fetchone()["c"]
        return {"total_papers": total, "reviewed": reviewed, "days_covered": days}
