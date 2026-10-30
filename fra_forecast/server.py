"""Local JSON API and an allowlisted presentation page; no directory listing."""

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from . import chat, weather_bot
from .pipeline import refresh
from .verification import comparison_payload, remember_forecast
from .wind_ml import MODEL_VERSION


def make_handler(data_dir, *, origin_scheme="http", refresh_after_seconds=None):
    data_dir = Path(data_dir)
    presentation = Path(__file__).parent / "presentation"
    refresh_lock = threading.Lock()
    chat_lock = threading.Lock()
    weather_bot_lock = threading.Lock()
    chat_slots = threading.BoundedSemaphore(2)
    chat_requests = deque()
    routes = {
        "/how-it-works": (presentation / "index.html", "text/html; charset=utf-8"),
        "/how-it-works/": (presentation / "index.html", "text/html; charset=utf-8"),
        "/how-it-works/style.css": (presentation / "style.css", "text/css; charset=utf-8"),
        "/how-it-works/page.js": (presentation / "page.js", "text/javascript; charset=utf-8"),
        "/api/traffic": (data_dir / "traffic.json", "application/json"),
        "/api/forecast": (data_dir / "forecast.json", "application/json"),
        "/api/sources": (data_dir / "sources.json", "application/json"),
        "/api/model-metrics": (data_dir / "models" / MODEL_VERSION / "metrics.json", "application/json"),
        "/api/runway18/departures": (data_dir / "runway18-departures.json", "application/json"),
        "/api/operations-metrics": (data_dir / "operations-evaluation.json", "application/json"),
        "/api/discovery": (data_dir / "comparison" / "discovery.json", "application/json"),
        "/api/model-comparison": (data_dir / "comparison" / "evaluation.json", "application/json"),
        "/api/forecast-comparison": (data_dir / "comparison" / "forecast.json", "application/json"),
        "/api/forecast-agent": (data_dir / "comparison" / "agent.json", "application/json"),
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
            if urlsplit(self.path).path == "/api/forecast" and refresh_after_seconds is not None:
                snapshot = data_dir / "forecast.json"
                if (not snapshot.exists() or time.time() - snapshot.stat().st_mtime > refresh_after_seconds) and refresh_lock.acquire(blocking=False):
                    try:
                        refresh(data_dir, live_only=True, history_days=1)
                    except (OSError, ValueError, KeyError) as exc:
                        self.log_error("Automatic refresh failed: %s", exc)
                    finally:
                        refresh_lock.release()
            if urlsplit(self.path).path == '/api/weather-bot/status':
                return self.send_json(200, weather_bot.status())
            if urlsplit(self.path).path == '/api/weather-bot/preview':
                try:
                    return self.send_json(200, weather_bot.preview(data_dir))
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
                return self.send_json(404, {"error": "Requested data is unavailable. Run refresh for forecasts or train-ml for model metrics."})
            self.send_body(200, body, content_type)

        def do_POST(self):
            if urlsplit(self.path).path == '/api/weather-bot':
                origin = self.headers.get('Origin')
                expected = origin_scheme + '://' + self.headers.get('Host', '')
                if self.headers.get('X-FRA-Chat') != '1' or (origin and origin != expected):
                    return self.send_json(403, {'error': 'Chat requires a same-origin request.'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if length <= 0 or length > 40000:
                        return self.send_json(413, {'error': 'Question is too large.'})
                    body = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError):
                    return self.send_json(400, {'error': 'Invalid question.'})
                if not weather_bot_lock.acquire(blocking=False):
                    return self.send_json(429, {'error': 'The bot is answering another question. Please try shortly.'})
                try:
                    return self.send_json(200, weather_bot.ask(data_dir, body))
                except weather_bot.ChatError as exc:
                    return self.send_json(exc.status, {'error': str(exc)})
                except (OSError, ValueError, KeyError):
                    return self.send_json(503, {'error': 'Project data is unavailable. Refresh the saved data and retry.'})
                finally:
                    weather_bot_lock.release()
            if urlsplit(self.path).path == "/api/chat":
                return self.chat_reply()
            if urlsplit(self.path).path != "/api/refresh":
                return self.send_json(404, {"error": "Not found"})
            # Require an explicit client header and reject cross-origin browser calls.
            origin = self.headers.get("Origin")
            expected = origin_scheme + "://" + self.headers.get("Host", "")
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

        def chat_reply(self):
            origin = self.headers.get("Origin")
            expected = origin_scheme + "://" + self.headers.get("Host", "")
            if self.headers.get("X-FRA-Chat") != "1" or (origin and origin != expected):
                return self.send_json(403, {"error": "forbidden", "answer": "Chat requires X-FRA-Chat: 1 and a same-origin request."})
            if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                return self.send_json(400, {"error": "invalid_request", "answer": "Send application/json with Content-Length."})
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            if not 0 < size <= chat.MAX_BODY:
                return self.send_json(413 if size > chat.MAX_BODY else 400,
                                      {"error": "invalid_body_size", "answer": "Chat body must contain 1–16384 bytes."})
            try:
                self.connection.settimeout(10)
                body = json.loads(self.rfile.read(size))
                chat.validate_request(body)
            except (OSError, ValueError, UnicodeError):
                return self.send_json(400, {"error": "invalid_request", "answer": "Invalid chat message, history or JSON body."})
            with chat_lock:
                now = time.monotonic()
                while chat_requests and chat_requests[0] <= now - 60:
                    chat_requests.popleft()
                if len(chat_requests) >= 12 or not chat_slots.acquire(blocking=False):
                    return self.send_json(429, {"error": "rate_limited", "answer": "Chat is busy. Try again shortly."})
                chat_requests.append(now)
            try:
                status, result = chat.run(data_dir, body)
                self.send_json(status, result)
            finally:
                chat_slots.release()

    return Handler


def serve(data_dir, port=8000):
    snapshot = Path(data_dir) / "forecast.json"
    if snapshot.exists():
        remember_forecast(data_dir, json.loads(snapshot.read_text()))
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data_dir))
    print(f"FRA data API: http://127.0.0.1:{server.server_port}/api/forecast", flush=True)
    print(f"ML presentation: http://127.0.0.1:{server.server_port}/how-it-works", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
