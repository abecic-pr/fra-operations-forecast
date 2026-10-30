"""Explicit as-of replay for jury issue times; missing inputs stay disclosed."""

import csv
from datetime import datetime, timedelta
from pathlib import Path

from .dataset import load_labels, label_at
from .domain import UTC, RULESET, DirectionState, iso, parse_time
from .ml_data import uv
from .ml_live import load_artifact
from .sources import SourceClient, forecast, write_csv, write_json
from . import operations_ml


def issue_times(path):
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if "forecast_reference_time" not in (reader.fieldnames or []):
            raise ValueError("Issue CSV requires forecast_reference_time with explicit timezone")
        times = [parse_time(row["forecast_reference_time"]) for row in reader]
    if not times or len(times) != len(set(times)):
        raise ValueError("Provide at least one unique jury issue time")
    if any(t.minute or t.second or t.microsecond for t in times):
        raise ValueError("This version requires whole-hour forecast reference times")
    if any(t > datetime.now(UTC) for t in times):
        raise ValueError("Cannot replay a forecast issue time that has not happened yet")
    return sorted(times)


def eligible_artifact(artifact, report, reference):
    if artifact is None:
        return False
    cutoff = artifact.get("data_cutoff")
    if not cutoff:
        dates = [report.get("partitions", {}).get(p, {}).get("last_target") for p in ("train", "selection", "calibration")]
        if not all(dates):
            return False
        cutoff = iso(max(parse_time(d) for d in dates)+timedelta(hours=1))
    return parse_time(cutoff) < reference


