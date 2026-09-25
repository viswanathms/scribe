"""CLI entrypoint: python -m src.cli <command> ..."""
from __future__ import annotations

import argparse
import datetime as dt
import logging

from . import config, db, pipeline


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_backfill(args):
    db.init_db()
    end = dt.date.today() - dt.timedelta(days=1)  # yesterday: last fully-announced day
    start = end - dt.timedelta(days=args.days - 1)
    total = pipeline.crawl_range(start, end, category=args.category)
    print(f"Crawled {start} .. {end}: {total} papers total.")
    if not args.skip_review:
        reviewed = 0
        while True:
            n = pipeline.review_pending(limit=args.review_batch)
            reviewed += n
            if n == 0:
                break
        print(f"Reviewed {reviewed} papers.")


def cmd_crawl_day(args):
    db.init_db()
    n = pipeline.crawl_day(args.date, category=args.category)
    print(f"Crawled {args.date}: {n} papers.")


def cmd_review_pending(args):
    db.init_db()
    total = 0
    while True:
        n = pipeline.review_pending(limit=args.batch_size)
        total += n
        if n == 0 or not args.loop:
            break
    print(f"Reviewed {total} papers.")


def cmd_daily(args):
    db.init_db()
    result = pipeline.run_daily_job(target_date=args.date, category=args.category)
    print(result)


def cmd_stats(args):
    db.init_db()
    print(db.stats())


def cmd_serve(args):
    from webapp.app import create_app  # local import: keeps Flask optional for crawl-only use

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(prog="scribe")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("backfill", help="Crawl the last N days (default 30) and review them.")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--category", default=config.ARXIV_CATEGORY)
    p.add_argument("--review-batch", type=int, default=config.REVIEW_BATCH_SIZE)
    p.add_argument("--skip-review", action="store_true")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("crawl-day", help="Crawl a single YYYY-MM-DD day.")
    p.add_argument("date")
    p.add_argument("--category", default=config.ARXIV_CATEGORY)
    p.set_defaults(func=cmd_crawl_day)

    p = sub.add_parser("review-pending", help="Send unreviewed papers to Claude.")
    p.add_argument("--batch-size", type=int, default=config.REVIEW_BATCH_SIZE)
    p.add_argument("--loop", action="store_true", help="Keep going until nothing is pending.")
    p.set_defaults(func=cmd_review_pending)

    p = sub.add_parser("daily", help="Crawl yesterday (or --date) + review pending. What the scheduler calls.")
    p.add_argument("--date", default=None)
    p.add_argument("--category", default=config.ARXIV_CATEGORY)
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("stats", help="Print DB counts.")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("serve", help="Run the local web UI.")
    p.add_argument("--host", default=config.WEB_HOST)
    p.add_argument("--port", type=int, default=config.WEB_PORT)
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    _setup_logging()
    args.func(args)


if __name__ == "__main__":
    main()
