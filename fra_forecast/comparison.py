"""Fixed forecast candidates, matched evaluation, discovery, and live comparison."""

from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

from .domain import UTC, RULESET, DirectionState, iso, parse_time
from .ml_data import DATA_VERSION, uv
from .ml_live import explicit_live_run, load_artifact
from .sources import SourceClient, forecast, write_json
from .wind_ml import (ARTIFACT_VERSION, FEATURES, PARAMETERS, chronological_split, corrected,
                      fit_residuals, matrices, probabilities, probability_metrics,
                      regression_metrics, residual_calibration, save_artifact, weather_outcome)

MODEL_VERSION = "wind-comparison-v1"
CANDIDATES = ("raw_icon_eu", "persistence", "boosting_correction", "linear_correction", "equal_blend")
ELIGIBLE = ("raw_icon_eu", "linear_correction", "boosting_correction", "equal_blend")
WEIGHTS = {"raw_icon_eu": 1/3, "linear_correction": 1/3, "boosting_correction": 1/3}
LIMITATIONS = ["Historical availability is estimated; retrospective DWD observations can be revised.",
               "Weather suitability is not official runway availability or actual runway use.",
               "Shared ICON-EU inputs make correction candidates correlated, not independent sources.",
               "Hourly values cannot resolve exact 30-minute persistence or within-hour reversals.",
               "Empirical probabilities and forecast disagreement are not guaranteed calibrated confidence.",
               "The previously inspected test period is exploratory; fresh validation is still needed."]


