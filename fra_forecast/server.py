"""Local JSON API for the teammate's UI; no assets or directory listing."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from . import chat
from .pipeline import refresh
from .verification import comparison_payload, remember_forecast


def make_handler(data_dir):
    data_dir = Path(data_dir)
    refresh_lock = threading.Lock()
    chat_lock = threading.Lock()
    routes = {
        "/api/forecast": (data_dir / "forecast.json", "application/json"),
        "/api/sources": (data_dir / "sources.json", "application/json"),
        "/api/runway18/departures": (data_dir / "runway18-departures.json", "application/json"),
    }

    class Handler(BaseHTTPRequestHandler):
        def send_body(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A cancelled browser request does not invalidate the snapshot.

        def send_json(self, status, value):
            self.send_body(status, json.dumps(value, allow_nan=False).encode())

        def do_GET(self):
            if urlsplit(self.path).path == '/api/chat/status':
                return self.send_json(200, chat.status())
            if urlsplit(self.path).path == '/api/chat/preview':
                try:
                    return self.send_json(200, chat.preview(data_dir))
                except (OSError, ValueError, KeyError):
                    return self.send_json(503, {'error': 'Saved weather data is unavailable.'})
            if urlsplit(self.path).path == "/api/verification":
                try:
                    return self.send_json(200, comparison_payload(data_dir))
                except (OSError, ValueError) as exc:
                    return self.send_json(502, {"error": f"Verification data unavailable: {exc}"})
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
            if urlsplit(self.path).path == '/api/chat':
                origin = self.headers.get('Origin')
                expected = 'http://' + self.headers.get('Host', '')
                if self.headers.get('X-FRA-Chat') != '1' or (origin and origin != expected):
                    return self.send_json(403, {'error': 'Chat requires a same-origin request.'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if length <= 0 or length > 40000:
                        return self.send_json(413, {'error': 'Question is too large.'})
                    body = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError):
                    return self.send_json(400, {'error': 'Invalid question.'})
                if not chat_lock.acquire(blocking=False):
                    return self.send_json(429, {'error': 'The bot is answering another question. Please try shortly.'})
                try:
                    return self.send_json(200, chat.ask(data_dir, body))
                except chat.ChatError as exc:
                    return self.send_json(exc.status, {'error': str(exc)})
                except (OSError, ValueError, KeyError):
                    return self.send_json(503, {'error': 'Project data is unavailable. Refresh the saved data and retry.'})
                finally:
                    chat_lock.release()
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
    snapshot = Path(data_dir) / "forecast.json"
    if snapshot.exists():
        remember_forecast(data_dir, json.loads(snapshot.read_text()))
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data_dir))
    print(f"FRA data API: http://127.0.0.1:{server.server_port}/api/forecast", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
