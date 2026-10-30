"""Small ICON-EU residual model, chronological evaluation and weather uncertainty."""

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

from .domain import UTC, iso, parse_time
from .ml_data import DATA_VERSION, uv
from .sources import write_json

ARTIFACT_VERSION = 1
MODEL_VERSION = "icon-eu-wind-v1"
FEATURES = ["raw_u_kt", "raw_v_kt", "raw_gust_kt", "model_lead_hours",
            "hour_sin", "hour_cos", "year_sin", "year_cos", "gust_missing"]
BANDS = ((5,12),(13,24),(25,48),(49,72))
SAMPLES = 256
PARAMETERS = dict(max_iter=120, max_leaf_nodes=15, learning_rate=0.05,
                  min_samples_leaf=30, l2_regularization=1.0,
                  early_stopping=False, random_state=42)


def features(row):
    at = parse_time(row["valid_time"])
    hour = at.hour + at.minute/60
    year = (at.timetuple().tm_yday-1+hour/24)/365.25
    gust = row.get("raw_gust_kt")
    return [row["raw_u_kt"], row["raw_v_kt"], gust if gust is not None else float("nan"),
            row["model_lead_hours"], math.sin(2*math.pi*hour/24), math.cos(2*math.pi*hour/24),
            math.sin(2*math.pi*year), math.cos(2*math.pi*year), float(gust is None)]


def chronological_split(rows):
    days = sorted({row["decision_time"][:10] for row in rows})
    if len(days) < 30:
        raise ValueError("At least 30 issue dates are required for a chronological split")
    # The middle 20% is divided into selection and independent calibration.
    boundaries = [days[int(len(days)*fraction)]+"T00:00:00Z" for fraction in (0.6,0.7,0.8)]
    groups = {name: [] for name in ("train","selection","calibration","test")}
    purged = 0
    for row in rows:
        decision = parse_time(row["decision_time"])
        valid = parse_time(row["valid_time"])
        available = parse_time(row["forecast_available_at"])
        if available > decision or valid <= decision:
            raise ValueError("Input availability/target time violates the forecasting boundary")
        part = sum(row["decision_time"] >= boundary for boundary in boundaries)
        if part < 3 and row["valid_time"] >= boundaries[part]:
            purged += 1
            continue
        groups[list(groups)[part]].append(row)
    if any(len(group) < 100 for group in groups.values()):
        raise ValueError("Insufficient data in a purged chronological partition")
    return groups, {"boundaries": boundaries, "purged_rows": purged,
                    "rule": "Every target in an earlier partition precedes the next partition's first issue date."}


def matrices(rows):
    import numpy as np
    x = np.asarray([features(r) for r in rows], dtype=float)
    raw = np.asarray([[r["raw_u_kt"],r["raw_v_kt"],r.get("raw_gust_kt")] for r in rows],dtype=float)
    actual = np.asarray([[r["target_u_kt"],r["target_v_kt"],r.get("target_gust_kt")] for r in rows],dtype=float)
    return x, raw, actual


def corrected(artifact, x, raw, candidate=False):
    import numpy as np
    result = raw.copy()
    enabled = {"wind":True,"gust":True} if candidate else artifact["selected"]
    for column, name in enumerate(("u","v","gust")):
        if enabled["gust" if name == "gust" else "wind"] and artifact["estimators"].get(name) is not None:
            mask = np.isfinite(raw[:,column])
            if mask.any():
                result[mask,column] += artifact["estimators"][name].predict(x[mask])
    # Enforce the same physical bound on deployed predictions and evaluation.
    if any(enabled.values()):
        speed = np.hypot(result[:,0], result[:,1])
        result[:,2] = np.where(np.isfinite(result[:,2]), np.maximum(speed,result[:,2]),np.nan)
    return result


def weather_outcome(values, gust_directions=None):
    """RWY18 headwind is v, crosswind is |u|, with true heading 180 degrees."""
    import numpy as np
    speed = np.hypot(values[:,0], values[:,1])
    tail = np.maximum(0,-values[:,1])
    with np.errstate(invalid="ignore",divide="ignore"):
        gust_cross = values[:,2]*np.abs(values[:,0])/speed
    gust_cross = np.where((speed == 0)&(values[:,2] == 0),0,gust_cross)
    if gust_directions is not None:
        directions = np.asarray(gust_directions,dtype=float)
        gust_cross = np.where(np.isfinite(directions),
                              np.abs(values[:,2]*np.sin(np.radians(directions-180))),gust_cross)
    known_bad = (tail >= 15)|(np.abs(values[:,0]) > 40)|(gust_cross > 40)
    known = np.isfinite(values).all(axis=1)&np.isfinite(gust_cross)
    return np.where(known_bad,0.0,np.where(known,1.0,np.nan))