def dataset(data_dir):
    raw = (Path(data_dir)/"ml"/"dataset.json").read_bytes()
    obj = json.loads(raw)
    if obj.get("data_version") != DATA_VERSION:
        raise ValueError("Unsupported comparison dataset; run prepare-ml")
    rows = obj["rows"]
    keys = [(r["decision_time"], r["valid_time"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate decision/valid-time pairs in comparison dataset")
    return rows, hashlib.sha256(raw).hexdigest()


def values(artifact, rows):
    import numpy as np
    x, raw, _ = matrices(rows)
    result = {"raw_icon_eu": raw, "persistence": np.asarray([
        [r.get("persistence_u_kt"), r.get("persistence_v_kt"), r.get("persistence_gust_kt")]
        for r in rows], dtype=float)}
    for name in ("boosting_correction", "linear_correction"):
        model = artifact.get("models", {}).get(name)
        if not model or any(model["estimators"].get(k) is None for k in ("u", "v")):
            result[name] = np.full_like(raw, np.nan)
        else:
            result[name] = corrected(model, x, raw, candidate=True)
            if model["estimators"].get("gust") is None:
                result[name][:, 2] = np.nan
    result["equal_blend"] = sum(result[name]*weight for name, weight in WEIGHTS.items())
    blend = result["equal_blend"]
    blend[:, 2] = np.maximum(blend[:, 2], np.hypot(blend[:, 0], blend[:, 1]))
    return result


def reference_masks(raw, actual):
    import numpy as np
    return (np.isfinite(raw[:, :2]).all(axis=1) & np.isfinite(actual[:, :2]).all(axis=1),
            np.isfinite(raw[:, 2]) & np.isfinite(actual[:, 2]))


def score(predicted, actual, wind, gust):
    import numpy as np
    reference = actual.copy()
    reference[~wind, :2] = np.nan
    reference[~gust, 2] = np.nan
    return regression_metrics(predicted, reference)


def choose_policy(rows, predicted):
    import numpy as np
    _, _, actual = matrices(rows)
    wind, gust = reference_masks(predicted["raw_icon_eu"], actual)
    raw = score(predicted["raw_icon_eu"], actual, wind, gust)
    counts = {"wind_rows": int(wind.sum()), "gust_rows": int(gust.sum()),
              "wind_dates": len({r["decision_time"][:10] for r, k in zip(rows, wind) if k}),
              "gust_dates": len({r["decision_time"][:10] for r, k in zip(rows, gust) if k})}
    enough = min(counts["wind_rows"], counts["gust_rows"]) >= 100 and min(counts["wind_dates"], counts["gust_dates"]) >= 10
    decisions, passing = {}, []
    for name in ELIGIBLE:
        metrics = score(predicted[name], actual, wind, gust)
        full = metrics["samples"] == raw["samples"] and metrics["gust_samples"] == raw["gust_samples"]
        better = bool(enough and full and metrics["vector_rmse_kt"] is not None
                      and metrics["vector_rmse_kt"] < raw["vector_rmse_kt"]
                      and metrics["speed_mae_kt"] <= raw["speed_mae_kt"]*1.02
                      and metrics["gust_mae_kt"] <= raw["gust_mae_kt"])
        decisions[name] = {"passes_gate": better, "full_reference_coverage": full, "metrics": metrics}
        if better:
            passing.append(name)
    winner = min(passing, key=lambda n: (decisions[n]["metrics"]["vector_rmse_kt"],
                                       decisions[n]["metrics"]["gust_mae_kt"], ELIGIBLE.index(n))) if passing else "raw_icon_eu"
    return {"winner": winner, "weights": WEIGHTS if winner == "equal_blend" else {winner: 1.0},
            "selection_partition_only": True, "cohort": counts, "sufficient_coverage": enough,
            "candidates": decisions, "fallback": "raw_icon_eu",
            "reason": "validation_gate_passed" if passing else "no_candidate_passed_validation_gate"}


def weather_scores(predicted, actual, gust_directions, rows, p=None):
    import numpy as np
    truth = weather_outcome(actual, gust_directions)
    expected = weather_outcome(predicted)
    keep = np.isfinite(truth) & np.isfinite(expected)
    bad = keep & (truth == 0)
    result = {"samples": int(keep.sum()), "adverse_cases": int(bad.sum()),
              "unique_adverse_valid_times": len({r["valid_time"] for r, k in zip(rows, bad) if k}),
              "missed_adverse_cases": int((bad & (expected == 1)).sum()),
              "false_alarm_cases": int((keep & (truth == 1) & (expected == 0)).sum()),
              "adverse_recall": float((expected[bad] == 0).mean()) if bad.any() else None,
              "deterministic_brier_score": float(((truth[keep]-expected[keep])**2).mean()) if keep.any() else None}
    if p is not None:
        result["probability"] = probability_metrics(p, truth)
        result["probability"]["unique_adverse_valid_times"] = result["unique_adverse_valid_times"]
    return result


def evaluate(rows, artifact):
    import numpy as np
    candidates = values(artifact, rows)
    _, _, actual = matrices(rows)
    wind, gust = reference_masks(candidates["raw_icon_eu"], actual)
    chance = {n: probabilities({"calibration": pool}, rows, candidates[n])
              for n, pool in artifact.get("calibrations", {}).items()}
    result = {}
    for horizon in ("all_1_to_48h", 1, 6, 24, 48):
        mask = np.asarray([1 <= r["lead_time_hours"] <= 48 and
                           (horizon == "all_1_to_48h" or r["lead_time_hours"] == horizon) for r in rows])
        subset = [r for r, k in zip(rows, mask) if k]
        directions = [r.get("target_gust_from_deg_true") for r in subset]
        scores = {}
        for name, pred in candidates.items():
            metrics = score(pred, actual, wind & mask, gust & mask)
            metrics["weather"] = weather_scores(pred[mask], actual[mask], directions, subset,
                                                 chance[name][mask] if name in chance else None)
            if name in chance:
                truth = weather_outcome(actual[mask], directions)
                probability = chance[name][mask]
                known = np.isfinite(truth) & np.isfinite(probability)
                quality = metrics["weather"]["probability"]
                quality["missed_adverse_cases_at_0_5"] = int((known & (truth == 0) & (probability >= 0.5)).sum())
                quality["false_alarm_cases_at_0_5"] = int((known & (truth == 1) & (probability < 0.5)).sum())
                quality["matched_baselines"] = {}
                for baseline_name, source in (("challenge_rules", "raw_icon_eu"), ("persistence", "persistence")):
                    baseline = weather_outcome(candidates[source][mask])
                    matched = known & np.isfinite(baseline)
                    quality["matched_baselines"][baseline_name] = {
                        "samples": int(matched.sum()), "excluded_probability_cases": int((known & ~matched).sum()),
                        "model_brier_score": float(((probability[matched]-truth[matched])**2).mean()) if matched.any() else None,
                        "baseline_brier_score": float(((baseline[matched]-truth[matched])**2).mean()) if matched.any() else None}
            # Persistence can be missing on a different subset: show its matched raw score.
            valid_w = wind & mask & np.isfinite(pred[:, :2]).all(axis=1)
            valid_g = gust & mask & np.isfinite(pred[:, 2])
            metrics["raw_on_same_rows"] = score(candidates["raw_icon_eu"], actual, valid_w, valid_g)
            scores[name] = metrics
        result[str(horizon)] = {"candidates": scores, "reference_wind_rows": int((wind & mask).sum()),
                               "reference_gust_rows": int((gust & mask).sum()),
                               "unique_valid_times": len({r["valid_time"] for r in subset}),
                               "issue_dates": len({r["decision_time"][:10] for r in subset})}
    return result


def probability_status(report, name):
    coverage = (report or {}).get("test", {}).get("all_1_to_48h", {}).get("candidates", {}).get(name, {}).get("weather", {})
    return ("provisional_low_event_coverage" if coverage.get("unique_adverse_valid_times", 0) < 20
            else "provisional_empirical")


def patterns(rows, predicted):
    import numpy as np
    _, raw, actual = matrices(rows)
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        lead = row["lead_time_hours"]
        groups[f"lead:{'1-6' if lead <= 6 else '7-24' if lead <= 24 else '25-48'}"].append(i)
        direction = row.get("raw_wind_from_deg_true")
        if direction is not None:
            groups[f"forecast_sector:{int((direction+22.5)%360//45)*45}"].append(i)
        near = -raw[i, 1] >= 10 or abs(raw[i, 0]) >= 35
        groups[f"near_rwy18_mean_wind_threshold:{near}"].append(i)
    summaries = {}
    for name, indexes in groups.items():
        dates = len({rows[i]["decision_time"][:10] for i in indexes})
        enough = len(indexes) >= 30 and dates >= 5
        summaries[name] = {"rows": len(indexes), "issue_dates": dates, "status": "available" if enough else "insufficient_coverage",
                           "metrics": {n: regression_metrics(v[indexes], actual[indexes]) for n, v in predicted.items()} if enough else None}
    correlations = {}
    for name in CANDIDATES[1:]:
        a = (raw[:, :2]-actual[:, :2]).ravel()
        b = (predicted[name][:, :2]-actual[:, :2]).ravel()
        keep = np.isfinite(a) & np.isfinite(b)
        correlations[name] = float(np.corrcoef(a[keep], b[keep])[0, 1]) if keep.sum() >= 30 and np.std(a[keep]) > 0 and np.std(b[keep]) > 0 else None
    differences = np.full(len(rows), np.nan)
    for i in range(len(rows)):
        vectors = [v[i, :2] for v in predicted.values() if np.isfinite(v[i, :2]).all()]
        if len(vectors) >= 2:
            differences[i] = max(float(np.linalg.norm(a-b)) for a in vectors for b in vectors)
    examples = sorted((i for i in range(len(rows)) if np.isfinite(differences[i])), key=lambda i: -differences[i])[:5]
    return {"partition": "selection_only", "groups": summaries, "residual_correlation_with_raw": correlations,
            "disagreement_examples": [{"decision_time": rows[i]["decision_time"], "valid_time": rows[i]["valid_time"],
                                       "max_vector_difference_kt": float(differences[i])} for i in examples],
            "limitation": "Descriptive groups and correlations, not independent weather events or a routing policy."}


def train(data_dir="data", progress=print):
    import sklearn
    from threadpoolctl import threadpool_limits
    root = Path(data_dir)
    rows, digest = dataset(root)
    groups, split = chronological_split(rows)
    settings = {"boosting": PARAMETERS, "linear": {"alpha": 1.0}, "blend": WEIGHTS, "split": split}
    experiment = hashlib.sha256((digest+json.dumps(settings, sort_keys=True)+MODEL_VERSION).encode()).hexdigest()[:20]
    artifact = {"artifact_version": ARTIFACT_VERSION, "model_version": MODEL_VERSION, "features": FEATURES,
                "sklearn_version": sklearn.__version__, "experiment_id": experiment, "models": {}, "calibrations": {}}
    with threadpool_limits(limits=2):
        previous, old_report, _ = load_artifact(root)
        reusable = previous and old_report.get("dataset_sha256") == digest and old_report.get("split") == split and old_report.get("parameters") == PARAMETERS
        boosting = previous["estimators"] if reusable else fit_residuals(groups["train"], progress=progress)
        artifact["models"] = {"boosting_correction": {"estimators": boosting},
                              "linear_correction": {"estimators": fit_residuals(groups["train"], linear=True, progress=progress)}}
        selection = [r for r in groups["selection"] if r["lead_time_hours"] <= 48]
        selected_values = values(artifact, selection)
        policy = choose_policy(selection, selected_values)
        policy["experiment_id"] = experiment
        artifact["policy"] = policy
        cal = groups["calibration"]
        cal_values = values(artifact, cal)
        pools = {}
        for name in dict.fromkeys(("raw_icon_eu", policy["winner"])):
            artifact["calibrations"][name], pools[name] = residual_calibration(cal, cal_values[name])
        artifact["data_cutoff"] = iso(max(parse_time(r["valid_time"]) for k in ("train", "selection", "calibration") for r in groups[k])+timedelta(hours=1))
        report = {"schema_version": "1.0", "model_version": MODEL_VERSION, "experiment_id": experiment,
                  "trained_at": iso(datetime.now(UTC)), "sklearn_version": sklearn.__version__, "dataset_sha256": digest,
                  "settings": settings, "data_cutoff": artifact["data_cutoff"], "policy": policy,
                  "partitions": {k: {"rows": len(v), "first_issue": v[0]["decision_time"], "last_issue": v[-1]["decision_time"],
                                     "last_target": max(r["valid_time"] for r in v)} for k, v in groups.items()},
                  "selection": evaluate(selection, artifact), "calibration_pools": pools,
                  "test": evaluate(groups["test"], artifact), "test_status": "exploratory_reused_test",
                  "discovery": patterns(selection, selected_values), "historical_availability_verified": False,
                  "operations_status": "requires_independent_labels", "limitations": LIMITATIONS}
    save_artifact(root, artifact, report)
    write_json(root/"models"/MODEL_VERSION/"policy.json", policy)
    write_json(root/"comparison"/"evaluation.json", report)
    progress(f"Selected {policy['winner']}: {policy['reason']}. Report: {root/'comparison'/'evaluation.json'}", flush=True)
    return report


def probe_gfs(data_dir, report=None):
    root = Path(data_dir)
    client = SourceClient(root, timeout=10, attempts=1)
    now = datetime.now(UTC)
    eligible = now-timedelta(hours=6)
    recent = eligible.replace(hour=eligible.hour//6*6, minute=0, second=0, microsecond=0)
    dates = [recent]
    for part in ("train", "selection", "test"):
        stamp = (report or {}).get("partitions", {}).get(part, {}).get("first_issue")
        if stamp:
            at = parse_time(stamp)-timedelta(hours=6)
            dates.append(at.replace(hour=at.hour//6*6, minute=0, second=0, microsecond=0))
    runs = []
    for at in dict.fromkeys(dates):
        try:
            result = forecast(client, "gfs_global", at, forecast_days=4, availability_delay_hours=6)
            rows = result["hourly"]
            runs.append({"run_at": iso(at), "status": "available" if rows else "unavailable", "hours": len(rows),
                         "gust_hours": sum(r.get("wind_gust_kt") is not None for r in rows),
                         "first_valid_time": rows[0]["valid_time"] if rows else None,
                         "last_valid_time": rows[-1]["valid_time"] if rows else None})
        except (OSError, ValueError, KeyError) as exc:
            runs.append({"run_at": iso(at), "status": "unavailable", "error": str(exc)})
    output = {"model": "gfs_global", "checked_at": iso(now), "runs": runs, "checks": client.checks,
              "selection_eligible": False, "availability_verified": False,
              "availability_basis": "estimated_6_hour_model_delay", "status": "partial" if any(r["status"] == "available" for r in runs) else "unavailable",
              "limitations": ["Small archive probe only, no matched historical evaluation.",
                              "Source gust interval compatibility is not established; no ranked gust skill claim."]}
    write_json(root/"comparison"/"gfs-probe.json", output)
    return output


def discover(data_dir="data", probe=False):
    root = Path(data_dir)
    rows, digest = dataset(root)
    path = root/"comparison"/"evaluation.json"
    evaluation = json.loads(path.read_text()) if path.exists() else {}
    path = root/"comparison"/"gfs-probe.json"
    gfs = probe_gfs(root, evaluation) if probe else json.loads(path.read_text()) if path.exists() else {"status": "not_evaluated"}
    checks = []
    for path in (root/"sources.json", root/"ml"/"sources.json"):
        if path.exists():
            data = json.loads(path.read_text())
            checks.extend(data if isinstance(data, list) else data.get("sources", []))
    grouped = defaultdict(list)
    for check in checks:
        grouped[check.get("source", "unknown")].append(check)
    inventory = [{"source": name, "requests": len({c.get('url') for c in items}),
                  "last_fetched_at": max((c.get("fetched_at", "") for c in items), default="") or None,
                  "status": "partial" if any(c.get("status") == "error" for c in items) else "usable",
                  "source_url": next((c["url"] for c in items if c.get("url")), None)} for name, items in grouped.items()]
    output = {"schema_version": "1.0", "generated_at": iso(datetime.now(UTC)), "dataset_sha256": digest,
              "rows": len(rows), "issue_dates": len({r["decision_time"][:10] for r in rows}),
              "unique_valid_times": len({r["valid_time"] for r in rows}),
              "first_issue": min(r["decision_time"] for r in rows), "last_issue": max(r["decision_time"] for r in rows),
              "missing": {key: sum(r.get(key) is None for r in rows) for key in ("raw_gust_kt", "target_gust_kt", "persistence_gust_kt")},
              "sources": inventory, "additional_source": gfs,
              "patterns": evaluation.get("discovery") if evaluation.get("dataset_sha256") == digest else None,
              "operations_labels": {"status": "not_verified", "reason": "See operations-evaluation.json; current-state snapshots are not historical intervals."},
              "limitations": LIMITATIONS, "source_research": "docs/operations-label-research.md"}
    write_json(root/"comparison"/"discovery.json", output)
    return output


def observed_initial(snapshot, data_dir, reference):
    candidates = [snapshot.get("observed_operations") or {}]
    path = Path(data_dir)/"operations-snapshots.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                candidates.append(json.loads(line))
            except ValueError:
                continue  # An interrupted append must not take down the weather baseline.
    known = []
    for row in candidates:
        if not isinstance(row, dict):
            continue
        stamp = row.get("fetched_at") or row.get("observed_at")
        if stamp and row.get("operating_direction") in ("07", "25"):
            try:
                age = (reference-parse_time(stamp)).total_seconds()
            except (ValueError, TypeError):
                continue
            if 0 <= age <= 5400:
                known.append((stamp, row["operating_direction"]))
    return max(known)[1] if known else None


def wind_dict(vector):
    u, v, gust = (float(x) for x in vector)
    speed = math.hypot(u, v)
    return {"wind_speed_kt": speed if math.isfinite(speed) else None,
            "wind_from_deg_true": math.degrees(math.atan2(-u, -v)) % 360 if math.isfinite(speed) and speed >= 0.5 else None,
            "wind_gust_kt": gust if math.isfinite(gust) else None}


def disagreement(candidates):
    known = {n: c for n, c in candidates.items() if c.get("wind_speed_kt") is not None}
    if len(known) < 2:
        return {"status": "unknown", "candidate_count": len(known), "max_vector_difference_kt": None}
    vectors = [uv(c["wind_speed_kt"], c["wind_from_deg_true"]) for c in known.values()]
    vectors = [v for v in vectors if v is not None]
    gusts = [c["wind_gust_kt"] for c in known.values() if c.get("wind_gust_kt") is not None]
    speeds = [c["wind_speed_kt"] for c in known.values()]
    states = {n: c["runway_wind"]["18"]["weather_state"] for n, c in known.items()
              if c["runway_wind"]["18"]["weather_state"] != "unknown"}
    return {"status": "available", "candidate_count": len(known), "speed_range_kt": [min(speeds), max(speeds)],
            "gust_range_kt": [min(gusts), max(gusts)] if len(gusts) >= 2 else None,
            "max_vector_difference_kt": max(math.hypot(a[0]-b[0], a[1]-b[1]) for a in vectors for b in vectors) if len(vectors) >= 2 else None,
            "rwy18_disagreement": states if len(set(states.values())) > 1 else {},
            "meaning": "Descriptive spread, not a confidence interval."}


def refresh(data_dir="data", include_gfs=True, client=None):
    import numpy as np
    from threadpoolctl import threadpool_limits
    from .pipeline import next_change
    root = Path(data_dir)
    snapshot = json.loads((root/"forecast.json").read_text())
    reference = parse_time(snapshot["forecast_reference_time"])
    targets = [iso(reference+timedelta(hours=h)) for h in range(1, 49)]
    if [p["valid_time"] for p in snapshot["forecast"]] != targets:
        raise ValueError("Expected exactly 48 hourly targets after the forecast reference")
    artifact, report, error = load_artifact(root, MODEL_VERSION)
    if artifact and parse_time(artifact["data_cutoff"]) >= reference:
        artifact, error = None, "model_data_not_before_reference"
    client = client or SourceClient(root, timeout=10, attempts=1)
    provenance, source, errors = {}, {}, []
    for point in snapshot["forecast"]:
        ml = point.get("ml", {})
        if (ml.get("source_model") == "icon_eu" and ml.get("raw_wind_speed_kt") is not None
                and ml.get("available_at") and parse_time(ml["available_at"]) <= reference
                and ml.get("model_run_at") and 0 <= (reference-parse_time(ml["model_run_at"])).total_seconds() <= 86400):
            source[point["valid_time"]] = {"valid_time": point["valid_time"], "wind_speed_kt": ml["raw_wind_speed_kt"],
                                         "wind_from_deg_true": ml.get("raw_wind_from_deg_true"), "wind_gust_kt": ml.get("raw_wind_gust_kt")}
            provenance[point["valid_time"]] = {k: ml.get(k) for k in ("model_run_at", "available_at", "availability_basis", "availability_verified", "fetched_at")}
    if not source:
        try:
            run, prov = explicit_live_run(client, reference)
            source = {r["valid_time"]: r for r in run["hourly"]}
            provenance = {k: {**prov, "fetched_at": r.get("fetched_at")} for k, r in source.items()}
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"source": "icon_eu", "error": str(exc)})
    persistence = None
    for name in ("metar", "dwd_observation", "current_weather"):
        row = snapshot.get(name) or {}
        available = row.get("available_at") or row.get("fetched_at")
        at = row.get("valid_time")
        if at and available and parse_time(available) <= reference and 0 <= (reference-parse_time(at)).total_seconds() <= 5400:
            if persistence is None or at > persistence["valid_time"]:
                persistence = row
    past = uv(persistence.get("wind_speed_kt"), persistence.get("wind_from_deg_true")) if persistence else None
    rows = []
    for h, stamp in enumerate(targets, 1):
        weather, prov = source.get(stamp, {}), provenance.get(stamp, {})
        vector = uv(weather.get("wind_speed_kt"), weather.get("wind_from_deg_true"))
        run = parse_time(prov["model_run_at"]) if prov.get("model_run_at") else reference
        lead = (parse_time(stamp)-run).total_seconds()/3600
        if not 5 <= lead <= 72:
            vector = None
        rows.append({"valid_time": stamp, "decision_time": iso(reference), "lead_time_hours": h, "model_lead_hours": lead,
                     "raw_u_kt": vector[0] if vector else None, "raw_v_kt": vector[1] if vector else None,
                     "raw_gust_kt": weather.get("wind_gust_kt") if vector else None,
                     "target_u_kt": None, "target_v_kt": None, "target_gust_kt": None,
                     "persistence_u_kt": past[0] if past else None, "persistence_v_kt": past[1] if past else None,
                     "persistence_gust_kt": persistence.get("wind_gust_kt") if persistence else None})
    active = artifact or {"models": {}, "calibrations": {}}
    with threadpool_limits(limits=2):
        candidates = values(active, rows)
        chance = {n: probabilities({"calibration": pool}, rows, candidates[n]) for n, pool in active["calibrations"].items()}
    gfs = {}
    if include_gfs:
        eligible = reference-timedelta(hours=6)
        at = eligible.replace(hour=eligible.hour//6*6, minute=0, second=0, microsecond=0)
        try:
            result = forecast(client, "gfs_global", at, forecast_days=4, availability_delay_hours=6)
            gfs = {r["valid_time"]: r for r in result["hourly"]}
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"source": "gfs_global", "error": str(exc)})
    policy = active.get("policy", {"winner": "raw_icon_eu", "weights": {"raw_icon_eu": 1.0}, "reason": error})
    initial = observed_initial(snapshot, root, reference)
    states = {n: DirectionState(initial) for n in (*CANDIDATES, "raw_gfs", "selected")}
    hours = []
    for i, row in enumerate(rows):
        stamp = row["valid_time"]
        outputs = {}
        for name in (*CANDIDATES, "raw_gfs"):
            if name == "raw_gfs":
                weather = {k: gfs.get(stamp, {}).get(k) for k in ("wind_speed_kt", "wind_from_deg_true", "wind_gust_kt")}
                prov = {k: gfs.get(stamp, {}).get(k) for k in ("model_run_at", "available_at", "availability_basis", "availability_verified", "fetched_at")}
            else:
                weather = wind_dict(candidates[name][i])
                prov = provenance.get(stamp, {}) if name != "persistence" else {
                    "observation_at": persistence.get("valid_time") if persistence else None,
                    "available_at": (persistence.get("available_at") or persistence.get("fetched_at")) if persistence else None}
            rule = states[name].step({"valid_time": stamp, **weather}, 60)
            p = chance.get(name, np.full(48, np.nan))[i]
            outputs[name] = {**weather, **rule, **prov, "source_model": "gfs_global" if name == "raw_gfs" else "observation" if name == "persistence" else "icon_eu",
                             "prediction_status": "available" if weather["wind_speed_kt"] is not None else "unavailable",
                             "selection_eligible": name in ELIGIBLE, "p_rwy18_weather_usable": float(p) if math.isfinite(p) else None,
                             "probability_status": probability_status(report, name) if math.isfinite(p) else "unavailable",
                             "reason": "unranked_additional_source" if name == "raw_gfs" else error if name != "raw_icon_eu" else None}
        winner = policy["winner"]
        effective = winner if outputs[winner]["wind_speed_kt"] is not None else "raw_icon_eu"
        selected = {**outputs[effective], "policy_winner": winner, "effective_candidate": effective,
                    "weights": policy["weights"] if effective == winner else {effective: 1.0},
                    "fallback_reason": error or ("selected_candidate_missing" if effective != winner else None)}
        selected_rule = states["selected"].step({"valid_time": stamp, **selected}, 60)
        selected.update({k: v for k, v in selected_rule.items() if not k.startswith("p_") and k != "probability_status"})
        hours.append({"valid_time": stamp, "lead_time_hours": i+1, "candidates": outputs, "selected": selected,
                      "disagreement": disagreement(outputs), "operations_ml": snapshot["forecast"][i].get("operations_ml")})
    age = (datetime.now(UTC)-parse_time(snapshot["generated_at"])).total_seconds()
    output = {"schema_version": "1.0", "model_version": MODEL_VERSION if artifact else None,
              "generated_at": iso(datetime.now(UTC)), "forecast_reference_time": iso(reference),
              "snapshot_generated_at": snapshot["generated_at"], "snapshot_age_seconds": age,
              "status": "stale_snapshot" if age > 7200 else "available" if any(h["selected"]["wind_speed_kt"] is not None for h in hours) else "unavailable",
              "experiment_id": artifact.get("experiment_id") if artifact else None, "policy": policy,
              "ruleset": RULESET, "source_checks": client.checks,
              "forecast": hours, "source_errors": errors, "model_error": error, "limitations": LIMITATIONS,
              "next_rule_direction_change": next_change([{"valid_time": h["valid_time"], **h["selected"]} for h in hours], "operating_direction", initial),
              "operations_model": snapshot.get("operations_model")}
    from .direction import enrich_comparison
    enrich_comparison(output)
    write_json(root/"comparison"/"forecast.json", output)
    return output
