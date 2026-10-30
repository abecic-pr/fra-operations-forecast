"""Join archived forecasts to observations and independent operations labels."""

import csv
from datetime import timedelta
from bisect import bisect_right

from .domain import DirectionState, iso, number, parse_time

LABEL_COLUMNS = ["valid_from", "valid_to", "available_at", "operating_direction",
                 "rwy18_weather_usable", "rwy18_operational_status", "source"]


def load_labels(path):
    if path is None:
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not set(LABEL_COLUMNS) <= set(reader.fieldnames or []):
            raise ValueError(f"Operations CSV needs columns: {', '.join(LABEL_COLUMNS)}")
        rows = []
        for line, row in enumerate(reader, 2):
            if not any(row.values()):
                continue
            start, end, available = (parse_time(row[k]) for k in ("valid_from", "valid_to", "available_at"))
            if start >= end or not row["source"].strip():
                raise ValueError(f"Invalid operations interval/source on line {line}")
            if row["operating_direction"] not in ("07", "25", "", "unknown"):
                raise ValueError(f"Invalid operating direction on line {line}")
            if row["rwy18_weather_usable"] not in ("0", "1", "", "unknown"):
                raise ValueError(f"RWY18 label must be 0, 1 or unknown on line {line}")
            rows.append({**row, "start": start, "end": end, "available": available})
    rows.sort(key=lambda row: row["start"])
    for previous, current in zip(rows, rows[1:]):
        if current["start"] < previous["end"]:
            raise ValueError("Overlapping operations intervals; resolve conflicting labels first")
    return rows


def label_at(labels, at, known_by=None):
    for row in labels:
        if row["start"] <= at < row["end"] and (known_by is None or row["available"] <= known_by):
            return row
    return None


def build_dataset(runs, observations, labels):
    observations = sorted(observations, key=lambda row: row["valid_time"])
    observation_times = [parse_time(row["valid_time"]) for row in observations]
    rows = []
    for run in sorted(runs, key=lambda item: item["run_at"]):
        decision = parse_time(run["run_at"]) + timedelta(hours=4)
        initial = label_at(labels, decision, known_by=decision)
        initial_direction = initial["operating_direction"] if initial else None
        if initial_direction not in ("07", "25"):
            initial_direction = None
        state = DirectionState(initial_direction)
        # A retrospective observation is conservatively delayed by an hour.
        past_index = bisect_right(observation_times, decision - timedelta(hours=1)) - 1
        past = observations[past_index] if past_index >= 0 else None
        if past and decision - parse_time(past["valid_time"]) > timedelta(hours=2):
            past = None
        for weather in sorted(run["hourly"], key=lambda item: item["valid_time"]):
            at = parse_time(weather["valid_time"])
            if at < decision:
                continue
            prediction = state.step(weather, resolution_minutes=60)
            lead = (at - decision).total_seconds() / 3600
            if not 1 <= lead <= 48:
                continue
            target = label_at(labels, at)
            # Observed target weather is reference-only, never an input feature.
            reference_index = bisect_right(observation_times, at) - 1
            reference = observations[reference_index] if reference_index >= 0 else None
            if reference and at - parse_time(reference["valid_time"]) > timedelta(minutes=10):
                reference = None
            row = {
                "decision_time": iso(decision), "valid_time": iso(at), "lead_time_hours": int(lead),
                "model": weather["model"], "model_run_at": run["run_at"],
                "forecast_available_at": weather["available_at"],
                "availability_basis": weather["availability_basis"],
                "availability_verified": False,
                "wind_speed_kt": weather["wind_speed_kt"], "wind_from_deg_true": weather["wind_from_deg_true"],
                "wind_gust_kt": weather["wind_gust_kt"],
                "initial_operating_direction": initial_direction,
                "initial_direction_source": initial["source"] if initial_direction else "unknown",
                "past_observation_time": past["valid_time"] if past else None,
                "past_wind_speed_kt": past.get("wind_speed_kt") if past else None,
                "past_wind_from_deg_true": past.get("wind_from_deg_true") if past else None,
                "reference_observation_time": reference["valid_time"] if reference else None,
                "reference_wind_speed_kt": reference.get("wind_speed_kt") if reference else None,
                "reference_wind_from_deg_true": reference.get("wind_from_deg_true") if reference else None,
                "reference_wind_gust_kt": reference.get("wind_gust_kt") if reference else None,
                "target_operating_direction": target["operating_direction"] if target else None,
                "target_rwy18_weather_usable": target["rwy18_weather_usable"] if target else None,
                "target_source": target["source"] if target else None,
                "baseline_operating_direction": prediction["operating_direction"],
                "baseline_rwy18_weather_state": prediction["rwy18_weather_state"],
                "baseline_temporal_resolution_minutes": 60,
            }
            rows.append(row)
    return rows


def dataset_report(rows, observations, labels):
    known_od = sum(row["target_operating_direction"] in ("07", "25") for row in rows)
    known_18 = sum(row["target_rwy18_weather_usable"] in ("0", "1") for row in rows)
    missing = {key: sum(row.get(key) is None for row in rows)
               for key in ("wind_speed_kt", "wind_from_deg_true", "wind_gust_kt", "reference_wind_speed_kt")}
    errors = []
    keys = [(r["model"], r["model_run_at"], r["valid_time"]) for r in rows]
    if len(keys) != len(set(keys)):
        errors.append("duplicate_model_run_valid_time")
    for row in rows:
        if parse_time(row["forecast_available_at"]) > parse_time(row["decision_time"]):
            errors.append("forecast_available_after_decision")
        if parse_time(row["valid_time"]) <= parse_time(row["decision_time"]):
            errors.append("target_not_in_future")
    mae = {}
    for horizon in (1, 6, 24):
        pairs = [(r["wind_speed_kt"], r["reference_wind_speed_kt"]) for r in rows
                 if r["lead_time_hours"] == horizon and r["wind_speed_kt"] is not None and r["reference_wind_speed_kt"] is not None]
        mae[str(horizon)] = {"samples": len(pairs), "wind_speed_mae_kt": sum(abs(a-b) for a,b in pairs)/len(pairs) if pairs else None}
    return {"status": "invalid" if errors else "ready_for_labels" if not known_od and not known_18 else "labeled",
            "rows": len(rows), "observation_rows": len(observations), "label_intervals": len(labels),
            "operating_direction_labels": known_od, "rwy18_weather_labels": known_18,
            "missing_counts": missing, "validation_errors": sorted(set(errors)),
            "weather_forecast_diagnostics": mae,
            "operational_model_metrics": None,
            "limitations": ["Historical publication times are estimated, not verified.",
                            "Current UNH snapshots are not backfilled into historical labels.",
                            "Hourly archive baseline cannot resolve a 30-minute transition precisely.",
                            "Weather errors are not operating-direction accuracy."]}
