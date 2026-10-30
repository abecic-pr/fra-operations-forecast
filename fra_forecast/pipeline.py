"""One refresh creates a frontend snapshot and a reproducible training CSV."""

from datetime import datetime, timedelta
import json
from pathlib import Path

from .domain import UTC, DirectionState, RULESET, iso, parse_time, runway_conditions
from .dataset import build_dataset, dataset_report, load_labels
from .sources import (SourceClient, current_metar, current_operations, dwd_observations,
                      forecast, iem_observations, write_csv, write_json)


def next_change(points, field, initial):
    previous = None if initial in (None, "unknown") else initial
    previous_time = None
    gap = False
    for row in points:
        value = row.get(field)
        if value in (None, "unknown"):
            gap = True
            continue
        if previous is not None and value != previous:
            return {"status": "change_expected", "from": previous, "to": value,
                    "earliest": previous_time, "latest": row["valid_time"],
                    "probability": None, "method": "deterministic_rule_crossing",
                    "uncertain_due_to_gap": gap}
        previous, previous_time = value, row["valid_time"]
    return {"status": "unknown" if gap or not points or initial in (None, "unknown") else "no_change_within_horizon",
            "earliest": None, "latest": None, "probability": None}


def live_snapshot(now, models, metar, dwd, operations, checks):
    # Select whole-hour output points strictly after generation; use D2 where
    # available and explicit EU fallback for its shorter remaining horizon.
    first = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    targets = [first + timedelta(hours=i) for i in range(48)]
    hourly = {}
    for model in ("icon_eu", "icon_d2"):
        for row in models.get(model, {}).get("hourly", []):
            hourly[row["valid_time"]] = row
    fine = {row["valid_time"]: row for row in models.get("icon_d2", {}).get("minutely_15", [])}
    initial_direction = operations.get("operating_direction") if operations else None
    state = DirectionState(initial_direction)
    timeline = []
    # Include the current quarter-hour as the initial forecast state. It is a
    # forecast sample, not an assertion that measured conditions persisted earlier.
    at = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    while at <= targets[-1]:
        stamp = iso(at)
        weather = fine.get(stamp)
        if weather is None and at.minute == 0:
            weather = hourly.get(stamp)
        if weather is not None:
            result = state.step(weather, weather["resolution_minutes"])
            timeline.append({**weather, **result})
        at += timedelta(minutes=15)
    by_time = {r["valid_time"]: r for r in timeline}
    output = []
    for at in targets:
        row = by_time.get(iso(at))
        if row is None:
            row = {"valid_time": iso(at), "operating_direction": None, "rwy18_weather_state": "unknown",
                   "wind_speed_kt": None, "wind_from_deg_true": None, "wind_gust_kt": None,
                   "p_od07": None, "p_od25": None, "p_rwy18_weather_usable": None,
                   "reason_codes": ["forecast_unavailable"], "model": None}
        output.append({**row, "lead_time_hours": round((at-now).total_seconds()/3600, 3)})
    recent_dwd = max(dwd, key=lambda r: r["valid_time"]) if dwd else None
    observations = [r for r in (metar, recent_dwd) if r and parse_time(r["valid_time"]) <= now]
    current = max(observations, key=lambda r: r["valid_time"]) if observations else None
    # Never fill a METAR gust using a different station/interval silently.
    current_conditions = runway_conditions(current) if current else None
    age = (now-parse_time(current["valid_time"])).total_seconds() if current else None
    future_timeline = [r for r in timeline if parse_time(r["valid_time"]) > now]
    current18 = current_conditions["18"]["weather_state"] if current_conditions else "unknown"
    return {
        "schema_version": "1.0", "airport_icao": "EDDF", "display_timezone": "Europe/Berlin",
        "generated_at": iso(now), "method": "challenge_rules_baseline", "ruleset": RULESET,
        "probability_status": "unavailable_until_model_is_trained",
        "observed_operations": operations or {"operating_direction": None, "rwy18_operational_status": "unknown"},
        "current_weather": current, "metar": metar, "dwd_observation": recent_dwd,
        "current_runway_wind": current_conditions,
        "data_quality": {"weather_age_seconds": age,
                         "weather_status": "unknown" if age is None else "stale" if age > 5400 else "recent",
                         "forecast_hours_available": sum(r.get("model") is not None for r in output),
                         "initial_direction_source": "observed_operations" if initial_direction else "wind_inference",
                         "source_errors": [r for r in checks if r.get("status") == "error"]},
        "forecast": output,
        "next_operating_direction_change": next_change(future_timeline, "operating_direction", initial_direction),
        "next_rwy18_weather_change": next_change(future_timeline, "rwy18_weather_state", current18),
        "limitations": ["Deterministic baseline; probabilities are intentionally null.",
                        "RWY18 weather suitability does not establish official runway availability.",
                        "Gust crosswind uses mean wind direction when gust direction is unavailable.",
                        "After D2 coverage ends, hourly ICON-EU cannot resolve a 30-minute change precisely."]}


