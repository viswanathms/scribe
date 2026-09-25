"""Crawl-then-review orchestration."""
from __future__ import annotations

import datetime as dt
import logging

from . import config, crawler, db

log = logging.getLogger("scribe")


def crawl_day(date: str, category: str = config.ARXIV_CATEGORY) -> int:
    """Crawl one day, upsert into the DB. Returns count of papers seen that day."""
    papers = crawler.fetch_day(date, category=category)
    with db.get_conn() as conn:
        for p in papers:
            db.upsert_paper(conn, p.as_dict())
    log.info("crawl_day %s: %d papers", date, len(papers))
    return len(papers)


def crawl_range(start_date: dt.date, end_date: dt.date, category: str = config.ARXIV_CATEGORY) -> int:
    """Crawl every day in [start_date, end_date] inclusive. One request-burst per day,
    naturally paced by the crawler's own crawl-delay enforcement."""
    total = 0
    day = start_date
    while day <= end_date:
        total += crawl_day(day.isoformat(), category=category)
        day += dt.timedelta(days=1)
    return total


def review_pending(limit: int = config.REVIEW_BATCH_SIZE) -> int:
    from .reviewer import ClaudeReviewer  # deferred: avoid requiring an API key just to crawl

    reviewer = ClaudeReviewer()
    with db.get_conn() as conn:
        pending = db.get_unreviewed(conn, limit=limit)

    reviewed = 0
    for paper in pending:
        try:
            result = reviewer.review(paper)
        except Exception:
            log.exception("review failed for %s", paper["arxiv_id"])
            continue
        with db.get_conn() as conn:
            db.save_review(
                conn,
                arxiv_id=paper["arxiv_id"],
                score=result["importance_score"],
                reasoning=result["reasoning"],
                growth_impact=result["growth_impact"],
                tags_json=result["tags_json"],
                model=reviewer.model,
            )
        reviewed += 1
    log.info("review_pending: %d/%d papers reviewed", reviewed, len(pending))
    return reviewed


def run_daily_job(target_date: str | None = None, category: str = config.ARXIV_CATEGORY) -> dict:
    """The job the scheduler calls once a day: crawl one day + review everything pending."""
    if target_date is None:
        target_date = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    seen = crawl_day(target_date, category=category)
    reviewed = 0
    while True:
        n = review_pending()
        reviewed += n
        if n == 0:
            break
    return {"date": target_date, "crawled": seen, "reviewed": reviewed}
