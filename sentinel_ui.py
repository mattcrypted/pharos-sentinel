"""sentinel_ui.py — a small web UI for the Sentinel risk gate.

Serves the sleek single-page front end (`sentinel_ui.html`) and a read-only
JSON endpoint that runs the REAL Sentinel `risk_check` (Foundry `cast` under the
hood). Same-origin (no CORS), keyless — it never signs, never holds a key — so it
is safe to expose publicly. `/check` is concurrency-capped (SENTINEL_MAX_CONCURRENCY,
default 4) and sheds excess load with 429, so a flood can't exhaust the host.

    python sentinel_ui.py                 # http://localhost:8000
    HOST=0.0.0.0 PORT=8000 python sentinel_ui.py   # for a container/host (reads $PORT)

Endpoints:
    GET /                          -> the UI page
    GET /check?address=..&action=  -> {verdict, score, reasons[], data{}}  (JSON)
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import sentinel_skill as sentinel

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE / "sentinel_ui.html").read_bytes()
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Concurrency cap: each /check fans out to ~12 `cast` subprocesses (warm prefetch),
# so an unbounded flood could exhaust a small host and hammer the RPC. Cap the
# number of in-flight risk checks and shed the rest with 429 (env-tunable).
MAX_CONCURRENCY = max(1, int(os.environ.get("SENTINEL_MAX_CONCURRENCY", "4")))
_inflight = threading.BoundedSemaphore(MAX_CONCURRENCY)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # keep the console clean
        pass

    def _send(self, code: int, body, ctype: str = "application/json", headers: dict | None = None):
        data = body if isinstance(body, (bytes, bytearray)) else str(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if u.path == "/check":
            if not _inflight.acquire(blocking=False):
                # shed load rather than spawn unbounded `cast` subprocesses
                busy = {"verdict": "unknown", "score": -1,
                        "reasons": ["risk gate busy — too many concurrent checks, retry shortly"],
                        "data": {}}
                self._send(429, json.dumps(busy), headers={"Retry-After": "2"})
                return
            try:
                q = parse_qs(u.query)
                address = (q.get("address") or [""])[0].strip()
                action = (q.get("action") or ["call"])[0].strip().lower()
                try:
                    result = sentinel.risk_check(address, action)
                except Exception as e:  # never leak a stack trace to the client
                    result = {"verdict": "unknown", "score": -1,
                              "reasons": [f"risk check failed: {e}"], "data": {}}
                self._send(200, json.dumps(result))
            finally:
                _inflight.release()
            return
        if u.path == "/healthz":
            self._send(200, json.dumps({"ok": True}))
            return
        self._send(404, json.dumps({"error": f"no resource at {u.path}"}))


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Sentinel UI on http://localhost:{PORT}  "
          f"(read-only risk gate; runs Foundry cast, holds no key)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
