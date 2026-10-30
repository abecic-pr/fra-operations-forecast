"""Actual operating-direction learning requires independently sourced labels."""

from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

from .dataset import label_at, load_labels
from .domain import UTC, FEATURE_NAMES, DirectionState, iso, parse_time, prediction_features
from .ml_data import DATA_VERSION
from .ml_live import load_artifact
from .sources import write_json
from .wind_ml import ARTIFACT_VERSION, chronological_split, probability_metrics, save_artifact

MODEL_VERSION = "operations-logistic-v1"


def raw_weather(row):
    return {"valid_time": row["valid_time"], "wind_speed_kt": row.get("raw_wind_speed_kt"),
            "wind_from_deg_true": row.get("raw_wind_from_deg_true"), "wind_gust_kt": row.get("raw_gust_kt")}


def labeled_rows(rows, labels):
    result = []
    for row in rows:
        if not 1 <= row["lead_time_hours"] <= 48:
            continue
        at, decision = parse_time(row["valid_time"]), parse_time(row["decision_time"])
        target = label_at(labels, at)
        if not target or target["operating_direction"] not in ("07", "25"):
            continue
        initial = label_at(labels, decision, known_by=decision)
        direction = initial["operating_direction"] if initial else None
        if direction not in ("07", "25"):
            direction = None
        x = prediction_features(raw_weather(row), direction, row["lead_time_hours"])
        if x is not None:
            result.append({**row, "x": x, "initial_operating_direction": direction,
                           "target_operating_direction": target["operating_direction"],
                           "target_label_available_at": iso(target["available"]),
                           "target_interval_start": iso(target["start"]), "target_source": target["source"]})
    return sorted(result, key=lambda r: (r["decision_time"], r["valid_time"]))


def class_probabilities(artifact, x):
    import numpy as np
    if artifact.get("calibrator") is not None:
        score = artifact["estimator"].decision_function(x)
        p = artifact["calibrator"].predict_proba(np.asarray(score).reshape(-1, 1))[:, 1]
    else:
        p = artifact["estimator"].predict_proba(x)[:, 1]
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid operating-direction probabilities")
    return p


