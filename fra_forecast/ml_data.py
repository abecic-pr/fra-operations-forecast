"""Cached ICON-EU backfill and exact, observation-only regression targets."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import json
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlsplit

from .domain import UTC, iso, number, parse_time
from .sources import SourceClient, dwd_observations, forecast, write_csv, write_json

DATA_VERSION = "wind-training-v1"
AVAILABILITY_DELAY_HOURS = 4


def uv(speed, direction):
    import math
    speed, direction = number(speed), number(direction)
    if speed is None or speed < 0:
        return None
    if speed == 0:
        return (0.0, 0.0)
    if direction is None or not 0 <= direction <= 360:
        return None
    angle = math.radians(direction)
    return (-speed * math.sin(angle), -speed * math.cos(angle))


def good_quality(row, field):
    quality = number(row.get(field, row.get("quality_code")))
    return quality is not None and quality >= 2


def observation_target(index, at):
    """No nearest/future joins. Gust covers (at-60min, at] exactly."""
    row = index.get(iso(at))
    if row is None or not good_quality(row, "wind_quality_code"):
        return None
    components = uv(row.get("wind_speed_kt"), row.get("wind_from_deg_true"))
    if components is None:
        return None
    interval = [index.get(iso(at - timedelta(minutes=10*i))) for i in range(6)]
    complete = all(r and good_quality(r, "gust_quality_code") and
                   number(r.get("wind_gust_kt")) is not None and number(r.get("wind_gust_kt")) >= 0
                   for r in interval)
    peak = max(interval, key=lambda r: r["wind_gust_kt"]) if complete else None
    return {"target_u_kt": components[0], "target_v_kt": components[1],
            "target_wind_speed_kt": row["wind_speed_kt"],
            "target_wind_from_deg_true": row.get("wind_from_deg_true"),
            "target_gust_kt": peak["wind_gust_kt"] if peak else None,
            "target_gust_from_deg_true": peak.get("gust_from_deg_true") if peak else None,
            "target_gust_samples": 6 if complete else sum(bool(r and number(r.get("wind_gust_kt")) is not None) for r in interval),
            "target_wind_quality_code": row.get("wind_quality_code", row.get("quality_code")),
            "target_source": "dwd_cdc:01420"}


def build_rows(runs, observations):
    index = {r["valid_time"]: r for r in observations}
    rows = []
    for run in runs:
        run_at = parse_time(run["run_at"])
        decision = run_at + timedelta(hours=AVAILABILITY_DELAY_HOURS)
        past_at = decision - timedelta(hours=1)
        past = observation_target(index, past_at)
        for weather in run["hourly"]:
            at = parse_time(weather["valid_time"])
            model_lead = (at-run_at).total_seconds()/3600
            if not 5 <= model_lead <= 72 or model_lead % 1:
                continue
            raw = uv(weather.get("wind_speed_kt"), weather.get("wind_from_deg_true"))
            target = observation_target(index, at)
            if raw is None or target is None:
                continue
            rows.append({"decision_time": iso(decision), "valid_time": iso(at),
                         "model_run_at": iso(run_at), "model_lead_hours": int(model_lead),
                         "lead_time_hours": int(model_lead-AVAILABILITY_DELAY_HOURS),
                         "forecast_available_at": iso(decision), "availability_verified": False,
                         "availability_basis": "estimated_four_hour_model_delay",
                         "forecast_fetched_at": weather["fetched_at"], "model": "icon_eu",
                         "raw_u_kt": raw[0], "raw_v_kt": raw[1],
                         "raw_wind_speed_kt": weather["wind_speed_kt"],
                         "raw_wind_from_deg_true": weather.get("wind_from_deg_true"),
                         "raw_gust_kt": weather.get("wind_gust_kt"),
                         "persistence_observation_time": iso(past_at) if past else None,
                         "persistence_u_kt": past["target_u_kt"] if past else None,
                         "persistence_v_kt": past["target_v_kt"] if past else None,
                         "persistence_gust_kt": past["target_gust_kt"] if past else None,
                         **target})
    rows.sort(key=lambda r: (r["decision_time"], r["valid_time"]))
    return rows


def archive_provenance(root, run_times):
    """Recover original response provenance even when parsed runs were cached."""
    result = {}
    for path in (Path(root)/"raw"/"forecast_icon_eu").glob("*.json"):
        metadata = json.loads(path.read_text())
        url = metadata.get("url","")
        if "single-runs-api.open-meteo.com" not in url:
            continue
        stamp = parse_qs(urlsplit(url).query).get("run",[None])[0]
        if stamp and iso(parse_time(stamp+"Z")) in run_times:
            result[url] = {**metadata,"raw_metadata_file":str(path.relative_to(root))}
    return list(result.values())


def prepare(data_dir="data", days=180, max_minutes=50, progress=print):
    if not 30 <= days <= 180:
        raise ValueError("ML archive days must be between 30 and 180")
    root = Path(data_dir)
    output = root / "ml"
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    # All 72-hour outcomes must already exist; do not include unfinished runs.
    last_day = midnight - timedelta(days=4)
    first_day = last_day - timedelta(days=days-1)
    client = SourceClient(root)
    progress(f"Fetching DWD 01420 observations from {iso(first_day)}…", flush=True)
    observations = dwd_observations(client, first_day-timedelta(hours=1), midnight, include_now=False)
    write_csv(output / "observations.csv", observations)
    requests = [first_day+timedelta(days=d, hours=h) for d in range(days) for h in (0,6,12,18)]
    folder = output / "runs"
    folder.mkdir(exist_ok=True)
    rate_lock = threading.Lock()
    next_request = [time.monotonic()]

    def fetch_run(at):
        path = folder / (at.strftime("%Y%m%dT%H%M") + ".json")
        if path.exists():
            return json.loads(path.read_text()), []
        with rate_lock:
            delay = max(0, next_request[0] - time.monotonic())
            if delay:
                time.sleep(delay)
            next_request[0] = time.monotonic()+1.0
        reader = SourceClient(root, timeout=20)
        data = forecast(reader, "icon_eu", at, forecast_days=4)
        result = {"run_at": iso(at), **data}
        write_json(path, result)
        return result, reader.checks

    errors, checks, runs = [], list(client.checks), []
    # A bounded worker queue avoids submitting hundreds of requests after timeout.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for offset in range(0, len(requests), 4):
            if time.monotonic()-started > max_minutes*60:
                progress("Backfill timebox reached; restricting this dataset to the latest 90 issue days.", flush=True)
                break
            # Recent first makes the planned 90-day fallback usable.
            batch = list(reversed(requests))[offset:offset+4]
            futures = {pool.submit(fetch_run, at): at for at in batch}
            for future in as_completed(futures):
                at = futures[future]
                try:
                    result, source_checks = future.result()
                    runs.append(result)
                    checks.extend(source_checks)
                except (OSError, ValueError, KeyError) as exc:
                    errors.append({"run_at": iso(at), "error": str(exc)})
            if offset % 40 == 0 or offset+4 == len(requests):
                progress(f"Archive: {min(offset+4,len(requests))}/{len(requests)} requests, {len(runs)} retrieved runs, {len(errors)} errors.", flush=True)
    effective_days = days
    if len(runs)+len(errors) < len(requests):
        effective_days = min(days,90)
        cutoff = last_day-timedelta(days=effective_days-1)
        runs = [r for r in runs if parse_time(r["run_at"]) >= cutoff]
    rows = build_rows(runs, observations)
    report = {"data_version": DATA_VERSION, "prepared_at": iso(datetime.now(UTC)),
              "requested_days": days, "effective_days": effective_days,
              "requested_runs": len(requests), "successful_runs": len(runs), "source_errors": errors,
              "runs_with_training_rows":len({r["model_run_at"] for r in rows}),
              "empty_forecast_runs":[r["run_at"] for r in runs if not r.get("hourly")],
              "distinct_issue_dates":len({r["decision_time"][:10] for r in rows}),
              "rows": len(rows), "observation_rows": len(observations),
              "first_decision_time": rows[0]["decision_time"] if rows else None,
              "last_decision_time": rows[-1]["decision_time"] if rows else None,
              "missing_gust_targets": sum(r["target_gust_kt"] is None for r in rows),
              "availability_verified": False,
              "limitations": ["Historical availability assumes model initialization plus four hours.",
                              "Retrospective DWD observations may include later quality corrections.",
                              "DWD gusts are preceding-hour maxima requiring all six ten-minute records.",
                              "Missing archive requests and measurements are not synthesized."]}
    write_json(output / "dataset.json", {"data_version": DATA_VERSION, "rows": rows})
    write_json(output / "preparation-report.json", report)
    all_checks = {check["url"]:check for check in checks if "url" in check}
    for check in archive_provenance(root,{r["run_at"] for r in runs}):
        all_checks[check["url"]] = check
    write_json(output / "sources.json", list(all_checks.values()))
    progress(f"Prepared {len(rows)} wind training rows in {output}.", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()
    prepare(args.data_dir,args.days)
