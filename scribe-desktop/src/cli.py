"""CLI entrypoint: python -m src.cli <command> ..."""
from __future__ import annotations

import argparse
import datetime as dt
import logging

from . import config, db, pipeline
from .providers import ProviderError, get_provider


def _setup_logging():
    config.ensure_dirs()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def cmd_backfill(args):
    db.init_db()
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=args.days - 1)
    total = pipeline.crawl_range(start, end, category=args.category)
    print(f"Crawled {start} .. {end}: {total} papers total.")
    if not args.skip_review:
        reviewed = pipeline.review_all_pending(batch_size=args.review_batch)
        print(f"Reviewed {reviewed} papers.")


def cmd_crawl_day(args):
    db.init_db()
    n = pipeline.crawl_day(args.date, category=args.category)
    print(f"Crawled {args.date}: {n} papers.")


def cmd_review_pending(args):
    db.init_db()
    if args.loop:
        total = pipeline.review_all_pending(batch_size=args.batch_size)
    else:
        _, total = pipeline.review_pending(limit=args.batch_size)
    print(f"Reviewed {total} papers.")


def cmd_daily(args):
    db.init_db()
    print(pipeline.run_daily_job(target_date=args.date))


def cmd_backfill_summaries(args):
    db.init_db()
    if args.loop:
        total = pipeline.backfill_all_summaries(batch_size=args.batch_size)
    else:
        _, total = pipeline.backfill_summaries(limit=args.batch_size)
    print(f"Summarized {total} papers.")


def cmd_generate_report(args):
    db.init_db()
    path = pipeline.save_report_file(args.date, min_score=args.min_score)
    print(f"Report saved to {path}")


def cmd_stats(args):
    db.init_db()
    print(db.stats())


def cmd_test_connection(args):
    settings = config.load_settings()
    try:
        provider = get_provider(settings)
        provider.test_connection()
    except ProviderError as e:
        print(f"FAILED: {e}")
        raise SystemExit(1)
    print(f"OK: {settings['provider']} / {settings['model']} reachable.")


def cmd_serve(args):
    from webapp.app import create_app

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(prog="scribe")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("backfill", help="Crawl the last N days (default 30) and review them.")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--category", default=None)
    p.add_argument("--review-batch", type=int, default=20)
    p.add_argument("--skip-review", action="store_true")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("crawl-day", help="Crawl a single YYYY-MM-DD day.")
    p.add_argument("date")
    p.add_argument("--category", default=None)
    p.set_defaults(func=cmd_crawl_day)

    p = sub.add_parser("review-pending", help="Send unreviewed papers to the configured provider.")
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--loop", action="store_true", help="Keep going until nothing is pending.")
    p.set_defaults(func=cmd_review_pending)

    p = sub.add_parser("daily", help="Crawl yesterday (or --date) + review pending. What the scheduler calls.")
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("backfill-summaries", help="Fill in the one-line summary for already-reviewed papers.")
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--loop", action="store_true", help="Keep going until nothing is pending.")
    p.set_defaults(func=cmd_backfill_summaries)

    p = sub.add_parser("generate-report", help="Save a markdown digest for one day.")
    p.add_argument("--date", required=True)
    p.add_argument("--min-score", type=int, default=None, help="Defaults to the saved report_threshold setting.")
    p.set_defaults(func=cmd_generate_report)

    p = sub.add_parser("stats", help="Print DB counts.")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("test-connection", help="Validate the configured provider/key/model.")
    p.set_defaults(func=cmd_test_connection)

    p = sub.add_parser("serve", help="Run the local web UI (used standalone or inside the pywebview shell).")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8788)  # distinct from the original scribe project's 8765
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    _setup_logging()
    args.func(args)


if __name__ == "__main__":
    main()
