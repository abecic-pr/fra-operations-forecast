"""Actual operating-direction learning requires independently sourced labels."""

from collections import defaultdict
import csv
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

from .dataset import label_at, load_labels
from .domain import UTC, FEATURE_NAMES as BASE_FEATURES, DirectionState, iso, number, parse_time, prediction_features
from .ml_data import DATA_VERSION, observation_target
from .ml_live import load_artifact
from .sources import write_json
from .wind_ml import ARTIFACT_VERSION, chronological_split, probability_metrics, save_artifact

MODEL_VERSION = "operations-v3"
RECENT_FIELDS = ["persistence_u_kt", "persistence_v_kt", "persistence_gust_kt"]
CONTEXT_FIELDS = ["forecast_along_3h_kt", "forecast_along_6h_kt"]
FEATURE_NAMES = BASE_FEATURES + RECENT_FIELDS + ["forecast_along_kt", "recent_along_decay_kt", "recent_anomaly_decay_kt", "hour_sin", "hour_cos"] + CONTEXT_FIELDS


def along(u, v):
    return u*math.sin(math.radians(70))+v*math.cos(math.radians(70))


def forecast_context(weather, reference):
    """Trailing forecast winds only; observations at target time never enter."""
    path = {}
    for point in weather:
        lead = (parse_time(point["valid_time"])-reference).total_seconds()/3600
        x = prediction_features(point, None, lead)
        if 1 <= lead <= 48 and lead.is_integer():
            path[int(lead)] = along(x[0], x[1]) if x else None
    result = {}
    for lead in path:
        values = {}
        for window, name in zip((3, 6), CONTEXT_FIELDS):
            history = [path.get(h) for h in range(max(1, lead-window+1), lead+1)]
            values[name] = sum(history)/len(history) if all(v is not None for v in history) else None
        result[iso(reference+timedelta(hours=lead))] = values
    return result


def historical_recent(row):
    at = row.get("persistence_observation_time")
    return row if at and parse_time(at) == parse_time(row["decision_time"])-timedelta(hours=1) else {}


def features(weather, initial, lead, recent=None):
    base = prediction_features(weather, initial, lead)
    if base is None:
        return None
    values = [number((recent or {}).get(k)) for k in RECENT_FIELDS]
    values = [v if v is not None else float("nan") for v in values]
    raw, observed = along(*base[:2]), along(*values[:2])
    decay = math.exp(-lead/6)
    at = parse_time(weather["valid_time"]) if weather.get("valid_time") else None
    hour = at.hour+at.minute/60 if at else float("nan")
    return base + values + [raw, observed*decay, (observed-raw)*decay,
                            math.sin(2*math.pi*hour/24), math.cos(2*math.pi*hour/24)] + [
                            number(weather.get(k)) if number(weather.get(k)) is not None else float("nan") for k in CONTEXT_FIELDS]


def recent_observation(data_dir, reference, observations=None):
    """Use the same exact one-hour-old DWD target definition as training."""
    if observations is None:
        observations = []
        for path in (Path(data_dir)/"ml"/"observations.csv", Path(data_dir)/"observations.csv"):
            if path.exists():
                with path.open(newline="") as handle:
                    observations.extend(csv.DictReader(handle))
    at = reference-timedelta(hours=1)
    index = {}
    for source in observations:
        stamp, available = source.get("valid_time"), source.get("available_at")
        if not stamp or not available or not at-timedelta(minutes=50) <= parse_time(stamp) <= at or parse_time(available) > reference:
            continue
        row = dict(source)
        for key in ("wind_speed_kt", "wind_from_deg_true", "wind_gust_kt", "gust_from_deg_true"):
            row[key] = number(row.get(key))
        index[stamp] = row
    target = observation_target(index, at)
    if target is None:
        return {}
    return {"persistence_u_kt": target["target_u_kt"], "persistence_v_kt": target["target_v_kt"],
            "persistence_gust_kt": target["target_gust_kt"], "persistence_observation_time": iso(at),
            "availability_verified": False, "availability_basis": "estimated_one_hour_dwd_delay",
            "fetched_at": index[iso(at)].get("fetched_at")}


