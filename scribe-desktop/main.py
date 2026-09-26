"""Desktop entry point. Runs the Flask backend in a background thread and
shows it in a native window via pywebview -- no browser chrome, a real
window/Dock icon once packaged into a .app. This is what PyInstaller points
at when building SCRIBE.app.
"""
from __future__ import annotations

import threading
import time

import requests
import webview

from src import config, db

PORT = 8788


def _run_flask():
    from webapp.app import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def _wait_for_server(timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{PORT}/api/stats"
    while time.monotonic() < deadline:
        try:
            if requests.get(url, timeout=1).ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.2)
    return False


def main():
    config.ensure_dirs()
    db.init_db()

    thread = threading.Thread(target=_run_flask, daemon=True)
    thread.start()
    _wait_for_server()

    webview.create_window(
        "SCRIBE",
        f"http://127.0.0.1:{PORT}",
        width=1100,
        height=900,
        min_size=(760, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
