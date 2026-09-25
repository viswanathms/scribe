# SCRIBE

**S**cientific **C**orpus **R**etrieval & **I**nsight **B**riefing **E**ngine

Crawls new `cs.AI` papers from arXiv every day, has Claude score each one on
how much implementing it would help an AI-driven organization grow, stores
everything in a local SQLite database, and shows it in a small local web UI
you can sort/filter by importance or date.

## robots.txt compliance

Checked `https://arxiv.org/robots.txt` before building anything. For a
generic user-agent it says:

```
User-agent: *
Crawl-delay: 15
Allow: /archive, /year, /list, /abs, /pdf, /html, /catchup
Disallow: /api, /search, /find, ... (and others)
```

So the crawler:
- Only hits `/catchup/<category>/<date>` (and `/abs`, `/pdf` as links, never fetched
  in bulk) — all explicitly `Allow`ed paths.
- Never touches `/api` or `/search`, which are `Disallow`ed for generic bots
  (this is also why we don't use arXiv's `export.arxiv.org` API host — its
  own `robots.txt` disallows everything).
- Enforces the `Crawl-delay: 15` (15 seconds between every request) in
  `src/crawler.py`, globally, regardless of caller.
- Sends a descriptive `User-Agent` with a contact email, per arXiv's own
  etiquette guidance.

`/catchup/<category>/<YYYY-MM-DD>?abs=True` is arXiv's own "catch up on one
day" view — it returns that day's new submissions **with abstracts inlined**,
so one request gets a full day's papers instead of a listing page plus one
abstract fetch per paper.

## Setup

```bash
cd /Volumes/Work/OpenSource/scribe
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put your ANTHROPIC_API_KEY in .env
```

## First run: backfill the last month

```bash
source venv/bin/activate
export $(grep -v '^#' .env | xargs)   # or just export ANTHROPIC_API_KEY=...
python -m src.cli backfill --days 30
```

This crawls day-by-day (respecting the 15s crawl-delay, so ~30 requests takes
several minutes minimum, more on heavy-volume days that paginate) and then
sends every new paper to Claude for review. Safe to re-run or interrupt —
`crawl-day` upserts on `arxiv_id`, so already-crawled papers are skipped, and
`review-pending` only reviews papers that don't have a score yet.

## View the papers

```bash
python -m src.cli serve
```

Open http://127.0.0.1:8765 — sort by importance or date, filter by day or a
minimum score, expand any paper to read Claude's reasoning.

## Run it daily in the background (macOS launchd)

```bash
cp scheduler/com.scribe.daily.plist ~/Library/LaunchAgents/
# edit ~/Library/LaunchAgents/com.scribe.daily.plist:
#   replace __PROJECT_DIR__ with the absolute path to this folder
launchctl load ~/Library/LaunchAgents/com.scribe.daily.plist
```

This runs `scheduler/run_daily.sh` every day at 07:00 local time, which
activates the venv and runs `python -m src.cli daily` — that crawls
*yesterday* (the last fully-announced arXiv day) and reviews anything
pending. Logs go to `logs/daily.log` and `logs/launchd.*.log`.

To test the job immediately without waiting for 07:00:
```bash
launchctl start com.scribe.daily
```

To stop the schedule:
```bash
launchctl unload ~/Library/LaunchAgents/com.scribe.daily.plist
```

## CLI reference

```bash
python -m src.cli backfill --days 30        # crawl + review the last N days
python -m src.cli crawl-day 2026-09-23      # crawl one specific day
python -m src.cli review-pending --loop     # send unreviewed papers to Claude
python -m src.cli daily                     # what the scheduler runs
python -m src.cli stats                     # counts in the DB
python -m src.cli serve                     # web UI
```

## Data

SQLite DB at `data/scribe.db` (one `papers` table — see `src/db.py`
for the schema: arxiv id, title, authors, abstract, subjects, dates, plus
`importance_score` / `importance_reasoning` / `growth_impact` / `review_tags`
once Claude has reviewed it).