def raw_weather(row):
    return {"valid_time": row["valid_time"], "wind_speed_kt": row.get("raw_wind_speed_kt"),
            "wind_from_deg_true": row.get("raw_wind_from_deg_true"), "wind_gust_kt": row.get("raw_gust_kt"),
            **{k: row.get(k) for k in CONTEXT_FIELDS}}


def labeled_rows(rows, labels):
    issues = defaultdict(list)
    for row in rows:
        issues[row["decision_time"]].append(raw_weather(row))
    context = {issue: forecast_context(points, parse_time(issue)) for issue, points in issues.items()}
    result = []
    for row in rows:
        if not 1 <= row["lead_time_hours"] <= 48:
            continue
        at, decision = parse_time(row["valid_time"]), parse_time(row["decision_time"])
        target = label_at(labels, at)
        if not target or target["operating_direction"] not in ("07", "25"):
            continue
        row = {**row, **context[row["decision_time"]].get(row["valid_time"], {})}
        initial = label_at(labels, decision, known_by=decision)
        direction = initial["operating_direction"] if initial else None
        if direction not in ("07", "25"):
            direction = None
        x = features(raw_weather(row), direction, row["lead_time_hours"], historical_recent(row))
        if x is not None:
            result.append({**row, "x": x, "initial_operating_direction": direction,
                           "target_operating_direction": target["operating_direction"],
                           "target_label_available_at": iso(target["available"]),
                           "target_interval_start": iso(target["start"]), "target_source": target["source"]})
    return sorted(result, key=lambda r: (r["decision_time"], r["valid_time"]))


def class_probabilities(artifact, x):
    import numpy as np
    x = np.asarray(x, dtype=float)
    x = x[:, :artifact.get("feature_count", 10 if artifact.get("uses_recent_observation") else len(BASE_FEATURES))]
    p = artifact["estimator"].predict_proba(x)[:, 1]
    if artifact.get("calibrator") is not None:
        p = np.clip(p, 1e-8, 1-1e-8)
        p = artifact["calibrator"].predict_proba(np.log(p/(1-p)).reshape(-1, 1))[:, 1]
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid operating-direction probabilities")
    return p


def predict(artifact, weather, initial, lead, recent=None):
    x = features(weather, initial, lead, recent)
    missing_recent = artifact.get("uses_recent_observation") and any(number((recent or {}).get(k)) is None for k in RECENT_FIELDS[:2])
    missing_context = artifact.get("uses_forecast_context") and any(number(weather.get(k)) is None for k in CONTEXT_FIELDS)
    if x is None or missing_recent or missing_context:
        return {"status": "unavailable", "reason": "missing_recent_dwd_observation" if missing_recent else "missing_forecast_context" if missing_context else "missing_forecast_wind", "operating_direction": None,
                "p_od07": None, "p_od25": None, "certainty_score": None}
    p = float(class_probabilities(artifact, [x])[0])
    return {"status": "available" if artifact.get("selection_gate_passed", True) else "experimental",
            "reason": None if artifact.get("selection_gate_passed", True) else "did_not_pass_selection_gate",
            "model_version": MODEL_VERSION,
            "operating_direction": "07" if p >= 0.5 else "25", "p_od07": p, "p_od25": 1-p,
            "certainty_score": max(p, 1-p), "certainty_basis": "model_class_probability",
            "probability_status": artifact["probability_status"],
            "label_quality": artifact.get("label_quality", "independent_intervals"),
            "recent_observation_time": (recent or {}).get("persistence_observation_time"),
            "initial_direction_known": initial in ("07", "25")}