def replay(reference, data_dir, client, labels=()):
    from .direction import prediction
    from .comparison import MODEL_VERSION as COMPARISON_VERSION, probability_status, values, wind_dict
    from .pipeline import next_change
    from .wind_ml import corrected, matrices, probabilities
    eligible = reference-timedelta(hours=4)
    run_at = eligible.replace(hour=eligible.hour//6*6, minute=0, second=0, microsecond=0)
    source_error = None
    try:
        run = forecast(client, "icon_eu", run_at, forecast_days=4)
        source = {r["valid_time"]: r for r in run["hourly"] if parse_time(r["available_at"]) <= reference}
    except (OSError, ValueError, KeyError) as exc:
        source, source_error = {}, str(exc)
    targets = [iso(reference+timedelta(hours=h)) for h in range(1, 49)]
    inputs, weather = [], []
    for h, stamp in enumerate(targets, 1):
        point = source.get(stamp, {})
        vector = uv(point.get("wind_speed_kt"), point.get("wind_from_deg_true"))
        inputs.append({"valid_time": stamp, "model_lead_hours": (parse_time(stamp)-run_at).total_seconds()/3600,
                       "lead_time_hours": h, "raw_u_kt": vector[0] if vector else None,
                       "raw_v_kt": vector[1] if vector else None, "raw_gust_kt": point.get("wind_gust_kt"),
                       "target_u_kt": None, "target_v_kt": None, "target_gust_kt": None})
        weather.append({k: point.get(k) for k in ("wind_speed_kt", "wind_from_deg_true", "wind_gust_kt")})
    chance, identities, reasons = [None]*48, ["raw_icon_eu"]*48, []
    statuses, artifacts = ["unavailable"]*48, {}
    comparison, comparison_report, error = load_artifact(data_dir, COMPARISON_VERSION)
    legacy, legacy_report, legacy_error = load_artifact(data_dir)
    if eligible_artifact(comparison, comparison_report, reference):
        artifacts["wind"] = {k: comparison_report.get(k) for k in ("model_version", "experiment_id", "data_cutoff", "trained_at", "dataset_sha256")}
        import numpy as np
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=2):
            predicted = values(comparison, inputs)
            winner = comparison["policy"]["winner"]
            chances = {name: probabilities({"calibration": pool}, inputs, predicted[name])
                       for name, pool in comparison["calibrations"].items()}
        for i in range(48):
            name = winner if np.isfinite(predicted[winner][i, :2]).all() else "raw_icon_eu"
            weather[i] = wind_dict(predicted[name][i])
            p = chances.get(name, np.full(48, np.nan))[i]
            chance[i] = float(p) if np.isfinite(p) else None
            statuses[i] = probability_status(comparison_report, name) if chance[i] is not None else "unavailable"
            identities[i] = f"{COMPARISON_VERSION}:{comparison['experiment_id']}:{name}"
    elif eligible_artifact(legacy, legacy_report, reference):
        artifacts["wind"] = {k: legacy_report.get(k) for k in ("model_version", "trained_at", "dataset_sha256", "partitions")}
        import numpy as np
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=2):
            x, raw, _ = matrices(inputs)
            predicted = corrected(legacy, x, raw)
            chances = probabilities(legacy, inputs, predicted)
        weather = [wind_dict(v) for v in predicted]
        chance = [float(p) if np.isfinite(p) else None for p in chances]
        statuses = [legacy["probability_status"] if p is not None else "unavailable" for p in chance]
        identities = [legacy["model_version"]]*48
    else:
        reasons.append("no_eligible_wind_probability_artifact_before_issue")
    operations, operations_report, operations_error = load_artifact(data_dir, operations_ml.MODEL_VERSION, operations_ml.FEATURE_NAMES)
    if not eligible_artifact(operations, operations_report, reference):
        operations = None
        reasons.append("no_eligible_independent_label_od_artifact_before_issue")
    else:
        artifacts["operations"] = {k: operations_report.get(k) for k in ("model_version", "experiment_id", "data_cutoff", "trained_at", "labels_sha256", "dataset_sha256")}
    label = label_at(labels, reference, known_by=reference)
    initial = label["operating_direction"] if label and label["operating_direction"] in ("07", "25") else None
    recent = operations_ml.recent_observation(data_dir, reference)
    context = operations_ml.forecast_context([source.get(stamp, {"valid_time": stamp}) for stamp in targets], reference)
    baseline = DirectionState(initial)
    selected_direction = DirectionState(initial)
    if iso(reference) in source:
        baseline.step(source[iso(reference)], 60)
    result = []
    for i, stamp in enumerate(targets):
        raw = source.get(stamp, {"valid_time": stamp})
        rule = baseline.step(raw, 60)
        od = operations_ml.predict(operations, {**raw, **context.get(stamp, {})}, initial, i+1, recent) if operations else {
            "status": "unavailable", "reason": "no_eligible_independent_label_od_artifact_before_issue",
            "operating_direction": None, "p_od07": None, "p_od25": None, "certainty_score": None}
        selected_rule = selected_direction.step({"valid_time": stamp, **weather[i]}, 60)
        direction = prediction(selected_rule, od, "challenge_rules_selected_weather", identities[i])
        plan = direction["runway_plan"]
        result.append({"forecast_reference_time": iso(reference), "valid_time": stamp, "lead_time_hours": i+1,
                       "expected_operating_direction": direction["operating_direction"],
                       "expected_direction_basis": direction["basis"],
                       "landing_movement_direction": plan["landings"]["movement_direction"],
                       "landing_approach_from": plan["landings"]["approach_from"],
                       "landing_runway_ends": ",".join(plan["landings"]["runway_ends"]),
                       "centre_departure_direction": plan["centre_departures"]["movement_direction"],
                       "centre_departure_runway_end": plan["centre_departures"]["runway_end"],
                       "runway18_departure_direction": "southbound",
                       **weather[i], "p_rwy18_weather_usable": chance[i],
                       "rwy18_probability_status": statuses[i],
                       "operating_direction": od["operating_direction"], "p_od07": od["p_od07"], "p_od25": od["p_od25"],
                       "certainty_score": od["certainty_score"], "od_status": od["status"],
                       "od_probability_status": od.get("probability_status", "unavailable"),
                       "od_label_quality": od.get("label_quality"),
                       "od_recent_observation_time": od.get("recent_observation_time"),
                       "baseline_operating_direction": rule["operating_direction"],
                       "baseline_rwy18_weather_state": rule["rwy18_weather_state"],
                       "wind_model": identities[i], "od_model": operations_ml.MODEL_VERSION if operations else None,
                       "source_model": "icon_eu", "model_run_at": iso(run_at),
                       "available_at": raw.get("available_at"), "fetched_at": raw.get("fetched_at"),
                       "availability_verified": False, "availability_basis": "estimated_four_hour_model_delay"})
    timeline = [{"valid_time": p["valid_time"], "direction": p["operating_direction"] if p["od_status"] == "available" else None} for p in result]
    change = next_change(timeline, "direction", initial)
    change["method"] = "predicted_hourly_class_change"
    if change["status"] == "change_expected" and change["earliest"] is None and initial:
        change["earliest"] = iso(reference)
    for row in result:
        row.update(next_change_status=change["status"], next_change_earliest=change["earliest"], next_change_latest=change["latest"])
    counts = {"wind_hours": sum(p["wind_speed_kt"] is not None for p in result),
              "rwy18_probability_hours": sum(p["p_rwy18_weather_usable"] is not None for p in result),
              "od_probability_hours": sum(p["od_status"] == "available" and p["p_od07"] is not None for p in result)}
    return result, {"forecast_reference_time": iso(reference), **counts, "source_error": source_error,
                    "status": "complete_with_availability_assumptions" if all(n == 48 for n in counts.values()) else "incomplete",
                    "reasons": reasons, "next_change": change, "artifacts": artifacts,
                    "replay_kind": "retrospective_reconstruction_with_assumed_publication_delay"}


def export(data_dir, issues_path, output_dir, labels_path=None, client=None):
    times = issue_times(issues_path)
    labels = load_labels(labels_path)
    client = client or SourceClient(data_dir)
    rows, issues = [], []
    for reference in times:
        points, coverage = replay(reference, data_dir, client, labels)
        rows.extend(points)
        issues.append(coverage)
    if len(rows) != 48*len(times) or len({(p["forecast_reference_time"], p["valid_time"]) for p in rows}) != len(rows):
        raise ValueError("Submission must have 48 unique future targets per issue")
    report = {"schema_version": "1.0", "generated_at": iso(datetime.now(UTC)), "issues": issues,
              "status": "complete_with_availability_assumptions" if all(i["status"].startswith("complete") for i in issues) else "incomplete",
              "rows": len(rows), "jury_schema_confirmed": False, "ruleset": RULESET, "source_checks": client.checks,
              "limitations": ["Internal export schema; organizer dates/schema are not given in the brief.",
                              "Forecast publication delay and historical observation revisions are unverified.",
                              "Null OD is an incomplete deliverable, not a fabricated rule-trained model."]}
    output = Path(output_dir)
    write_csv(output/"forecasts.csv", rows)
    write_json(output/"forecasts.json", {"schema_version": "1.0", "generated_at": report["generated_at"], "forecast": rows})
    write_json(output/"report.json", report)
    return report
