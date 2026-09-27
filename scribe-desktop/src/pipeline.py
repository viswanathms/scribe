"""Crawl-then-review orchestration."""
from __future__ import annotations

import datetime as dt
import json
import logging

from . import config, crawler, db
from .providers import get_provider

log = logging.getLogger("scribe")


def crawl_day(date: str, categories: list[str] | None = None) -> int:
    """Crawl one day across every tracked category. One request-burst per
    category (each already paced by the crawler's own crawl-delay), results
    from all categories land in the same `papers` table -- a paper crawled
    under more than one category's "new submissions" (rare) is just a no-op
    upsert the second time, since arxiv_id is the primary key."""
    categories = categories or config.load_settings()["categories"]
    total = 0
    for category in categories:
        papers = crawler.fetch_day(date, category=category)
        with db.get_conn() as conn:
            for p in papers:
                db.upsert_paper(conn, p.as_dict())
        log.info("crawl_day %s (%s): %d papers", date, category, len(papers))
        total += len(papers)
    return total


def crawl_range(start_date: dt.date, end_date: dt.date, categories: list[str] | None = None) -> int:
    """Crawl every day in [start_date, end_date] inclusive, across every tracked category."""
    total = 0
    day = start_date
    while day <= end_date:
        total += crawl_day(day.isoformat(), categories=categories)
        day += dt.timedelta(days=1)
    return total


def review_pending(limit: int = 20) -> tuple[int, int]:
    """Returns (attempted, succeeded). A paper that errors (e.g. a transient
    provider timeout) is skipped, not removed from the unreviewed pool, so
    the caller's loop can tell "nothing left to review" (attempted == 0)
    apart from "this batch happened to fail" (attempted > 0, succeeded == 0)
    -- conflating the two used to make one flaky call end an entire backfill."""
    settings = config.load_settings()
    provider = get_provider(settings)
    criteria = settings["criteria"]
    criteria_json = json.dumps(criteria)

    with db.get_conn() as conn:
        pending = db.get_unreviewed(conn, limit=limit)

    reviewed = 0
    for paper in pending:
        try:
            result = provider.review(paper, criteria)
        except Exception:
            log.exception("review failed for %s", paper["arxiv_id"])
            continue
        with db.get_conn() as conn:
            db.save_review(
                conn,
                arxiv_id=paper["arxiv_id"],
                score=result.importance_score,
                reasoning=result.reasoning,
                growth_impact=result.growth_impact,
                tags_json=json.dumps(result.tags),
                model=settings["model"],
                provider=settings["provider"],
                criteria_snapshot_json=criteria_json,
                summary=result.summary,
            )
        reviewed += 1
    log.info("review_pending: %d/%d papers reviewed", reviewed, len(pending))
    return len(pending), reviewed


def review_all_pending(batch_size: int = 20, max_consecutive_stalls: int = 20) -> int:
    total = 0
    stalls = 0
    while True:
        attempted, n = review_pending(limit=batch_size)
        if attempted == 0:
            break
        total += n
        if n == 0:
            stalls += 1
            if stalls >= max_consecutive_stalls:
                log.error(
                    "review_all_pending: %d consecutive fully-failed batches, giving up "
                    "(likely a systematically bad paper or a dead provider, not a blip)",
                    stalls,
                )
                break
        else:
            stalls = 0
    return total


def backfill_summaries(limit: int = 20) -> tuple[int, int]:
    """Same (attempted, succeeded) shape as review_pending, for papers that
    already have a score but predate the summary field."""
    settings = config.load_settings()
    provider = get_provider(settings)

    with db.get_conn() as conn:
        pending = db.get_missing_summaries(conn, limit=limit)

    done = 0
    for paper in pending:
        try:
            summary = provider.summarize(paper)
        except Exception:
            log.exception("summarize failed for %s", paper["arxiv_id"])
            continue
        with db.get_conn() as conn:
            db.save_summary(conn, arxiv_id=paper["arxiv_id"], summary=summary)
        done += 1
    log.info("backfill_summaries: %d/%d papers summarized", done, len(pending))
    return len(pending), done


def backfill_all_summaries(batch_size: int = 1, max_consecutive_stalls: int = 20) -> int:
    total = 0
    stalls = 0
    while True:
        attempted, n = backfill_summaries(limit=batch_size)
        if attempted == 0:
            break
        total += n
        if n == 0:
            stalls += 1
            if stalls >= max_consecutive_stalls:
                log.error(
                    "backfill_all_summaries: %d consecutive fully-failed batches, giving up",
                    stalls,
                )
                break
        else:
            stalls = 0
    return total


def generate_report(date: str, min_score: int | None = None) -> list[dict]:
    if min_score is None:
        min_score = config.load_settings()["report_threshold"]
    return db.get_report(date, min_score)


def render_report_markdown(date: str, min_score: int, papers: list[dict]) -> str:
    lines = [f"# SCRIBE daily report -- {date}", "", f"Threshold: importance >= {min_score}", ""]
    if not papers:
        lines.append("No papers scored at or above the threshold today.")
    for p in papers:
        summary = p.get("summary") or "(no summary yet)"
        lines.append(f"- **[{p['importance_score']}] [{p['title']}]({p['abs_url']})** -- {summary}")
    return "\n".join(lines) + "\n"


def save_report_file(date: str, min_score: int | None = None) -> str:
    papers = generate_report(date, min_score)
    if min_score is None:
        min_score = config.load_settings()["report_threshold"]
    reports_dir = config.APP_SUPPORT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{date}.md"
    path.write_text(render_report_markdown(date, min_score, papers))
    return str(path)


def run_daily_job(target_date: str | None = None) -> dict:
    """The job the scheduler calls once a day: crawl one day + review everything pending
    + save that day's report file."""
    if target_date is None:
        target_date = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    seen = crawl_day(target_date)
    reviewed = review_all_pending()
    backfill_all_summaries()
    report_path = save_report_file(target_date)
    return {"date": target_date, "crawled": seen, "reviewed": reviewed, "report": report_path}