def refresh(root, history_days=14, archive_days=7, labels_path=None, live_only=False, progress=print, use_ml=True, include_departures=True):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    client = SourceClient(root)
    now = datetime.now(UTC)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = midnight - timedelta(days=history_days)
    errors = []

    def attempt(name, action, default):
        progress(f"Fetching {name}…", flush=True)
        try:
            return action()
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"source": name, "status": "error", "error": str(exc)})
            progress(f"  {name} unavailable: {exc}", flush=True)
            return default

    labels = load_labels(labels_path)
    dwd = attempt("DWD observations", lambda: dwd_observations(client, start, now + timedelta(minutes=1)), [])
    metar = attempt("EDDF METAR", lambda: current_metar(client), None)
    taf = attempt("EDDF TAF", lambda: client.json("awc_taf", "https://aviationweather.gov/api/data/taf?ids=EDDF&format=json")[0], [])
    operations = attempt("current operating direction", lambda: current_operations(client), None)
    models = {model: attempt(model, lambda model=model: forecast(client, model), {}) for model in ("icon_d2", "icon_eu")}
    snapshot = live_snapshot(datetime.now(UTC), models, metar, dwd, operations, client.checks + errors)
    snapshot["taf"] = taf
    from .ml_live import enrich
    enrich(snapshot,root,client,enabled=use_ml)
    from .operations_ml import enrich as enrich_operations
    enrich_operations(snapshot, root, enabled=use_ml, observations=dwd)
    from .direction import enrich as enrich_direction
    enrich_direction(snapshot)
    snapshot["runway18_departures_url"] = "/api/runway18/departures"
    write_json(root / "forecast.json", snapshot)
    from .verification import remember_forecast
    remember_forecast(root, snapshot)
    if operations:
        with (root / "operations-snapshots.jsonl").open("a") as f:
            f.write(json.dumps(operations) + "\n")
    write_csv(root / "observations.csv", dwd)
    if not live_only:
        iem = attempt("historical METAR", lambda: iem_observations(client, start, midnight), [])
        write_csv(root / "metar-history.csv", iem)
        runs = []
        for offset in range(archive_days, 0, -1):
            run_at = midnight - timedelta(days=offset)
            result = attempt(f"ICON-D2 archive {iso(run_at)}", lambda run_at=run_at: forecast(client, "icon_d2", run_at), {})
            if result.get("hourly"):
                runs.append({"run_at": iso(run_at), **result})
        write_json(root / "archived-forecasts.json", runs)
        rows = build_dataset(runs, dwd, labels)
        write_csv(root / "training-dataset.csv", rows)
        report = dataset_report(rows, dwd, labels)
        write_json(root / "dataset-report.json", report)
    if include_departures:
        from .departures import refresh_departures
        attempt("RWY18 departure assessments",lambda:refresh_departures(root,forecast_snapshot=snapshot,progress=progress),None)
    if include_departures:
        from .traffic import refresh_traffic
        attempt("airport arrivals and departures", lambda: refresh_traffic(root, now=now, client=client), None)
    write_json(root / "sources.json", {"checked_at": iso(datetime.now(UTC)), "sources": client.checks, "errors": errors})
    progress(f"Saved {root / 'forecast.json'} ({snapshot['data_quality']['forecast_hours_available']}/48 forecast hours).", flush=True)
    return snapshot
