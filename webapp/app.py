from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import db  # noqa: E402


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"), static_url_path="")
    db.init_db()

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

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
        return jsonify(rows)

    @app.get("/api/stats")
    def api_stats():
        return jsonify(db.stats())

    return app


if __name__ == "__main__":
    from src import config

    create_app().run(host=config.WEB_HOST, port=config.WEB_PORT, debug=True)
