"""Local JSON API for the teammate's UI; no assets or directory listing."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from .pipeline import refresh


def make_handler(data_dir):
    data_dir = Path(data_dir)
    refresh_lock = threading.Lock()
    routes = {
        "/api/forecast": (data_dir / "forecast.json", "application/json"),
        "/api/sources": (data_dir / "sources.json", "application/json"),
    }

    class Handler(BaseHTTPRequestHandler):
        def send_body(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, value):
            self.send_body(status, json.dumps(value, allow_nan=False).encode())

        def do_GET(self):
            route = routes.get(urlsplit(self.path).path)
            if route is None:
                return self.send_json(404, {"error": "Not found"})
            path, content_type = route
            try:
                body = path.read_bytes()
            except FileNotFoundError:
                return self.send_json(404, {"error": "No saved data yet. Run python3 -m fra_forecast refresh --live-only."})
            self.send_body(200, body, content_type)

        def do_POST(self):
            if urlsplit(self.path).path != "/api/refresh":
                return self.send_json(404, {"error": "Not found"})
            # Require an explicit client header and reject cross-origin browser calls.
            origin = self.headers.get("Origin")
            expected = "http://" + self.headers.get("Host", "")
            if self.headers.get("X-FRA-Refresh") != "1" or (origin and origin != expected):
                return self.send_json(403, {"error": "Refresh requires X-FRA-Refresh: 1 and a same-origin request."})
            if not refresh_lock.acquire(blocking=False):
                return self.send_json(409, {"error": "A refresh is already running. Try again shortly."})
            try:
                snapshot = refresh(data_dir, live_only=True)
                self.send_json(200, snapshot)
            except (OSError, ValueError, KeyError) as exc:
                self.send_json(502, {"error": f"Data refresh failed: {exc}"})
            finally:
                refresh_lock.release()

    return Handler


def serve(data_dir, port=8000):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data_dir))
    print(f"FRA data API: http://127.0.0.1:{server.server_port}/api/forecast", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