def regression_metrics(predicted, actual):
    import numpy as np
    valid = np.isfinite(predicted[:,:2]).all(axis=1)&np.isfinite(actual[:,:2]).all(axis=1)
    speed = np.hypot(predicted[:,0],predicted[:,1])
    observed = np.hypot(actual[:,0],actual[:,1])
    gusts = np.isfinite(predicted[:,2])&np.isfinite(actual[:,2])
    eligible = valid&(observed >= 3)
    angles = eligible&(speed >= 0.5)
    delta = (np.degrees(np.arctan2(-predicted[:,0],-predicted[:,1]))-
             np.degrees(np.arctan2(-actual[:,0],-actual[:,1]))+180)%360-180
    return {"samples": int(valid.sum()),
            "unique_target_definition": "10-minute wind ending at valid_time; preceding-hour maximum gust",
            "speed_mae_kt": float(np.abs(speed[valid]-observed[valid]).mean()) if valid.any() else None,
            "vector_rmse_kt": float(np.sqrt(((predicted[valid,:2]-actual[valid,:2])**2).sum(axis=1).mean())) if valid.any() else None,
            "gust_mae_kt": float(np.abs(predicted[gusts,2]-actual[gusts,2]).mean()) if gusts.any() else None,
            "gust_samples": int(gusts.sum()),
            "direction_mae_deg": float(np.abs(delta[angles]).mean()) if angles.any() else None,
            "direction_samples": int(angles.sum()), "direction_eligible_samples": int(eligible.sum()),
            "direction_coverage": float(angles.sum()/eligible.sum()) if eligible.any() else None,
            "direction_calm_exclusion_kt": 3.0}


def probability_metrics(probabilities, actual):
    import numpy as np
    probabilities = np.asarray(probabilities,dtype=float)
    actual = np.asarray(actual,dtype=float)
    valid = np.isfinite(probabilities)&np.isfinite(actual)
    p,y = probabilities[valid],actual[valid]
    bins = []
    for low in range(10):
        subset = (p >= low/10)&(p <= 1 if low == 9 else p < (low+1)/10)
        bins.append({"lower":low/10,"upper":(low+1)/10,"samples":int(subset.sum()),
                     "mean_probability":float(p[subset].mean()) if subset.any() else None,
                     "observed_frequency":float(y[subset].mean()) if subset.any() else None})
    brier = float(((p-y)**2).mean()) if len(p) else None
    constant = float(((1-y)**2).mean()) if len(p) else None
    return {"samples":len(p),"brier_score":brier,
            "always_usable_brier_score":constant,
            "skill_vs_always_usable":1-brier/constant if constant is not None and constant > 0 else None,
            "adverse_weather_samples":int((y == 0).sum()),"reliability":bins,
            "calibration_claim":"provisional_not_guaranteed_calibrated"}


def band_for(lead):
    return next((f"{low}-{high}" for low,high in BANDS if low <= lead <= high),None)


def probabilities(artifact, rows, predicted):
    import numpy as np
    output = np.full(len(rows),np.nan)
    rng = np.random.default_rng(42)
    for i,row in enumerate(rows):
        pool = artifact.get("calibration",{}).get(band_for(row["model_lead_hours"]))
        if pool is None or len(pool) < 100 or not np.isfinite(predicted[i]).all():
            continue
        draws = predicted[i]+pool[rng.integers(0,len(pool),SAMPLES)]
        draws[:,2] = np.maximum(np.hypot(draws[:,0],draws[:,1]),draws[:,2])
        outcomes = weather_outcome(draws)
        if np.isfinite(outcomes).all():
            output[i] = outcomes.mean()
    return output


