"""Dependency-free commands for the hackathon data pipeline."""

import argparse
from pathlib import Path
import sys

from .pipeline import refresh


def main(argv=None):
    parser = argparse.ArgumentParser(description="FRA weather ingestion and runway baseline")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("refresh", help="Fetch public data and write frontend JSON and CSV")
    fetch.add_argument("--data-dir", type=Path, default=Path("data"))
    fetch.add_argument("--history-days", type=int, default=14)
    fetch.add_argument("--archive-days", type=int, default=7)
    fetch.add_argument("--labels", type=Path, help="Independent operations-label CSV")
    fetch.add_argument("--live-only", action="store_true", help="Skip historical METAR and forecast archives")
    api = commands.add_parser("serve", help="Serve local forecast JSON endpoints")
    api.add_argument("--data-dir", type=Path, default=Path("data"))
    api.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == "serve":
        from .server import serve
        try:
            serve(args.data_dir, args.port)
        except (OSError, ValueError) as exc:
            print(f"API failed to start: {exc}", file=sys.stderr)
            return 1
        return 0
    if not 1 <= args.history_days <= 30:
        parser.error("--history-days must be between 1 and 30 for this demo")
    if not 0 <= args.archive_days <= args.history_days:
        parser.error("--archive-days must be between 0 and --history-days")
    try:
        snapshot = refresh(args.data_dir, args.history_days, args.archive_days,
                           args.labels, args.live_only)
    except (OSError, ValueError) as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1
    return 0 if snapshot["data_quality"]["forecast_hours_available"] else 1