def direction_scores(probabilities, actual):
    import numpy as np
    p, y = np.asarray(probabilities, dtype=float), np.asarray(actual, dtype=float)
    keep = np.isfinite(p) & np.isfinite(y)
    p, y = p[keep], y[keep]
    if not len(y):
        return {"samples": 0, "accuracy": None, "balanced_accuracy": None, "brier_score": None}
    chosen = p >= 0.5
    recalls = [float((chosen[y == c] == c).mean()) for c in (0, 1) if (y == c).any()]
    metrics = probability_metrics(p, y)
    return {"samples": len(y), "accuracy": float((chosen == y).mean()),
            "balanced_accuracy": sum(recalls)/2 if len(recalls) == 2 else None,
            "class_counts": {"07": int((y == 1).sum()), "25": int((y == 0).sum())},
            "brier_score": metrics["brier_score"], "reliability": metrics["reliability"]}


def change_scores(decisions, labels, horizon):
    from .pipeline import next_change
    if any(r.get("label_kind") == "point" for r in labels):
        return {"status": "unavailable", "reason": "point_labels_do_not_establish_exact_switch_times",
                "candidates": {name: {"issue_cases": 0, "excluded_issues": len(decisions), "mae_minutes": None}
                               for name in ("model", "challenge_rules")}}
    scores = {name: {"issue_cases": 0, "excluded_issues": 0, "matched_changes": 0,
                     "missed_changes": 0, "false_changes": 0, "window_hits": 0, "errors": []}
              for name in ("model", "challenge_rules")}
    for issue, points in decisions.items():
        start = parse_time(issue)
        end = start + timedelta(hours=horizon)
        initial = label_at(labels, start, known_by=start)
        actual, cursor = None, start
        direction = initial["operating_direction"] if initial else None
        complete = direction in ("07", "25")
        for label in labels:
            if label["end"] <= start or label["start"] > end:
                continue
            if label["start"] > cursor or label["operating_direction"] not in ("07", "25"):
                complete = False
                break
            if label["operating_direction"] != direction and actual is None:
                actual = label["start"]
            direction = label["operating_direction"]
            cursor = max(cursor, label["end"])
            if cursor > end:
                break
        complete = complete and cursor > end
        subset = [p for p in points if parse_time(p["valid_time"]) <= end]
        grid = [iso(start+timedelta(hours=h)) for h in range(1, horizon+1)]
        for name, score in scores.items():
            if (not complete or [p["valid_time"] for p in subset] != grid
                    or any(p[name] is None for p in subset)):
                score["excluded_issues"] += 1
                continue
            score["issue_cases"] += 1
            change = next_change(subset, name, initial["operating_direction"])
            expected = parse_time(change["latest"]) if change["status"] == "change_expected" else None
            if actual and expected:
                score["matched_changes"] += 1
                score["errors"].append((expected-actual).total_seconds()/60)
                earliest = parse_time(change["earliest"]) if change["earliest"] else start
                score["window_hits"] += int(earliest < actual <= expected)
            score["missed_changes"] += int(actual is not None and expected is None)
            score["false_changes"] += int(actual is None and expected is not None)
    for score in scores.values():
        errors = score.pop("errors")
        score["mae_minutes"] = sum(abs(e) for e in errors)/len(errors) if errors else None
        score["mean_signed_error_minutes"] = sum(errors)/len(errors) if errors else None
        score["window_hit_rate"] = score["window_hits"]/len(errors) if errors else None
    return {"candidates": scores, "matching_rule": "First predicted switch versus first independent interval boundary; complete truth and known starting state required."}