def evaluate(rows, artifact):
    import numpy as np
    x, raw, actual = matrices(rows)
    deployed = corrected(artifact,x,raw)
    persistence = np.asarray([[r.get("persistence_u_kt"),r.get("persistence_v_kt"),r.get("persistence_gust_kt")] for r in rows],dtype=float)
    chance = probabilities(artifact,rows,deployed)
    truth = weather_outcome(actual,[r.get("target_gust_from_deg_true") for r in rows])
    groups = {"all_1_to_48h":np.asarray([1 <= r["lead_time_hours"] <= 48 for r in rows])}
    groups.update({str(h):np.asarray([r["lead_time_hours"] == h for r in rows]) for h in (1,6,24,48)})
    result = {name:{"raw_icon_eu":regression_metrics(raw[mask],actual[mask]),
                  "selected_forecast":regression_metrics(deployed[mask],actual[mask]),
                  "persistence":regression_metrics(persistence[mask],actual[mask]),
                  "rwy18_weather_probability":probability_metrics(chance[mask],truth[mask]),
                  "unique_valid_times":len({r["valid_time"] for r,m in zip(rows,mask) if m})}
            for name,mask in groups.items()}
    for name,mask in groups.items():
        adverse = {r["valid_time"] for r,m,y in zip(rows,mask,truth) if m and y == 0}
        tailwind = {r["valid_time"] for r,m in zip(rows,mask) if m and -r["target_v_kt"] >= 15}
        crosswind = {r["valid_time"] for r,m in zip(rows,mask) if m and (
            abs(r["target_u_kt"]) > 40 or (r.get("target_gust_kt") is not None and
            r.get("target_gust_from_deg_true") is not None and
            abs(r["target_gust_kt"]*math.sin(math.radians(r["target_gust_from_deg_true"]-180))) > 40))}
        result[name]["rwy18_weather_probability"].update({
            "unique_adverse_valid_times":len(adverse),
            "adverse_weather_dates":len({at[:10] for at in adverse}),
            "unique_tailwind_limit_valid_times":len(tailwind),
            "unique_crosswind_limit_valid_times":len(crosswind)})
    return result


