"""Small, cached readers for the public sources verified in docs/izvori-podataka.md."""

import csv
import hashlib
import html
import io
import json
from pathlib import Path
import re
import time
import urllib.request
from urllib.parse import urlencode
import zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .domain import UTC, iso, number, parse_time

DWD_ROOT = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes"
UNH_URL = "https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/"
WIND_FIELDS = "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
LAT, LON = 50.0259, 8.5213  # DWD station, for forecast/observation alignment.


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temp.replace(path)


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", newline="") as f:
        fields = fieldnames or list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


class SourceClient:
    def __init__(self, root, timeout=30):
        self.root = Path(root)
        self.timeout = timeout
        self.checks = []

    def get(self, source, url, immutable=False):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        folder = self.root / "raw" / source
        folder.mkdir(parents=True, exist_ok=True)
        body_path = folder / f"{key}.bin"
        meta_path = folder / f"{key}.json"
        if immutable and body_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self.checks.append({**meta, "cached": True})
            return body_path.read_bytes(), meta
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "FRA-Hackathon/0.1 (public data research)"})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    body = response.read(12_000_000)
                    if len(body) == 12_000_000:
                        raise ValueError("Source response exceeded the 12 MB limit")
                    status = response.status
                fetched = iso(datetime.now(UTC))
                meta = {"source": source, "url": url, "fetched_at": fetched,
                        "http_status": status, "sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body), "status": "ok"}
                if not immutable:
                    # Preserve successive live forecasts for later replay.
                    snapshot_key = f"{key}-{time.time_ns()}"
                    body_path = folder / f"{snapshot_key}.bin"
                    meta_path = folder / f"{snapshot_key}.json"
                body_path.write_bytes(body)
                write_json(meta_path, meta)
                self.checks.append(meta)
                return body, meta
            except (OSError, ValueError) as exc:
                if attempt == 2:
                    self.checks.append({"source": source, "url": url, "status": "error", "error": str(exc)})
                    raise
                time.sleep(0.5 * (attempt + 1))

    def json(self, source, url, immutable=False):
        body, meta = self.get(source, url, immutable)
        return json.loads(body), meta


def parse_dwd_zip(body, start, end):
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        filename = next(name for name in archive.namelist() if name.startswith("produkt_"))
        reader = csv.DictReader(io.StringIO(archive.read(filename).decode("utf-8-sig")), delimiter=";")
        rows = []
        for raw in reader:
            row = {k.strip(): v.strip() for k, v in raw.items() if k and v is not None}
            at = datetime.strptime(row["MESS_DATUM"], "%Y%m%d%H%M").replace(tzinfo=UTC)
            if not start <= at < end:
                continue
            result = {"valid_time": iso(at), "station_id": "01420", "source": "dwd_cdc",
                      "quality_code": row.get("QN"), "interval_minutes": 10,
                      "available_at": iso(at + timedelta(hours=1)),
                      "availability_basis": "estimated_one_hour_delay_retrospective_data"}
            for old, new, factor in [("FF_10", "wind_speed_kt", 1.943844),
                                     ("DD_10", "wind_from_deg_true", 1),
                                     ("FX_10", "wind_gust_kt", 1.943844),
                                     ("DX_10", "gust_from_deg_true", 1)]:
                if old in row:
                    value = number(row[old])
                    result[new] = value * factor if value is not None and value >= 0 else None
            rows.append(result)
    return rows


def dwd_observations(client, start, end, include_now=True):
    records = {}
    for group, prefix in [("wind", "wind"), ("extreme_wind", "extrema_wind")]:
        for kind, suffix in ([("recent", "akt"), ("now", "now")] if include_now else [("recent", "akt")]):
            url = f"{DWD_ROOT}/{group}/{kind}/10minutenwerte_{prefix}_01420_{suffix}.zip"
            try:
                body, meta = client.get(f"dwd_{group}_{kind}", url)
                for row in parse_dwd_zip(body, start, end):
                    records.setdefault(row["valid_time"], {}).update(row)
                    records[row["valid_time"]]["fetched_at"] = meta["fetched_at"]
            except (OSError, ValueError, zipfile.BadZipFile):
                if kind == "recent":
                    raise
    return [records[k] for k in sorted(records)]


def iem_observations(client, start, end):
    params = [("station", "EDDF"), ("data", "drct"), ("data", "sknt"),
              ("data", "gust"), ("data", "metar"), ("year1", start.year),
              ("month1", start.month), ("day1", start.day), ("year2", end.year),
              ("month2", end.month), ("day2", end.day), ("tz", "Etc/UTC"),
              ("format", "onlycomma"), ("latlon", "no"), ("elev", "no"),
              ("missing", "M"), ("trace", "T"), ("direct", "no"),
              ("report_type", "3"), ("report_type", "4")]
    body, meta = client.get("iem_metar", "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + urlencode(params), immutable=True)
    results = []
    for row in csv.DictReader(io.StringIO(body.decode())):
        at = datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        if start <= at < end:
            results.append({"valid_time": iso(at), "source": "iem_metar", "station_id": "EDDF",
                            "wind_speed_kt": number(row["sknt"]), "wind_from_deg_true": number(row["drct"]),
                            "wind_gust_kt": number(row["gust"]), "raw_metar": row["metar"],
                            "fetched_at": meta["fetched_at"], "availability_basis": "historical_receipt_time_unknown"})
    return results


def current_metar(client):
    data, meta = client.json("awc_metar", "https://aviationweather.gov/api/data/metar?ids=EDDF&format=json&hours=3")
    if not data:
        raise ValueError("No EDDF METAR returned")
    raw = max(data, key=lambda row: row["obsTime"])
    sector = re.search(r"\b(\d{3})V(\d{3})\b", raw.get("rawOb", ""))
    return {"valid_time": iso(datetime.fromtimestamp(raw["obsTime"], UTC)),
            "source": "awc_metar", "station_id": "EDDF", "fetched_at": meta["fetched_at"],
            "available_at": raw.get("receiptTime"), "availability_basis": "awc_receipt_time",
            "wind_speed_kt": number(raw.get("wspd")), "wind_from_deg_true": number(raw.get("wdir")),
            "wind_gust_kt": number(raw.get("wgst")), "gust_from_deg_true": None,
            "wind_variable": raw.get("wdir") == "VRB", "wind_sector_from_deg": int(sector[1]) if sector else None,
            "wind_sector_to_deg": int(sector[2]) if sector else None,
            "temperature_c": raw.get("temp"), "dew_point_c": raw.get("dewp"),
            "qnh_hpa": raw.get("altim"), "visibility_raw": raw.get("visib"),
            "cloud_layers": raw.get("clouds", []), "raw_metar": raw.get("rawOb")}


def parse_forecast(data, model, meta, run_at=None):
    result = {"hourly": [], "minutely_15": []}
    for block, resolution in [("hourly", 60), ("minutely_15", 15)]:
        series = data.get(block, {})
        units = data.get(f"{block}_units", {})
        for i, stamp in enumerate(series.get("time", [])):
            row = {"valid_time": iso(parse_time(stamp + ("Z" if "+" not in stamp and not stamp.endswith("Z") else ""))),
                   "source": "open_meteo", "model": model, "resolution_minutes": resolution,
                   "model_run_at": iso(run_at) if run_at else None,
                   "fetched_at": meta["fetched_at"],
                   "available_at": iso(run_at + timedelta(hours=4)) if run_at else meta["fetched_at"],
                   "availability_basis": "estimated_four_hour_model_delay" if run_at else "retrieved_live",
                   "latitude": data.get("latitude"), "longitude": data.get("longitude")}
            for old, new in [("wind_speed_10m", "wind_speed_kt"), ("wind_direction_10m", "wind_from_deg_true"),
                             ("wind_gusts_10m", "wind_gust_kt")]:
                values = series.get(old, [])
                value = number(values[i]) if i < len(values) else None
                if old != "wind_direction_10m" and value is not None and units.get(old) not in ("kn", "kt"):
                    raise ValueError(f"Unexpected wind units: {units}")
                row[new] = value
            if row["wind_speed_kt"] is not None:
                result[block].append(row)
    return result


def forecast(client, model, run_at=None):
    params = {"latitude": LAT, "longitude": LON, "hourly": WIND_FIELDS,
              "models": model, "wind_speed_unit": "kn", "timezone": "UTC"}
    if run_at:
        params.update(run=run_at.strftime("%Y-%m-%dT%H:%M"), forecast_days=3)
        base = "https://single-runs-api.open-meteo.com/v1/forecast"
    else:
        params["forecast_hours"] = 52
        if model == "icon_d2":
            params.update(minutely_15=WIND_FIELDS, forecast_minutely_15=196)
        base = "https://api.open-meteo.com/v1/forecast"
    data, meta = client.json(f"forecast_{model}", base + "?" + urlencode(params), immutable=bool(run_at))
    return parse_forecast(data, model, meta, run_at)


def parse_unh(body, fetched_at):
    text = html.unescape(re.sub(r"<[^>]*>", " ", body.decode("utf-8")))
    text = re.sub(r"\s+", " ", text)
    # Scope to the actual-state section, never the forecast paragraph.
    match = re.search(r"BR\s*(07|25)\s+(?:Ost|West)\s+Betriebsrichtung\s+seit\s+(\d{1,2})\.\s*([A-Za-zäÄ]+)\.?\s*,?\s*(\d{1,2})[.:](\d{2})\s*Uhr", text)
    if not match:
        raise ValueError("UNH actual-state markup not recognized; do not infer state from forecast text")
    months = {"jan": 1, "feb": 2, "mar": 3, "mär": 3, "apr": 4, "may": 5, "mai": 5,
              "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "dez": 12}
    fetched = parse_time(fetched_at)
    since = datetime(fetched.year, months[match[3][:3].lower()], int(match[2]), int(match[4]), int(match[5]), tzinfo=ZoneInfo("Europe/Berlin"))
    if since > fetched + timedelta(days=1):
        since = since.replace(year=since.year - 1)
    return {"operating_direction": match[1], "since": iso(since), "observed_at": fetched_at,
            "available_at": fetched_at, "source": "UNH (reports DFS)", "url": UNH_URL,
            "method": "public_page_snapshot", "historical_label": False,
            "rwy18_operational_status": "unknown"}


def current_operations(client):
    body, meta = client.get("unh_current_operations", UNH_URL)
    return parse_unh(body, meta["fetched_at"])
