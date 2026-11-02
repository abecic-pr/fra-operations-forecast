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
    operations = commands.add_parser("train-operations", help="Train OD from independently sourced interval or point labels")
    operations.add_argument("--data-dir", type=Path, default=Path("data"))
    operations.add_argument("--labels", type=Path, required=True)
    history = commands.add_parser("fetch-operations", help="Cache DFLD half-hour history and conservative point-label proxies")
    history.add_argument("--data-dir", type=Path, default=Path("data"))
    export = commands.add_parser("export-submission", help="Replay explicit jury issue times into CSV and JSON")
    export.add_argument("--data-dir", type=Path, default=Path("data"))
    export.add_argument("--issues", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument("--labels", type=Path)
    compare = commands.add_parser("compare-models", help="Train fixed wind candidates and select on validation dates")
    compare.add_argument("--data-dir", type=Path, default=Path("data"))
    discovery = commands.add_parser("discover-data", help="Report source coverage and development-period error patterns")
    discovery.add_argument("--data-dir", type=Path, default=Path("data"))
    discovery.add_argument("--probe-gfs", action="store_true", help="Probe one recent and three archived GFS runs")
    comparison = commands.add_parser("refresh-comparison", help="Run frozen candidates on the saved forecast reference")
    comparison.add_argument("--data-dir", type=Path, default=Path("data"))
    comparison.add_argument("--no-gfs", action="store_true", help="Skip the optional unranked GFS source")
    agent = commands.add_parser("forecast-agent", help="Explain the saved policy with bounded optional AI tools")
    agent.add_argument("--data-dir", type=Path, default=Path("data"))
    agent.add_argument("--question", default="Where do forecasts disagree, and why was this forecast selected?")
    online = commands.add_parser("learn-online", help="Replay past forecasts hour by hour to warm and score the online learner")
    online.add_argument("--data-dir", type=Path, default=Path("data"))
    online.add_argument("--days", type=int, default=30, help="Days of archived ICON-D2 runs to replay")
    api = commands.add_parser("serve", help="Serve local forecast JSON endpoints")
    api.add_argument("--data-dir", type=Path, default=Path("data"))
    api.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command in ("fetch-operations", "train-operations", "export-submission", "compare-models", "discover-data", "refresh-comparison", "forecast-agent"):
        try:
            if args.command == "fetch-operations":
                from .operations_history import fetch
                report = fetch(args.data_dir)
                print(f"OD history: {report['days']} days, {report['training_points']} provisional point labels")
                return 0 if report["training_points"] else 1
            if args.command == "train-operations":
                from .operations_ml import train
                report = train(args.data_dir, args.labels)
                print(f"OD training: {report['status']}; {report.get('reason') or 'see operations-evaluation.json'}")
                return 0 if report["status"] == "trained" else 1
            if args.command == "export-submission":
                from .submission import export
                report = export(args.data_dir, args.issues, args.output_dir, args.labels)
                print(f"Exported {report['rows']} rows to {args.output_dir}: {report['status']}")
                return 0 if report["status"].startswith("complete") else 1
            if args.command == "forecast-agent":
                from .agent import run
                report = run(args.data_dir, args.question)
                print(f"Agent: {report['status']}. {report['explanation']}")
                return 0 if report["status"] == "completed" else 1
            from . import comparison
            if args.command == "compare-models":
                comparison.train(args.data_dir)
            elif args.command == "discover-data":
                report = comparison.discover(args.data_dir, args.probe_gfs)
                print(f"Discovery: {report['rows']} rows; saved {args.data_dir/'comparison'/'discovery.json'}")
            else:
                report = comparison.refresh(args.data_dir, include_gfs=not args.no_gfs)
                print(f"Comparison: {report['status']}; selected {report['policy']['winner']}")
                return 0 if report["status"] == "available" else 1
            return 0
        except ImportError as exc:
            print(f"Optional ML dependencies unavailable: {exc}. Install with: python -m pip install -e '.[ml]'", file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"{args.command} failed: {exc}", file=sys.stderr)
            return 1
    if args.command == "learn-online":
        from .online import train as train_online
        if not 3 <= args.days <= 60:
            parser.error("--days must be between 3 and 60")
        try:
            report = train_online(args.data_dir, args.days)
        except (OSError, ValueError, KeyError) as exc:
            print(f"Online learning replay failed: {exc}", file=sys.stderr)
            return 1
        print(f"Online learner warmed on {report['samples']} past forecasts; saved {args.data_dir / 'online' / 'backtest.json'}")
        return 0
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