def evaluate(rows, artifact, timeline=None, labels=()):
    import numpy as np
    predicted = class_probabilities(artifact, [r["x"] for r in rows])
    if artifact.get("uses_recent_observation"):
        predicted[[any(number(r["x"][i]) is None for i in (7, 8)) for r in rows]] = np.nan
    if artifact.get("uses_forecast_context"):
        predicted[[any(number(r["x"][i]) is None for i in (15, 16)) for r in rows]] = np.nan
    by_time = {(r["decision_time"], r["valid_time"]): "07" if p >= .5 else "25" if np.isfinite(p) else None for r, p in zip(rows, predicted)}
    truth = np.asarray([r["target_operating_direction"] == "07" for r in rows], dtype=float)
    decisions = defaultdict(list)
    initials = {r["decision_time"]: r["initial_operating_direction"] for r in rows}
    last_target = max(r["valid_time"] for r in rows)
    baseline_by_time = {}
    state, previous = None, None
    # Labels filter scoring cases, never the weather timeline used by persistence rules.
    for row in sorted(timeline if timeline is not None else rows, key=lambda r: (r["decision_time"], r["valid_time"])):
        issue = row["decision_time"]
        if issue not in initials or not 1 <= row["lead_time_hours"] <= 48 or row["valid_time"] > last_target:
            continue
        if issue != previous:
            state, previous = DirectionState(initials[issue]), issue
        weather = raw_weather(row)
        direction = state.step(weather, 60)["operating_direction"]
        baseline_by_time[(issue, row["valid_time"])] = float(direction == "07") if direction else float("nan")
        decisions[issue].append({"valid_time": row["valid_time"], "model": by_time.get((issue, row["valid_time"])), "challenge_rules": direction})
    baseline = [baseline_by_time[(r["decision_time"], r["valid_time"])] for r in rows]
    persistence = [float(r["initial_operating_direction"] == "07") if r["initial_operating_direction"] else float("nan") for r in rows]
    baseline, persistence = np.asarray(baseline), np.asarray(persistence)
    scores = {}
    for horizon in ("all_1_to_48h", 1, 6, 24, 48):
        mask = np.asarray([horizon == "all_1_to_48h" or r["lead_time_hours"] == horizon for r in rows])
        common = mask & np.isfinite(baseline) & np.isfinite(predicted)
        persist = common & np.isfinite(persistence)
        scores[str(horizon)] = {
            "model": direction_scores(predicted[common], truth[common]),
            "challenge_rules": direction_scores(baseline[common], truth[common]),
            "persistence": direction_scores(persistence[persist], truth[persist]),
            "model_on_persistence_cohort": direction_scores(predicted[persist], truth[persist]),
            "unscored_baseline_rows": int((mask & ~np.isfinite(baseline)).sum()),
            "unscored_model_rows": int((mask & ~np.isfinite(predicted)).sum()),
            "unique_valid_times": len({r["valid_time"] for r, k in zip(rows, common) if k})}
    return {"horizons": scores, "next_change": {str(h): change_scores(decisions, labels, h) for h in (1, 6, 24, 48)}}


def selection_check(scores):
    """Require accuracy gains without sacrificing class balance or Brier."""
    a, b = (scores["horizons"]["all_1_to_48h"][k] for k in ("model", "challenge_rules"))
    return (a["brier_score"] is not None and b["brier_score"] is not None
            and a["brier_score"] < b["brier_score"] and a["accuracy"] >= b["accuracy"]
            and a["balanced_accuracy"] is not None and b["balanced_accuracy"] is not None
            and a["balanced_accuracy"] >= b["balanced_accuracy"])


