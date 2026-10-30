"""Vercel entrypoint for the existing forecast API."""
from pathlib import Path
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit

from fra_forecast.server import make_handler

# shortcut: cache/history are instance-local, use durable storage for long-term evaluation.
data_dir = Path(tempfile.mkdtemp(prefix="fra-forecast-")) / "data"
bundle = Path(__file__).resolve().parent.parent / "deployment-data"
if bundle.is_dir():
    shutil.copytree(bundle, data_dir)
else:
    data_dir.mkdir(parents=True)  # Git deployments fetch data on the first forecast request.


class handler(make_handler(data_dir, origin_scheme="https", refresh_after_seconds=600)):
    def do_GET(self):
        route = parse_qs(urlsplit(self.path).query).get("_route")
        if route:
            self.path = route[0]
        super().do_GET()

    def do_POST(self):
        route = parse_qs(urlsplit(self.path).query).get("_route")
        if route:
            self.path = route[0]
        super().do_POST()
