from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fra_forecast.server import make_handler
from scripts.prepare_deployment import prepare


class HostingTests(unittest.TestCase):
    def test_packaging_excludes_secrets_and_training_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "source", Path(folder) / "bundle"
            source.mkdir()
            (source / "forecast.json").write_text(json.dumps({"schema_version": "1.1", "forecast": [{}] * 48}))
            (source / ".env").write_text("SECRET=never-upload")
            (source / "training.csv").write_text("private")
            operations = source / "models" / "operations-v3"
            operations.mkdir(parents=True)
            (operations / "manifest.json").write_text('{}')
            history = source / "operations"
            history.mkdir()
            (history / "labels.csv").write_text("local source history")
            prepare(source, target)
            self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()),
                             ["forecast.json", "models/operations-v3/manifest.json"])
            with self.assertRaises(FileExistsError):
                prepare(source, target)

    def test_https_origin_and_stale_refresh(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / "forecast.json"
            snapshot.write_text('{"forecast": []}')
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(folder, origin_scheme="https", refresh_after_seconds=600))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def request(method, path, origin=None):
                connection = HTTPConnection("127.0.0.1", server.server_port)
                headers = {"Host": "fra.example", "X-FRA-Refresh": "1", "X-FRA-Chat": "1", "Content-Type": "application/json"}
                if origin:
                    headers["Origin"] = origin
                connection.request(method, path, body='{"message":"Wind?"}' if method == "POST" else None, headers=headers)
                response = connection.getresponse()
                result = response.status, json.loads(response.read())
                connection.close()
                return result
            try:
                with patch("fra_forecast.server.refresh", return_value={"refreshed": True}) as refresh:
                    self.assertEqual(request("GET", "/api/forecast")[0], 200)
                    refresh.assert_not_called()
                    os.utime(snapshot, (1, 1))
                    self.assertEqual(request("GET", "/api/forecast")[0], 200)
                    refresh.assert_called_once_with(Path(folder), live_only=True, history_days=1)
                    self.assertEqual(request("POST", "/api/refresh", "https://fra.example")[0], 200)
                    self.assertEqual(request("POST", "/api/refresh", "https://other.example")[0], 403)
                    self.assertEqual(request("POST", "/api/refresh", "http://fra.example")[0], 403)
                with patch("fra_forecast.server.chat.run", return_value=(200, {"answer": "ok"})):
                    self.assertEqual(request("POST", "/api/chat", "https://fra.example")[0], 200)
                with patch("fra_forecast.server.weather_bot.ask", return_value={"answer": "ok"}):
                    self.assertEqual(request("POST", "/api/weather-bot", "https://fra.example")[0], 200)
                with patch("fra_forecast.server.refresh", side_effect=OSError("offline")):
                    self.assertEqual(request("GET", "/api/forecast"), (200, {"forecast": []}))
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
