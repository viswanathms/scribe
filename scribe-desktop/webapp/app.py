from __future__ import annotations

import datetime as dt
import json
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, db, pipeline  # noqa: E402
from src.providers import ProviderError, get_provider  # noqa: E402

_job_lock = threading.Lock()
_job = {"type": None, "state": "idle", "progress": 0, "total": 0, "detail": "", "error": None}


def _job_snapshot() -> dict:
    with _job_lock:
        return dict(_job)


def _set_job(**kwargs):
    with _job_lock:
        _job.update(kwargs)


def _run_extract_job(days: int, category: str):
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=days - 1)
    total_days = (end - start).days + 1
    _set_job(type="extract", state="running", progress=0, total=total_days, detail="", error=None)
    day = start
    day_index = 0
    try:
        while day <= end:
            day_index += 1
            n = pipeline.crawl_day(day.isoformat(), category=category)
            _set_job(progress=day_index, detail=f"{day.isoformat()}: {n} papers")
            day += dt.timedelta(days=1)
        _set_job(state="done")
    except Exception as e:  # noqa: BLE001
        _set_job(state="error", error=str(e))


def _run_review_job(batch_size: int = 1):
    with db.get_conn() as conn:
        total = len(db.get_unreviewed(conn, limit=100000))
    _set_job(type="review", state="running", progress=0, total=total, detail="", error=None)
    reviewed = 0
    stalls = 0
    try:
        while True:
            attempted, n = pipeline.review_pending(limit=batch_size)
            if attempted == 0:
                break
            reviewed += n
            _set_job(progress=reviewed, detail=f"{reviewed}/{total} reviewed")
            stalls = 0 if n else stalls + 1
            if stalls >= 20:
                raise RuntimeError("20 consecutive failed reviews in a row -- stopping instead of spinning")
        _set_job(state="done")
    except Exception as e:  # noqa: BLE001
        _set_job(state="error", error=str(e))


def _run_summary_backfill_job(batch_size: int = 1):
    with db.get_conn() as conn:
        total = len(db.get_missing_summaries(conn, limit=100000))
    _set_job(type="summarize", state="running", progress=0, total=total, detail="", error=None)
    done = 0
    stalls = 0
    try:
        while True:
            attempted, n = pipeline.backfill_summaries(limit=batch_size)
            if attempted == 0:
                break
            done += n
            _set_job(progress=done, detail=f"{done}/{total} summarized")
            stalls = 0 if n else stalls + 1
            if stalls >= 20:
                raise RuntimeError("20 consecutive failed summaries in a row -- stopping instead of spinning")
        _set_job(state="done")
    except Exception as e:  # noqa: BLE001
        _set_job(state="error", error=str(e))


def _public_settings(settings: dict) -> dict:
    out = dict(settings)
    out["api_key_set"] = bool(out.pop("api_key", None))
    return out


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"), static_url_path="")
    db.init_db()

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # --- papers / stats (unchanged shape from the original SCRIBE UI) ---

    @app.get("/api/papers")
    def api_papers():
        sort_by = request.args.get("sort", "published_date")
        order = request.args.get("order", "desc")
        date = request.args.get("date") or None
        min_score = request.args.get("min_score", type=int)
        limit = request.args.get("limit", default=500, type=int)

        rows = db.list_papers(sort_by=sort_by, order=order, date=date, min_score=min_score, limit=limit)
        for r in rows:
            r["review_tags"] = json.loads(r["review_tags"]) if r.get("review_tags") else []
            r["criteria_snapshot"] = json.loads(r["criteria_snapshot"]) if r.get("criteria_snapshot") else None
        return jsonify(rows)

    @app.get("/api/stats")
    def api_stats():
        return jsonify(db.stats())

    # --- settings / onboarding ---

    @app.get("/api/settings")
    def api_get_settings():
        return jsonify(_public_settings(config.load_settings()))

    @app.post("/api/settings")
    def api_save_settings():
        body = request.get_json(force=True)
        settings = config.load_settings()
        for key in ("provider", "base_url", "model", "category"):
            if key in body:
                settings[key] = body[key]
        if "report_threshold" in body:
            settings["report_threshold"] = int(body["report_threshold"])
        if body.get("api_key"):  # only overwrite if a new one was actually typed
            settings["api_key"] = body["api_key"]
        if "criteria" in body:
            settings["criteria"] = {**settings["criteria"], **body["criteria"]}
        if body.get("onboarded"):
            settings["onboarded"] = True
        config.save_settings(settings)
        return jsonify(_public_settings(settings))

    @app.post("/api/settings/test")
    def api_test_settings():
        body = request.get_json(force=True) or {}
        settings = {**config.load_settings(), **body}
        try:
            provider = get_provider(settings)
            provider.test_connection()
        except ProviderError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        return jsonify({"ok": True})

    @app.get("/api/settings/models")
    def api_list_models():
        settings = {**config.load_settings(), **request.args}
        try:
            provider = get_provider(settings)
        except ProviderError as e:
            return jsonify({"models": [], "error": str(e)})
        return jsonify({"models": provider.list_models()})

    @app.get("/api/settings/criteria-suggestions")
    def api_criteria_suggestions():
        return jsonify(
            {
                "type": config.CRITERIA_TYPE_SUGGESTIONS,
                "function": config.CRITERIA_FUNCTION_SUGGESTIONS,
            }
        )

    # --- extraction / review jobs ---

    @app.post("/api/extract")
    def api_extract():
        if _job_snapshot()["state"] == "running":
            return jsonify({"error": "A job is already running."}), 409
        body = request.get_json(force=True) or {}
        days = int(body.get("days", 30))
        category = body.get("category") or config.load_settings()["category"]
        thread = threading.Thread(target=_run_extract_job, args=(days, category), daemon=True)
        thread.start()
        return jsonify({"started": True}), 202

    @app.post("/api/review/run")
    def api_review_run():
        if _job_snapshot()["state"] == "running":
            return jsonify({"error": "A job is already running."}), 409
        thread = threading.Thread(target=_run_review_job, daemon=True)
        thread.start()
        return jsonify({"started": True}), 202

    @app.get("/api/job")
    def api_job():
        return jsonify(_job_snapshot())

    # --- report / subject graph / calendar ---

    @app.get("/api/dates")
    def api_dates():
        lo, hi = db.get_date_bounds()
        return jsonify({"earliest": lo, "latest": hi})

    @app.get("/api/report")
    def api_report():
        date = request.args.get("date")
        if not date:
            _, latest = db.get_date_bounds()
            date = latest
        min_score = request.args.get("min_score", type=int)
        papers = pipeline.generate_report(date, min_score) if date else []
        return jsonify({"date": date, "min_score": min_score if min_score is not None else config.load_settings()["report_threshold"], "papers": papers})

    @app.get("/api/stats/by-subject")
    def api_by_subject():
        limit = request.args.get("limit", default=15, type=int)
        return jsonify(db.count_by_subject(limit=limit))

    @app.get("/api/stats/by-day")
    def api_by_day():
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        if not year or not month:
            _, latest = db.get_date_bounds()
            if latest:
                year, month = int(latest[:4]), int(latest[5:7])
            else:
                today = dt.date.today()
                year, month = today.year, today.month
        return jsonify({"year": year, "month": month, "days": db.get_calendar_data(year, month)})

    @app.post("/api/report/backfill-summaries")
    def api_backfill_summaries():
        if _job_snapshot()["state"] == "running":
            return jsonify({"error": "A job is already running."}), 409
        thread = threading.Thread(target=_run_summary_backfill_job, daemon=True)
        thread.start()
        return jsonify({"started": True}), 202

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8765, debug=True)
