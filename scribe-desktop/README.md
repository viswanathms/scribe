# SCRIBE (desktop)

**S**cientific **C**orpus **R**etrieval & **I**nsight **B**riefing **E**ngine

The Mac-app evolution of the original [`scribe`](..) project, kept as a
subfolder of it for convenience. This is still a **fully independent
project** — its own venv, its own database, its own launchd job. It borrowed
working code (the arXiv crawler) from the parent project by copying it in,
not by depending on it at runtime; the parent `scribe` project is untouched
and keeps working standalone.

New in this version:
- **Multi-provider**: Anthropic, OpenAI, or a local Ollama model — picked and
  authenticated in an onboarding screen instead of hardcoded.
- **User-defined ranking criteria** (Type / Function / Area / Other
  conditions), injected into the review prompt, editable anytime.
- **Native desktop window** via `pywebview` instead of "open a browser tab."
- Settings and the database live in `~/Library/Application Support/SCRIBE/`,
  not inside the project folder — survives reinstalls, shared between the
  app and the background daily job.

## Setup

```bash
cd /Volumes/Work/OpenSource/scribe/scribe-desktop
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
./run_app.sh
```

Opens SCRIBE in its own native window (no browser). First launch walks you
through:
1. **Provider & auth** — Anthropic / OpenAI / Ollama, base URL, API key
   (skipped for Ollama), model. "Test connection" must pass before continuing.
2. **Extract** — arXiv categories/fields to track (comma-separated, e.g.
   `cs.AI, cs.LG, cs.CL`; default `cs.AI`) and how many days back to crawl.
   Each category is crawled and reviewed independently -- a paper that's a
   "new submission" under more than one tracked category (rare) just gets
   upserted once, no duplicate. Runs for real, respecting arXiv's 15s
   crawl-delay per category per day, so this takes longer the more
   categories you track.
3. **Criteria** — Type / Function / Area / Other conditions. Saving triggers
   the first review pass over everything just extracted, using whichever
   provider you configured.

