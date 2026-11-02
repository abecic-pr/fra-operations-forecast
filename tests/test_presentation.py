from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from fra_forecast.server import make_handler


class PresentationTests(unittest.TestCase):
    def test_page_assets_missing_reports_and_private_paths(self):
        with TemporaryDirectory() as root:
            Path(root, "forecast.json").write_text('{"forecast": []}')
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                def get(path):
                    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                    try:
                        connection.request("GET", path)
                        response = connection.getresponse()
                        return response.status, response.getheader("Content-Type"), response.read()
                    finally:
                        connection.close()

                for path, content_type in [("/how-it-works", "text/html"),
                                           ("/how-it-works/?presentation=1", "text/html"),
                                           ("/how-it-works/style.css", "text/css"),
                                           ("/how-it-works/page.js", "text/javascript"),
                                           ("/how-it-works/hero.js", "text/javascript"),
                                           ("/how-it-works/airport-scene.js", "text/javascript"),
                                           ("/how-it-works/week-scene.js", "text/javascript")]:
                    with self.subTest(path=path):
                        status, mime, body = get(path)
                        self.assertEqual(status, 200)
                        self.assertIn(content_type, mime)
                        self.assertTrue(body)
                self.assertIn(b"How our ML works", get("/how-it-works")[2])
                for path in ["/", "/.env", "/how-it-works/../server.py",
                             "/how-it-works/%2e%2e/server.py", "/data/forecast.json",
                             "/api/model-comparison"]:
                    with self.subTest(path=path):
                        self.assertEqual(get(path)[0], 404)
                self.assertEqual(json.loads(get("/api/forecast")[2]), {"forecast": []})
                report = Path(root, "comparison", "evaluation.json")
                report.parent.mkdir()
                report.write_text('{"model_version": "wind-comparison-v1"}')
                self.assertEqual(json.loads(get("/api/model-comparison")[2]),
                                 {"model_version": "wind-comparison-v1"})
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