def train(data_dir="data", progress=print):
    import joblib
    import numpy as np
    import sklearn
    from sklearn.ensemble import HistGradientBoostingRegressor
    from threadpoolctl import threadpool_limits

    root = Path(data_dir)
    dataset_path = root/"ml"/"dataset.json"
    raw_bytes = dataset_path.read_bytes()
    dataset = json.loads(raw_bytes)
    if dataset.get("data_version") != DATA_VERSION:
        raise ValueError("Unsupported ML dataset version; rerun prepare-ml")
    groups, split = chronological_split(dataset["rows"])
    progress(f"Purged chronological partitions: { {k:len(v) for k,v in groups.items()} }",flush=True)
    x, raw, actual = matrices(groups["train"])
    artifact = {"artifact_version":ARTIFACT_VERSION,"model_version":MODEL_VERSION,
                "features":FEATURES,"sklearn_version":sklearn.__version__,
                "estimators":{},"selected":{"wind":False,"gust":False},"calibration":{}}
    # Bound native parallelism for predictable laptop training/inference.
    with threadpool_limits(limits=2):
        for column,name in enumerate(("u","v","gust")):
            mask = np.isfinite(raw[:,column])&np.isfinite(actual[:,column])
            if mask.sum() < 500:
                if name == "gust":
                    artifact["estimators"][name] = None
                    progress("Insufficient gust targets; retaining raw gusts and gating probabilities on calibration coverage.",flush=True)
                    continue
                raise ValueError(f"Insufficient {name} targets for training: {mask.sum()}")
            progress(f"Training {name} correction on {mask.sum()} rows…",flush=True)
            estimator = HistGradientBoostingRegressor(**PARAMETERS)
            estimator.fit(x[mask],actual[mask,column]-raw[mask,column])
            artifact["estimators"][name] = estimator
        selection = [r for r in groups["selection"] if r["lead_time_hours"] <= 48]
        sx,sraw,sy = matrices(selection)
        candidates = corrected(artifact,sx,sraw,candidate=True)
        raw_metrics = regression_metrics(sraw,sy)
        candidate_metrics = regression_metrics(candidates,sy)
        artifact["selected"] = {
            "wind":candidate_metrics["vector_rmse_kt"] < raw_metrics["vector_rmse_kt"] and
                   candidate_metrics["speed_mae_kt"] <= raw_metrics["speed_mae_kt"]*1.02,
            "gust":True}
        gust_candidate = regression_metrics(corrected(artifact,sx,sraw),sy)
        artifact["selected"]["gust"] = (artifact["estimators"].get("gust") is not None and
                   gust_candidate["gust_mae_kt"] is not None and raw_metrics["gust_mae_kt"] is not None and
                   gust_candidate["gust_mae_kt"] < raw_metrics["gust_mae_kt"])
        progress(f"Validation-selected corrections: {artifact['selected']}",flush=True)
        calibration = groups["calibration"]
        cx,craw,cy = matrices(calibration)
        residuals = cy-corrected(artifact,cx,craw)
        pool_report = {}
        for low,high in BANDS:
            key = f"{low}-{high}"
            mask = np.asarray([low <= r["model_lead_hours"] <= high for r in calibration])&np.isfinite(residuals).all(axis=1)
            days = {r["decision_time"][:10] for r,m in zip(calibration,mask) if m}
            values = residuals[mask]
            if len(days) >= 10 and len(values) >= 100:
                artifact["calibration"][key] = values
            pool_report[key] = {"joint_residuals":len(values),"distinct_issue_dates":len(days),
                                "enabled":key in artifact["calibration"]}
        progress("Evaluating the frozen model once on the final chronological test period…",flush=True)
        test = evaluate(groups["test"],artifact)
    prep_path = root/"ml"/"preparation-report.json"
    prep = json.loads(prep_path.read_text()) if prep_path.exists() else {}
    report = {"model_version":MODEL_VERSION,"artifact_version":ARTIFACT_VERSION,
              "trained_at":iso(datetime.now(UTC)),"sklearn_version":sklearn.__version__,
              "numpy_version":np.__version__,"dataset_sha256":hashlib.sha256(raw_bytes).hexdigest(),
              "features":FEATURES,"parameters":PARAMETERS,"selected_corrections":artifact["selected"],
              "selection":{"raw_icon_eu":raw_metrics,"candidate_corrections":candidate_metrics,
                           "gust_candidate_given_selected_wind":gust_candidate},
              "split":split,"partitions":{name:{"rows":len(rows),
                  "first_issue":rows[0]["decision_time"],"last_issue":rows[-1]["decision_time"],
                  "first_target":min(r["valid_time"] for r in rows),"last_target":max(r["valid_time"] for r in rows),
                  "distinct_issue_dates":len({r["decision_time"][:10] for r in rows})} for name,rows in groups.items()},
              "calibration_pools":pool_report,"probability_samples":SAMPLES,"test":test,
              "historical_availability_verified":False,"preparation":prep,
              "mixed_icon_comparison":{"status":"unavailable","reason":"No matching historical mixed ICON-D2/EU snapshots with observed outcomes; live raw fields remain available for comparison."},
              "operating_direction_model":{"status":"blocked_missing_independent_labels","p_od07":None,"p_od25":None},
              "limitations":["Backtest is conditional on estimated four-hour historical model publication delay.",
                             "Retrospective DWD reference observations can include later corrections.",
                             "Persistence uses retrospective observations with an estimated one-hour publication delay.",
                             "Residual probabilities are provisional; resampling does not add independent weather events.",
                             "Forecast gust direction is approximated by mean direction; reference gust direction is used when available.",
                             "RWY18 probabilities describe wind-limit suitability, not official operational availability.",
                             "Hourly predictions cannot resolve a 30-minute direction switch precisely.",
                             "Performance over these dates does not establish skill in other seasons or rare extremes."]}
    coverage = test["all_1_to_48h"]["rwy18_weather_probability"]
    low_coverage = min(coverage["unique_tailwind_limit_valid_times"],coverage["unique_crosswind_limit_valid_times"]) < 20
    report["probability_status"] = ("provisional_low_event_coverage" if low_coverage else "provisional_empirical") if artifact["calibration"] else "unavailable_insufficient_calibration"
    artifact["probability_status"] = report["probability_status"]
    output = root/"models"/MODEL_VERSION
    output.mkdir(parents=True,exist_ok=True)
    temp = output/"model.joblib.tmp"
    joblib.dump(artifact,temp,compress=3)
    temp.replace(output/"model.joblib")
    write_json(output/"metrics.json",report)
    write_json(output/"manifest.json",{"artifact_version":ARTIFACT_VERSION,"features":FEATURES,
               "model_version":MODEL_VERSION,"sklearn_version":sklearn.__version__,
               "model_sha256":hashlib.sha256((output/"model.joblib").read_bytes()).hexdigest(),
               "trained_at":report["trained_at"]})
    progress(f"Saved model and held-out metrics to {output}.",flush=True)
    return report
