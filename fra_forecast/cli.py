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
    fetch.add_argument("--no-ml", action="store_true", help="Explicitly use the raw baseline without loading a wind model")
    fetch.add_argument("--no-departures", action="store_true", help="Skip the public flight-board refresh")
    departures = commands.add_parser("refresh-departures", help="Match upcoming FRA flights to RWY18 weather")
    departures.add_argument("--data-dir", type=Path, default=Path("data"))
    departures.add_argument("--hours", type=int, default=48)
    prepare = commands.add_parser("prepare-ml", help="Backfill ICON-EU runs and DWD targets for wind training")
    prepare.add_argument("--data-dir", type=Path, default=Path("data"))
    prepare.add_argument("--days", type=int, default=180)
    prepare.add_argument("--max-minutes", type=float, default=50)
    train = commands.add_parser("train-ml", help="Train and chronologically evaluate wind corrections")
    train.add_argument("--data-dir", type=Path, default=Path("data"))
    api = commands.add_parser("serve", help="Serve local forecast JSON endpoints")
    api.add_argument("--data-dir", type=Path, default=Path("data"))
    api.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == "refresh-departures":
        from .departures import refresh_departures
        try:
            report=refresh_departures(args.data_dir,args.hours)
            return 0 if report["source"]["status"] != "unavailable" else 1
        except (OSError,ValueError,KeyError) as exc:
            print(f"Departure refresh failed: {exc}",file=sys.stderr)
            return 1
    if args.command in ("prepare-ml","train-ml"):
        try:
            if args.command == "prepare-ml":
                from .ml_data import prepare as prepare_data
                if args.max_minutes <= 0:
                    parser.error("--max-minutes must be positive")
                report = prepare_data(args.data_dir,args.days,args.max_minutes)
                return 0 if report["rows"] else 1
            from .wind_ml import train as train_model
            train_model(args.data_dir)
            return 0
        except ImportError as exc:
            print(f"ML dependencies unavailable: {exc}. Install with: python3 -m pip install -e '.[ml]'",file=sys.stderr)
            return 1
        except (OSError,ValueError,KeyError) as exc:
            print(f"ML command failed: {exc}",file=sys.stderr)
            return 1
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
                           args.labels, args.live_only,use_ml=not args.no_ml,
                           include_departures=not args.no_departures)
    except (OSError, ValueError) as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1
    return 0 if snapshot["data_quality"]["forecast_hours_available"] else 1