After that you land on the ranked list. The gear icon (or the **×** in the
wizard's top-right corner) reopens/closes the same wizard to change
provider/keys/criteria/categories at any time without having to click
through every step; "Extract more" jumps straight to step 2.

Prefer a browser tab instead of the native window? `python -m src.cli serve`
serves the exact same app on `http://127.0.0.1:8788`.

## Run it daily in the background (macOS launchd)

```bash
cp scheduler/com.scribe.daily.plist ~/Library/LaunchAgents/
# edit ~/Library/LaunchAgents/com.scribe.daily.plist:
#   replace __PROJECT_DIR__ with the absolute path to this folder
launchctl load ~/Library/LaunchAgents/com.scribe.daily.plist
```

Runs `scheduler/run_daily.sh` every day at 07:00 local time — crawls
*yesterday* and reviews anything pending, using whatever provider/criteria
are currently saved. Works whether or not the app window is open. Logs at
`~/Library/Application Support/SCRIBE/logs/daily.log`.

Test immediately: `launchctl start com.scribe.daily`
Stop: `launchctl unload ~/Library/LaunchAgents/com.scribe.daily.plist`

## CLI reference

```bash
python -m src.cli backfill --days 30        # crawl + review the last N days
python -m src.cli crawl-day 2026-09-23      # crawl one specific day
python -m src.cli review-pending --loop     # send unreviewed papers to the configured provider
python -m src.cli daily                     # what the scheduler runs
python -m src.cli test-connection           # validate the configured provider/key/model
python -m src.cli stats                     # counts in the DB
python -m src.cli serve                     # web UI in a browser tab, port 8788
```

## Data & settings

- `~/Library/Application Support/SCRIBE/config.json` — provider, base URL,
  API key, model, categories (a list, not a single value), criteria.
  `chmod 600` (contains a key in
  plaintext — declined Keychain storage in favor of a simple file; see
  project history if that tradeoff needs revisiting).
- `~/Library/Application Support/SCRIBE/scribe.db` — same `papers` schema as
  the original project, plus `review_provider`, `criteria_snapshot`
  (JSON: the Type/Function/Area/Other active when that paper was scored, so
  old reviews stay auditable even after you change criteria), and `summary`
  (one-line plain-English "what this paper does," used by the Daily Report).
- `~/Library/Application Support/SCRIBE/reports/YYYY-MM-DD.md` — a markdown
  digest auto-saved by the daily background job for each day it runs,
  filtered to `report_threshold` (default 7, editable from the Daily
  Report tab in-app).

## Daily Report / By Subject / Calendar tabs

Three views alongside the original paper list:

- **Daily Report** — pick a date and a minimum importance score; see just
  the title, one-line summary, and a link for everything that clears the
  bar that day. The same view is auto-saved as markdown by the nightly job
  (see above), so there's a standing record even if you never open the app.
- **By Subject** — paper counts grouped by arXiv's own `primary_subject`
  (e.g. "Machine Learning (cs.LG)") — already crawled data, no extra LLM
  calls or backfill needed for this one.
- **Calendar** — a month grid; each day's color reflects that day's average
  importance score (light blue = low, mid blue = mid, dark blue = high;
  validated colorblind-safe as an ordinal ramp via the dataviz skill's
  checker, since the original score-badge palette failed that same check),
  with the paper count shown as a number on the cell.

### Backfilling summaries for existing data

New papers get a `summary` automatically as part of their normal review.
Papers reviewed *before* this feature existed need a one-time catch-up:

```bash
./scripts/backfill_summaries.sh          # batch size 1 (default)
./scripts/backfill_summaries.sh 5        # or a bigger batch size
```

Same reliability pattern as the original review backfill: detached
(`nohup`), wrapped in `caffeinate -i` so it survives sleep, safe to
interrupt and re-run (only ever touches papers still missing a summary).
Check progress with `venv/bin/python -m src.cli stats` or:
```bash
sqlite3 ~/Library/Application\ Support/SCRIBE/scribe.db \
  "SELECT COUNT(*) FROM papers WHERE importance_score IS NOT NULL AND summary IS NULL;"
```

### Interests ("read later")

Every paper -- in the Papers list and the Daily Report -- has a star toggle.
Starring adds it to **Interests**, a 5th tab showing everything you've
bookmarked and haven't yet marked read. "Mark as read" clears it from that
list without deleting the bookmark history (`interest_marked_at` /
`interest_read_at` are separate columns -- unread interests are
`marked_at IS NOT NULL AND read_at IS NULL`). Re-starring a paper always
resets it to unread.

### Daily Report extras

The standalone "By Subject" tab is gone -- the subject bar chart now lives
*inside* the Daily Report, computed client-side from that day's filtered
papers (not an all-time global count), so it shows what today's shortlist
actually spans rather than a static all-time distribution. Each report item
also shows a subject tag (arXiv's `primary_subject`, shortened to its code,
e.g. `cs.LG`) and a direct PDF link alongside the abstract link.

### Calendar -> Daily Report

Any day cell with data is clickable -- it jumps straight to the Daily
Report tab with that date pre-filled and the report loaded.

## UI rework: pagination, search, alignment, theme

- **Real pagination** on the Papers tab (`/api/papers` now takes
  `page`/`page_size` and returns `{items, total, page, page_size}`, a
  breaking change from the old bare-array response) -- 25/page,
  server-side `LIMIT`/`OFFSET`, so 3,000+ papers don't all load at once.
- **Search**: a search box in the Papers tab controls (title/abstract/
  summary/authors, `LIKE`-based -- fine at this row count, no FTS5 needed),
  debounced 300ms, resets to page 1 on change. A **global search** box in
  the header is always visible regardless of tab; pressing Enter switches
  to Papers and applies the same query there, rather than being a second,
  separate search surface.
- **Alignment bug fixed**: the star (bookmark) button on paper cards used
  to sit as plain inline content inside the `<h2>` title, so on a title
  long enough to wrap, the star could wrap onto its own orphaned line
  below the card. Fixed by wrapping the title and star in a flex row
  (`.title-row`) with the star as a non-wrapping flex item -- confirmed
  by literally screenshotting a card whose title wraps, in both themes,
  not just by reasoning about the CSS.
- **Tag chips capped at 3 + "+N"** instead of wrapping to a second line,
  so card heights stay consistent down a page instead of some cards
  being visibly taller than others purely from tag count.
- **Theme refresh**: wider content column (900px -> 1040px, was leaving a
  lot of dead space on desktop), subtle card shadows instead of flat
  borders only, a small logo mark next to the wordmark, refined spacing.
  Score badge colors (red/orange/gray) were deliberately left alone --
  they're a separate, previously-flagged accessibility issue (see the
  Calendar section above) and changing them wasn't part of this ask.

