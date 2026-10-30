"""Recover DFLD's displayed actual-OD history, retaining its coarse resolution."""

from collections import Counter
from datetime import datetime, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .domain import UTC, iso, parse_time
from .sources import SourceClient, write_csv, write_json

HELP_URL = "https://www.dfld.de/Mess/Language/MessHelpG.html"
BERLIN = ZoneInfo("Europe/Berlin")


class DirectionPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bars, self.current, self.date = [], None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "D":
            self.date = attrs.get("value")
        if tag == "div" and attrs.get("class") == "LaermGraphLegende--24h":
            self.current = []
            self.bars.append(self.current)
        if tag == "img" and self.current is not None and attrs.get("class") == "LaermGraphLegendeBild--24h":
            self.current.append(attrs.get("title", ""))

    def handle_endtag(self, tag):
        if tag == "div":
            self.current = None


def parse_day(body, day, meta):
    page = DirectionPage()
    page.feed(body.decode("utf-8", errors="replace"))
    if page.date != day.strftime("%d.%m.%Y") or len(page.bars) != 2 or any(len(b) != 48 for b in page.bars):
        raise ValueError("Expected requested date and two complete 48-slot wind/actual-direction bars")
    start = datetime.combine(day, datetime.min.time(), BERLIN)
    if start.utcoffset() != (start+timedelta(days=1)).utcoffset():
        raise ValueError("DST transition day excluded: 48 display slots cannot resolve repeated/missing local times")
    directions = {"Betriebsrichtung West (25)": "25", "Betriebsrichtung Ost (07)": "07"}
    return [{"display_from": iso(start+timedelta(minutes=30*i)),
             "display_to": iso(start+timedelta(minutes=30*(i+1))),
             "display_local_date": day.isoformat(), "display_slot": i,
             "operating_direction": directions.get(title, "unknown"), "source_title": title,
             "wind_title": page.bars[0][i], "source": meta["url"], "fetched_at": meta["fetched_at"],
             "source_sha256": meta["sha256"], "resolution_minutes": 30,
             "semantics": "displayed_half_hour_category; exact sampling and switch times unverified"}
            for i, title in enumerate(page.bars[1])]


def training_points(records):
    by_time = {r["display_from"]: r for r in records}
    result = []
    for stamp, row in sorted(by_time.items()):
        at = parse_time(stamp)
        if at.minute:
            continue
        neighbors = [by_time.get(iso(at+timedelta(minutes=offset))) for offset in (-30, 0, 30)]
        direction = row["operating_direction"]
        if direction not in ("07", "25") or any(r is None or r["operating_direction"] != direction for r in neighbors):
            continue
        # shortcut: stable display bins are coarse point-label proxies, never exact switch intervals.
        result.append({"valid_from": stamp, "valid_to": stamp, "label_kind": "point",
                       "available_at": max(r["fetched_at"] for r in neighbors),
                       "operating_direction": direction, "rwy18_weather_usable": "",
                       "rwy18_operational_status": "", "source": row["source"],
                       "label_quality": "provisional_stable_display_proxy",
                       "resolution_minutes": 30, "historical_availability_verified": "false"})
    return result


def fetch(data_dir="data", client=None, progress=print):
    root = Path(data_dir)
    dataset = json.loads((root/"ml"/"dataset.json").read_text())["rows"]
    first = parse_time(min(r["valid_time"] for r in dataset)).astimezone(BERLIN).date()
    last = parse_time(max(r["valid_time"] for r in dataset)).astimezone(BERLIN).date()
    client = client or SourceClient(root/"od-research", timeout=20, attempts=1)
    records, failures = [], []
    for offset in range((last-first).days+1):
        day = first+timedelta(days=offset)
        url = "https://www.dfld.de/Mess/Messwerte.php?"+urlencode(dict(
            Do="D", L="G", R=1, S=137, K=0, D=day.strftime("%d.%m.%Y"), ST=0,
            Z="00:00:00", ZT="", A=1, Ps="", MNr=0, NoOpt=0))
        try:
            body, meta = client.get("dfld_history", url, immutable=True)
            records.extend(parse_day(body, day, meta))
        except (OSError, ValueError) as exc:
            failures.append({"date": day.isoformat(), "reason": str(exc), "url": url})
        if offset % 20 == 0:
            progress(f"OD history: {offset+1}/{(last-first).days+1} days; {len(records)} display slots", flush=True)
        if not client.checks[-1].get("cached"):
            time.sleep(0.5)
    if not records:
        raise ValueError("No historical direction pages passed validation; previous output preserved")
    points = training_points(records)
    report = {"generated_at": iso(datetime.now(UTC)), "status": "provisional_source_history",
              "first_local_date": first.isoformat(), "last_local_date": last.isoformat(),
              "days": len({r["display_local_date"] for r in records}), "display_slots": len(records),
              "display_counts": dict(Counter(r["operating_direction"] for r in records)),
              "training_points": len(points), "point_class_counts": dict(Counter(r["operating_direction"] for r in points)),
              "failed_or_excluded_days": failures, "source_checks": client.checks, "source_documentation": HELP_URL,
              "label_semantics": "Hourly point proxies only when previous/current/next displayed half-hours agree; no interval interpolation.",
              "timezone": "Europe/Berlin; independently checked against METAR before and after DST",
              "limitations": ["DFLD documents actual direction based on Fraport, but exact category sampling time is unverified.",
                              "Stable-bin selection excludes transitions; scores are conditional on this easier subset.",
                              "No exact change-time truth or historical as-of initial direction is inferred.",
                              "Historical publication unknown: retrieval time is used as availability; targets only.",
                              "Local research extract; redistribution rights have not been established."]}
    write_csv(root/"operations"/"dfld-half-hour.csv", records)
    fields = ["valid_from", "valid_to", "label_kind", "available_at", "operating_direction",
              "rwy18_weather_usable", "rwy18_operational_status", "source", "label_quality",
              "resolution_minutes", "historical_availability_verified"]
    write_csv(root/"operations"/"labels.csv", points, fields)
    write_json(root/"operations"/"history-report.json", report)
    return report
