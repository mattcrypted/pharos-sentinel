"""sentinel_ui.py — a small web UI for the Sentinel risk gate.

Serves the brutalist single-page front end (`sentinel_ui.html`) and a read-only
JSON endpoint that runs the REAL Sentinel `risk_check` (Foundry `cast` under the
hood). Same-origin (no CORS), keyless — it never signs, never holds a key — so it
is safe to expose publicly.

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import sentinel_skill as sentinel

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE / "sentinel_ui.html").read_bytes()
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # keep the console clean
        pass

    def _send(self, code: int, body, ctype: str = "application/json"):
        data = body if isinstance(body, (bytes, bytearray)) else str(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if u.path == "/check":
            q = parse_qs(u.query)
            address = (q.get("address") or [""])[0].strip()
            action = (q.get("action") or ["call"])[0].strip().lower()
            try:
                result = sentinel.risk_check(address, action)
            except Exception as e:  # never leak a stack trace to the client
                result = {"verdict": "unknown", "score": -1,
                          "reasons": [f"risk check failed: {e}"], "data": {}}
            self._send(200, json.dumps(result))
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