def train(data_dir="data", labels_path=None, progress=print):
    import numpy as np
    import sklearn
    from sklearn.base import clone
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import VotingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    root = Path(data_dir)
    labels = load_labels(labels_path)
    report = {"model_version": MODEL_VERSION, "trained_at": iso(datetime.now(UTC)),
              "status": "unavailable", "reason": "missing_independent_labels", "metrics": None}
    if not labels:
        write_json(root/"operations-evaluation.json", report)
        return report
    raw = (root/"ml"/"dataset.json").read_bytes()
    dataset = json.loads(raw)
    if dataset.get("data_version") != DATA_VERSION:
        raise ValueError("Unsupported wind dataset version")
    rows = labeled_rows(dataset["rows"], labels)
    report.update(label_intervals=len(labels), labeled_rows=len(rows), label_sources=sorted({r["source"] for r in labels}))
    try:
        full_groups, split = chronological_split(dataset["rows"])
        groups = {name: labeled_rows(part, labels) for name, part in full_groups.items()}
        if any(len(part) < 100 for part in groups.values()):
            raise ValueError("Need at least 100 labeled cases in every fixed chronological partition")
        y = [int(r["target_operating_direction"] == "07") for r in groups["train"]]
        if len(set(y)) < 2 or min(y.count(0), y.count(1)) < 20:
            raise ValueError("Need at least 20 training rows in each independent OD class")
    except ValueError as exc:
        report["reason"] = f"insufficient_independent_labels: {exc}"
        write_json(root/"operations-evaluation.json", report)
        return report
    label_hash = hashlib.sha256(Path(labels_path).read_bytes()).hexdigest()
    experiment = hashlib.sha256(raw + label_hash.encode() + MODEL_VERSION.encode() + json.dumps(FEATURE_NAMES).encode()).hexdigest()[:20]
    artifact = {"model_version": MODEL_VERSION, "artifact_version": ARTIFACT_VERSION, "features": FEATURE_NAMES,
                "sklearn_version": sklearn.__version__, "calibrator": None,
                "experiment_id": experiment, "probability_status": "uncalibrated_model_probability"}
    quality = sorted({r.get("label_quality") or "independent_intervals" for r in labels})
    artifact["label_quality"] = ",".join(quality)
    days = sorted({r["decision_time"][:10] for r in groups["train"]})
    inner_boundary = days[int(.8*len(days))]+"T00:00:00Z"
    inner_train = [r for r in groups["train"] if r["valid_time"] < inner_boundary]
    inner_check = [r for r in groups["train"] if r["decision_time"] >= inner_boundary]
    if len({r["target_operating_direction"] for r in inner_train}) < 2:
        report["reason"] = "insufficient_independent_labels: both OD classes required before inner-validation boundary"
        write_json(root/"operations-evaluation.json", report)
        return report
    def logistic():
        return make_pipeline(SimpleImputer(keep_empty_features=True), StandardScaler(),
                             LogisticRegression(C=1, class_weight="balanced", max_iter=500, random_state=42))
    blend = VotingClassifier([("recent", make_pipeline(ColumnTransformer([("recent", "passthrough", list(range(10)))]), logistic())),
                              ("trajectory", logistic())], voting="soft", weights=[1, 1], n_jobs=1)
    candidates = []
    for name, count, estimator in (("balanced_logistic", 7, logistic()),
                                    ("recent_balanced_logistic", 10, logistic()),
                                    ("trajectory_logistic", 17, logistic()),
                                    ("equal_recent_trajectory_logistic", 17, blend)):
        artifact.update(uses_recent_observation=count > 7, uses_forecast_context=count > 10, feature_count=count)
        required = (7, 8, 15, 16) if count > 10 else (7, 8) if count > 7 else ()
        if any(number(r["x"][i]) is None for p in ("train", "selection") for r in groups[p] for i in required):
            continue
        check_model = clone(estimator).fit([r["x"][:count] for r in inner_train], [int(r["target_operating_direction"] == "07") for r in inner_train])
        artifact["estimator"] = check_model
        inner_scores = evaluate(inner_check, artifact, dataset["rows"], labels)
        estimator.fit([r["x"][:count] for r in groups["train"]], y)
        artifact["estimator"] = estimator
        selection = evaluate(groups["selection"], artifact, dataset["rows"], labels)
        passes = selection_check(selection) and selection_check(inner_scores) and all(
            selection["horizons"][str(h)]["model"]["accuracy"] is not None
            and selection["horizons"][str(h)]["model"]["accuracy"] >= selection["horizons"][str(h)]["challenge_rules"]["accuracy"] for h in (1, 6, 24))
        gain = min(s["horizons"]["all_1_to_48h"]["model"]["accuracy"]-s["horizons"]["all_1_to_48h"]["challenge_rules"]["accuracy"] for s in (selection, inner_scores))
        candidates.append((passes, gain, name, estimator, selection, inner_scores, count))
    chosen = max(candidates, key=lambda c: (c[0], c[1]))
    passes, _, selected_name, estimator, selection, inner_scores, count = chosen
    artifact["estimator"] = estimator
    artifact.update(uses_recent_observation=count > 7, uses_forecast_context=count > 10, feature_count=count)
    artifact["selection_gate_passed"] = passes
    cal = groups["calibration"]
    days = sorted({r["decision_time"][:10] for r in cal})
    boundary = days[len(days)//2]+"T00:00:00Z"
    cal_fit = [r for r in cal if r["valid_time"] < boundary]
    cal_check = [r for r in cal if r["decision_time"] >= boundary]
    cy = [int(r["target_operating_direction"] == "07") for r in cal_fit]
    calibration_gate = {"accepted": False, "reason": "insufficient_independent_calibration_coverage",
                        "fit_rows": len(cal_fit), "check_rows": len(cal_check), "boundary": boundary}
    check_y = [int(r["target_operating_direction"] == "07") for r in cal_check]
    if min(cy.count(0), cy.count(1)) >= 20 and min(check_y.count(0), check_y.count(1)) >= 20 and len({r["decision_time"][:10] for r in cal_fit}) >= 5:
        calibrator = LogisticRegression(C=1.0, max_iter=500, random_state=42)
        fit_p = np.clip(class_probabilities(artifact, [r["x"] for r in cal_fit]), 1e-8, 1-1e-8)
        check_p = np.clip(class_probabilities(artifact, [r["x"] for r in cal_check]), 1e-8, 1-1e-8)
        calibrator.fit(np.log(fit_p/(1-fit_p)).reshape(-1, 1), cy)
        raw_score = direction_scores(check_p, check_y)
        candidate_score = direction_scores(calibrator.predict_proba(np.log(check_p/(1-check_p)).reshape(-1, 1))[:, 1], check_y)
        accepted = (candidate_score["brier_score"] < raw_score["brier_score"]
                    and candidate_score["balanced_accuracy"] is not None and raw_score["balanced_accuracy"] is not None
                    and candidate_score["balanced_accuracy"] >= raw_score["balanced_accuracy"])
        calibration_gate.update(accepted=accepted, reason="independent_calibration_check", raw=raw_score, calibrated=candidate_score)
        if accepted:
            artifact["calibrator"] = calibrator
            artifact["probability_status"] = "provisional_sigmoid_calibration"
    used = groups["train"] + groups["selection"] + groups["calibration"]
    cutoff = max(max(r["valid_time"], r["target_label_available_at"]) for r in used)
    artifact["data_cutoff"] = cutoff
    report.update(status="trained", reason=None, experiment_id=experiment, features=FEATURE_NAMES,
                  selected_candidate=selected_name, calibration_gate=calibration_gate,
                  uses_recent_observation=artifact["uses_recent_observation"],
                  uses_forecast_context=artifact["uses_forecast_context"],
                  inner_validation={"boundary": inner_boundary, "scores": inner_scores},
                  selection_candidates=[{"candidate": c[2], "passes_gate": c[0], "worst_split_accuracy_gain": c[1], "metrics": c[4]["horizons"]["all_1_to_48h"]["model"]} for c in candidates],
                  label_quality=quality,
                  label_kinds=sorted({r.get("label_kind") or "interval" for r in labels}),
                  target_definition="Source-derived stable half-hour display proxy at hourly timestamps" if any(r.get("label_kind") == "point" for r in labels) else "Independent actual operating-direction intervals",
                  label_limitations=["Display proxies exclude ambiguous transitions; metrics do not prove accuracy on all actual operations.",
                                     "Exact switch times and historical initial OD remain unverified."] if any(r.get("label_kind") == "point" for r in labels) else [],
                  sklearn_version=sklearn.__version__, labels_sha256=label_hash,
                  dataset_sha256=hashlib.sha256(raw).hexdigest(), split=split, data_cutoff=cutoff,
                  partitions={k: {"rows": len(v), "first_issue": v[0]["decision_time"], "last_issue": v[-1]["decision_time"]} for k, v in groups.items()},
                  selection=selection, selection_gate={"passes": passes, "metric": "accuracy_balanced_accuracy_and_brier_on_two_purged_splits; required_lead_accuracy_noninferior_on_selection",
                                                       "use": "eligible_with_provisional_labels" if passes else "experimental_only"},
                  test=evaluate(groups["test"], artifact, dataset["rows"], labels),
                  test_status="exploratory_reused_test", probability_status=artifact["probability_status"],
                  historical_availability_verified=False)
    scores = report["test"]["horizons"]["all_1_to_48h"]
    a, b = scores["model"]["brier_score"], scores["challenge_rules"]["brier_score"]
    report["lower_test_brier_than_rules"] = a < b if a is not None and b is not None else None
    save_artifact(root, artifact, report)
    write_json(root/"operations-evaluation.json", report)
    progress(f"Saved OD model trained on independent labels; test status: {report['test_status']}", flush=True)
    return report


def enrich(snapshot, data_dir, enabled=True, observations=None):
    from .pipeline import next_change
    artifact, report, error = load_artifact(data_dir, MODEL_VERSION, FEATURE_NAMES) if enabled else (None, None, "ml_disabled")
    reference = parse_time(snapshot["forecast_reference_time"])
    if artifact:
        try:
            if parse_time(artifact["data_cutoff"]) >= reference:
                artifact, error = None, "model_data_not_before_reference"
        except (KeyError, ValueError, TypeError):
            artifact, error = None, "model_artifact_incompatible"
    from .comparison import observed_initial
    initial = observed_initial(snapshot, data_dir, reference)
    recent = recent_observation(data_dir, reference, observations)
    weather = [{"valid_time": p["valid_time"], "wind_speed_kt": p.get("ml", {}).get("raw_wind_speed_kt"),
                "wind_from_deg_true": p.get("ml", {}).get("raw_wind_from_deg_true"),
                "wind_gust_kt": p.get("ml", {}).get("raw_wind_gust_kt")} for p in snapshot["forecast"]]
    context = forecast_context(weather, reference)
    for point, raw in zip(snapshot["forecast"], weather):
        result = {"status": "unavailable", "reason": error or "explicit_icon_eu_input_missing",
                  "operating_direction": None, "p_od07": None, "p_od25": None, "certainty_score": None}
        ml = point.get("ml", {})
        if artifact and ml.get("source_model") == "icon_eu" and ml.get("raw_wind_speed_kt") is not None:
            try:
                result = predict(artifact, {**raw, **context.get(point["valid_time"], {})}, initial, (parse_time(point["valid_time"])-reference).total_seconds()/3600, recent)
            except (ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
                result["reason"] = f"od_inference_unavailable: {exc}"
        point["operations_ml"] = result
    timeline = [{"valid_time": p["valid_time"], "direction": p["operations_ml"]["operating_direction"] if p["operations_ml"]["status"] == "available" else None} for p in snapshot["forecast"]]
    change = next_change(timeline, "direction", initial)
    change["method"] = "predicted_hourly_class_change"
    if change["status"] == "change_expected" and change["earliest"] is None and initial:
        change["earliest"] = iso(reference)
    available_hours = sum(p["operations_ml"]["status"] == "available" for p in snapshot["forecast"])
    snapshot["operations_model"] = {"status": "available" if available_hours == len(snapshot["forecast"]) else "partial" if available_hours else "unavailable", "reason": error,
                                    "forecast_hours_available": available_hours,
                                    "model_version": MODEL_VERSION, "next_change": change,
                                    "label_quality": artifact.get("label_quality") if artifact else None,
                                    "recent_observation": recent,
                                    "uses_forecast_context": artifact.get("uses_forecast_context") if artifact else None,
                                    "selection_gate_passed": artifact.get("selection_gate_passed") if artifact else None,
                                    "metrics_url": "/api/operations-metrics"}
    if "ml_model" in snapshot:
        snapshot["ml_model"]["operating_direction_status"] = snapshot["operations_model"]["status"]
    return snapshot
