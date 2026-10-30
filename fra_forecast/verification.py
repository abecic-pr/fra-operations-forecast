"""Source-screened measurements and immutable issued forecasts for UI comparison.

Recent DWD measurements remain provisional. This does not train a model or certify
final quality; it checks provenance, hash, station, timestamp, units and QN>=2.
"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import threading
from functools import lru_cache
import zipfile

from .domain import UTC, iso, number, parse_time, wind_components
from .sources import parse_dwd_zip

_archive_lock = threading.Lock()
DWD_WIND_ROOT = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/"


@lru_cache(maxsize=16)
def _parsed_wind(body, day):
    midnight = parse_time(day + "T00:00:00Z")
    return parse_dwd_zip(body, midnight - timedelta(days=1), midnight + timedelta(days=2))


def remember_forecast(root, snapshot, now=None):
    """Archive only future predictions, using actual archive time as issue time."""
    root = Path(root)
    now = now or datetime.now(UTC)
    generated = parse_time(snapshot["generated_at"])
    if generated > now or snapshot.get("schema_version") not in ("1.0", "1.1"):
        return
    points = []
    for row in snapshot.get("forecast", []):
        at = parse_time(row["valid_time"])
        tail = number((row.get("runway_wind") or {}).get("18", {}).get("tailwind_kt"))
        if at > now and tail is not None and tail >= 0:
            points.append({"valid_time": iso(at), "tailwind_kt": tail,
                           "model": row.get("model"), "source": row.get("source")})
    if not points:
        return
    path = root / "issued-forecasts.jsonl"
    with _archive_lock:
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    if json.loads(line).get("generated_at") == snapshot["generated_at"]:
                        return
                except ValueError:
                    continue
        root.mkdir(parents=True, exist_ok=True)
        with path.open("a") as stream:
            stream.write(json.dumps({"generated_at": snapshot["generated_at"], "issued_at": iso(now),
                                     "method": snapshot.get("method"), "forecast": points}) + "\n")


def comparison_payload(root, now=None):
    root = Path(root)
    now = now or datetime.now(UTC)
    start = now - timedelta(hours=6)
    # Pair complete wind/gust observations only at the same station and interval.
    # Read and hash-screen each original source independently; do not trust merged QN.
    gusts = {}
    gust_root = DWD_WIND_ROOT.replace("/wind/", "/extreme_wind/")
    for folder in ("dwd_extreme_wind_recent", "dwd_extreme_wind_now"):
        for meta_path in sorted((root / "raw" / folder).glob("*.json")):
            try:
                meta = json.loads(meta_path.read_text())
                received = parse_time(meta["fetched_at"])
                url = meta.get("url", "")
                if meta.get("status") != "ok" or meta.get("http_status") != 200 or received > now or not url.startswith(gust_root) or "_01420_" not in url:
                    continue
                body = meta_path.with_suffix(".bin").read_bytes()
                if hashlib.sha256(body).hexdigest() != meta.get("sha256"):
                    continue
                for row in _parsed_wind(body, now.date().isoformat()):
                    at = parse_time(row["valid_time"])
                    speed, direction = number(row.get("wind_gust_kt")), number(row.get("gust_from_deg_true"))
                    quality = str(row.get("gust_quality_code", ""))
                    if not start <= at <= min(now, received) or quality not in {"2", "3"} or speed is None or not 0 <= speed <= 200 or direction is None or not 0 <= direction <= 360:
                        continue
                    value = {"wind_gust_kt": speed, "gust_from_deg_true": direction,
                             "gust_quality_code": quality, "gust_source_url": url,
                             "gust_received_at": meta["fetched_at"], "gust_source_sha256": meta["sha256"]}
                    previous = gusts.get(row["valid_time"])
                    if previous is None or (quality, value["gust_received_at"]) > (previous["gust_quality_code"], previous["gust_received_at"]):
                        gusts[row["valid_time"]] = value
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                continue
    observations = {}
    excluded = 0
    # Read mean-wind source files directly: merged CSV QN can refer to the gust
    # source instead of the mean-wind source, so it is not used for verification.
    for folder in ("dwd_wind_recent", "dwd_wind_now"):
        for meta_path in sorted((root / "raw" / folder).glob("*.json")):
            try:
                meta = json.loads(meta_path.read_text())
                url = meta.get("url", "")
                received = parse_time(meta["fetched_at"])
                if meta.get("status") != "ok" or meta.get("http_status") != 200 or received > now or not url.startswith(DWD_WIND_ROOT) or "_01420_" not in url:
                    continue
                body = meta_path.with_suffix(".bin").read_bytes()
                if hashlib.sha256(body).hexdigest() != meta.get("sha256"):
                    continue
                for row in _parsed_wind(body, now.date().isoformat()):
                    at = parse_time(row["valid_time"])
                    if not start <= at <= now:
                        continue
                    speed, direction = number(row.get("wind_speed_kt")), number(row.get("wind_from_deg_true"))
                    quality = str(row.get("quality_code", ""))
                    if at > received or quality not in {"2", "3"} or speed is None or speed < 0 or speed > 200 or (speed > 0 and (direction is None or not 0 <= direction <= 360)):
                        excluded += 1
                        continue
                    components = wind_components(speed, direction, 180)
                    if components is None:
                        continue
                    result = {"valid_time": row["valid_time"], "tailwind_kt": components["tailwind_kt"],
                              "wind_speed_kt": speed, "wind_from_deg_true": direction,
                              "station_id": "01420", "source": "DWD CDC", "source_url": url,
                              "received_at": meta["fetched_at"], "quality_code": quality,
                              "eligible": True, "provisional": True,
                              "verification": "source_hash_station_time_and_QN_screened",
                              "source_sha256": meta["sha256"], **gusts.get(row["valid_time"], {})}
                    previous = observations.get(row["valid_time"])
                    if previous is None or (quality, result["received_at"]) > (previous["quality_code"], previous["received_at"]):
                        observations[row["valid_time"]] = result
            except (OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile):
                continue
    forecasts = []
    path = root / "issued-forecasts.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                run = json.loads(line)
                issued = parse_time(run["issued_at"])
                if issued > now:
                    continue
                for point in run.get("forecast", []):
                    at = parse_time(point["valid_time"])
                    value = number(point.get("tailwind_kt"))
                    if start <= at <= now and issued < at and value is not None and value >= 0:
                        forecasts.append({**point, "issued_at": run["issued_at"], "generated_at": run["generated_at"]})
            except (ValueError, KeyError):
                continue
    complete = [r for r in observations.values() if r.get("wind_gust_kt") is not None and now-parse_time(r["valid_time"]) <= timedelta(minutes=90)]
    return {"schema_version": "1.0", "checked_at": iso(now),
            "latest_complete_observation": max(complete, key=lambda r: r["valid_time"]) if complete else None,
            "observations": sorted(observations.values(), key=lambda row: row["valid_time"]),
            "issued_forecasts": forecasts, "excluded_measurements": excluded,
            "policy": "Official DWD mean wind, source hash and time checked, QN 2 or 3; provisional, not final QC.",
            "comparison": "Exact valid-time matches only; forecasts must have been archived before the observation time."}