def predict(artifact, weather, initial, lead):
    x = prediction_features(weather, initial, lead)
    if x is None:
        return {"status": "unavailable", "reason": "missing_forecast_wind", "operating_direction": None,
                "p_od07": None, "p_od25": None, "certainty_score": None}
    p = float(class_probabilities(artifact, [x])[0])
    return {"status": "available", "model_version": MODEL_VERSION,
            "operating_direction": "07" if p >= 0.5 else "25", "p_od07": p, "p_od25": 1-p,
            "certainty_score": max(p, 1-p), "certainty_basis": "model_class_probability",
            "probability_status": artifact["probability_status"],
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
        model = predict(artifact, weather, initials[issue], row["lead_time_hours"])
        decisions[issue].append({"valid_time": row["valid_time"], "model": model["operating_direction"], "challenge_rules": direction})
    baseline = [baseline_by_time[(r["decision_time"], r["valid_time"])] for r in rows]
    persistence = [float(r["initial_operating_direction"] == "07") if r["initial_operating_direction"] else float("nan") for r in rows]
    baseline, persistence = np.asarray(baseline), np.asarray(persistence)
    scores = {}
    for horizon in ("all_1_to_48h", 1, 6, 24, 48):
        mask = np.asarray([horizon == "all_1_to_48h" or r["lead_time_hours"] == horizon for r in rows])
        common = mask & np.isfinite(baseline)
        persist = common & np.isfinite(persistence)
        scores[str(horizon)] = {
            "model": direction_scores(predicted[common], truth[common]),
            "challenge_rules": direction_scores(baseline[common], truth[common]),
            "persistence": direction_scores(persistence[persist], truth[persist]),
            "model_on_persistence_cohort": direction_scores(predicted[persist], truth[persist]),
            "unscored_baseline_rows": int((mask & ~np.isfinite(baseline)).sum()),
            "unique_valid_times": len({r["valid_time"] for r, k in zip(rows, common) if k})}
    return {"horizons": scores, "next_change": {str(h): change_scores(decisions, labels, h) for h in (1, 6, 24, 48)}}


def train(data_dir="data", labels_path=None, progress=print):
    import numpy as np
    import sklearn
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
        groups, split = chronological_split(rows)
        y = [int(r["target_operating_direction"] == "07") for r in groups["train"]]
        if len(set(y)) < 2 or min(y.count(0), y.count(1)) < 20:
            raise ValueError("Need at least 20 training rows in each independent OD class")
    except ValueError as exc:
        report["reason"] = f"insufficient_independent_labels: {exc}"
        write_json(root/"operations-evaluation.json", report)
        return report
    estimator = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=42))
    estimator.fit([r["x"] for r in groups["train"]], y)
    label_hash = hashlib.sha256(Path(labels_path).read_bytes()).hexdigest()
    experiment = hashlib.sha256(raw + label_hash.encode() + MODEL_VERSION.encode()).hexdigest()[:20]
    artifact = {"model_version": MODEL_VERSION, "artifact_version": ARTIFACT_VERSION, "features": FEATURE_NAMES,
                "sklearn_version": sklearn.__version__, "estimator": estimator, "calibrator": None,
                "experiment_id": experiment, "probability_status": "uncalibrated_model_probability"}
    selection = evaluate(groups["selection"], artifact, dataset["rows"], labels)
    candidate, baseline = (selection["horizons"]["all_1_to_48h"][k] for k in ("model", "challenge_rules"))
    passes = (candidate["brier_score"] is not None and baseline["brier_score"] is not None
              and candidate["brier_score"] < baseline["brier_score"]
              and candidate["balanced_accuracy"] is not None and baseline["balanced_accuracy"] is not None
              and candidate["balanced_accuracy"] >= baseline["balanced_accuracy"])
    cal = groups["calibration"]
    cy = [int(r["target_operating_direction"] == "07") for r in cal]
    if min(cy.count(0), cy.count(1)) >= 20 and len({r["decision_time"][:10] for r in cal}) >= 5:
        calibrator = LogisticRegression(C=1.0, max_iter=500, random_state=42)
        calibrator.fit(estimator.decision_function([r["x"] for r in cal]).reshape(-1, 1), cy)
        artifact["calibrator"] = calibrator
        artifact["probability_status"] = "provisional_sigmoid_calibration"
    used = groups["train"] + groups["selection"] + groups["calibration"]
    cutoff = max(max(r["valid_time"], r["target_label_available_at"]) for r in used)
    artifact["data_cutoff"] = cutoff
    report.update(status="trained", reason=None, experiment_id=experiment, features=FEATURE_NAMES,
                  sklearn_version=sklearn.__version__, labels_sha256=label_hash,
                  dataset_sha256=hashlib.sha256(raw).hexdigest(), split=split, data_cutoff=cutoff,
                  partitions={k: {"rows": len(v), "first_issue": v[0]["decision_time"], "last_issue": v[-1]["decision_time"]} for k, v in groups.items()},
                  selection=selection, selection_gate={"passes": passes, "metric": "lower_brier_and_no_worse_balanced_accuracy",
                                                       "use": "experimental_model; baseline remains separately available"},
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


def enrich(snapshot, data_dir, enabled=True):
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
    for point in snapshot["forecast"]:
        result = {"status": "unavailable", "reason": error or "explicit_icon_eu_input_missing",
                  "operating_direction": None, "p_od07": None, "p_od25": None, "certainty_score": None}
        ml = point.get("ml", {})
        if artifact and ml.get("source_model") == "icon_eu" and ml.get("raw_wind_speed_kt") is not None:
            try:
                weather = {"wind_speed_kt": ml["raw_wind_speed_kt"], "wind_from_deg_true": ml.get("raw_wind_from_deg_true"),
                           "wind_gust_kt": ml.get("raw_wind_gust_kt")}
                result = predict(artifact, weather, initial, (parse_time(point["valid_time"])-reference).total_seconds()/3600)
            except (ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
                result["reason"] = f"od_inference_unavailable: {exc}"
        point["operations_ml"] = result
    timeline = [{"valid_time": p["valid_time"], "direction": p["operations_ml"]["operating_direction"]} for p in snapshot["forecast"]]
    change = next_change(timeline, "direction", initial)
    change["method"] = "predicted_hourly_class_change"
    if change["status"] == "change_expected" and change["earliest"] is None and initial:
        change["earliest"] = iso(reference)
    snapshot["operations_model"] = {"status": "available" if artifact else "unavailable", "reason": error,
                                    "model_version": MODEL_VERSION, "next_change": change,
                                    "metrics_url": "/api/operations-metrics"}
    return snapshot