## Ollama notes

Reasoning-tuned models (e.g. `qwen3.5`) can spend 30s+ on hidden
chain-of-thought before ever emitting the JSON review, which blew past the
original 60s timeout in testing. The Ollama provider now sends `think: false`
and falls back to extracting the first `{...}` block if a model still drifts
into prose despite the JSON schema constraint. `mistral:latest` and
`llama3:latest` were confirmed to follow the schema cleanly and quickly; if
you hit unparsable-response errors with a different model, try one of those.

## Packaging into a real .app / DMG

```bash
./scripts/build_app.sh
```

Builds from `SCRIBE.spec`, ad-hoc signs (no paid Apple Developer account —
that was an explicit tradeoff for "shareable with a few people," not
public distribution), and packages `dist/SCRIBE.app` into `dist/SCRIBE.dmg`
with an `Applications` symlink for drag-to-install. Both `dist/` and
`build/` are gitignored; `SCRIBE.spec` is checked in and is the source of
truth for the build (edit it, don't hand-edit `dist/`).

**First launch, on this Mac or any other:** right-click `SCRIBE.app` →
Open. Ad-hoc signing isn't notarized, so a plain double-click gets
Gatekeeper-blocked the first time; right-click → Open bypasses that once,
permanently, for that copy of the app.

The packaged app reads/writes the same `~/Library/Application
Support/SCRIBE/` data as running from source — no migration needed either
direction.

## Backfilling a large date range

Reviewing runs through whatever LLM you configured, one paper at a time.
Hosted APIs (Anthropic/OpenAI) handle large backfills in minutes; a local
Ollama model does not — expect roughly 7-10s/paper (confirmed with
`mistral:latest` on this machine), so a 30-day backfill (~3,000+ papers)
is a multi-hour job. Two things worth knowing:
- The in-app "Save & review papers" step runs the review loop as a
  background *thread inside the app process* — closing the app window
  kills it partway through.
- For a long backfill, prefer running it as its own detached process, under
  `caffeinate -i` so it survives the Mac sleeping (a plain background
  process just stalls through sleep, it doesn't get killed, but wall-clock
  progress grinds to a halt until you wake the machine):
  ```bash
  nohup caffeinate -i venv/bin/python -m src.cli review-pending --loop --batch-size 1 \
    >> ~/Library/Application\ Support/SCRIBE/logs/backfill_review.log 2>&1 &
  disown
  ```
  Check progress anytime with `venv/bin/python -m src.cli stats` (reliable)
  rather than the in-app progress bar (only meaningful while that process
  is still alive). `review_pending`'s loop only stops when there's truly
  nothing left unreviewed (or 20 consecutive fully-failed batches) — an
  earlier version wrongly stopped on the first transient provider timeout;
  don't reintroduce that by reverting to a plain `n == 0` check if editing
  `pipeline.py`.

## Not done yet

- Multiple named criteria profiles, re-ranking existing papers on demand,
  and live model-catalog fetching for Anthropic/OpenAI were explicitly
  scoped out of v1 (see project decisions) — deliberate, not oversights.
- No custom app icon yet (uses PyInstaller's default).
- Not notarized — fine for sharing with a few people who'll right-click
  Open once; would need a paid Apple Developer account for public
  distribution without that friction.
