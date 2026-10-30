"""Optional ML enrichment; a missing model never breaks the raw forecast."""

from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

from .domain import UTC, iso, parse_time, runway_conditions
from .ml_data import uv
from .sources import forecast
from .wind_ml import ARTIFACT_VERSION, FEATURES, MODEL_VERSION


def load_artifact(data_dir, model_version=MODEL_VERSION, expected_features=FEATURES):
    folder = Path(data_dir)/"models"/model_version
    if not (folder/"manifest.json").exists():
        return None, None, "model_artifact_missing"
    try:
        manifest = json.loads((folder/"manifest.json").read_text())
        if manifest["artifact_version"] != ARTIFACT_VERSION or manifest["features"] != expected_features:
            return None,None,"model_artifact_incompatible"
        import joblib
        import sklearn
        if manifest["sklearn_version"] != sklearn.__version__:
            return None,None,"model_dependency_version_mismatch"
        model_bytes = (folder/"model.joblib").read_bytes()
        if hashlib.sha256(model_bytes).hexdigest() != manifest["model_sha256"]:
            return None,None,"model_artifact_hash_mismatch"
        report_bytes = (folder/"metrics.json").read_bytes()
        if manifest.get("metrics_sha256") and hashlib.sha256(report_bytes).hexdigest() != manifest["metrics_sha256"]:
            return None,None,"model_metrics_hash_mismatch"
        artifact = joblib.load(folder/"model.joblib")
        if artifact.get("artifact_version") != ARTIFACT_VERSION or artifact.get("features") != expected_features:
            return None,None,"model_artifact_incompatible"
        report = json.loads(report_bytes)
        if artifact.get("model_version") != model_version or report.get("model_version") != model_version:
            return None,None,"model_artifact_incompatible"
        if artifact.get("experiment_id") != report.get("experiment_id"):
            return None,None,"model_report_mismatch"
        return artifact,report,None
    except ImportError:
        return None,None,"ml_dependencies_not_installed"
    except Exception:
        # Corrupt/unsupported local serialization must not take down raw forecasts.
        return None,None,"model_artifact_invalid"


def explicit_live_run(client, reference):
    def coverage(data, run_at):
        valid = {r["valid_time"] for r in data.get("hourly", [])
                 if uv(r.get("wind_speed_kt"), r.get("wind_from_deg_true")) is not None
                 and 5 <= (parse_time(r["valid_time"])-run_at).total_seconds()/3600 <= 72}
        return sum(iso(reference+timedelta(hours=h)) in valid for h in range(1, 49))

    preferred = None
    metadata_url = "https://api.open-meteo.com/data/dwd_icon_eu/static/meta.json"
    try:
        meta,_ = client.json("icon_eu_metadata",metadata_url)
        run_at = datetime.fromtimestamp(meta["last_run_initialisation_time"],UTC)
        available = datetime.fromtimestamp(meta["last_run_availability_time"],UTC)+timedelta(minutes=10)
        if available <= reference and reference-run_at <= timedelta(hours=24) and run_at <= reference:
            data = forecast(client,"icon_eu",run_at,forecast_days=4)
            provenance = {"model_run_at":iso(run_at),"available_at":iso(available),
                         "availability_basis":"provider_metadata_plus_ten_minute_replication_buffer",
                         "availability_verified":True,"metadata_url":metadata_url}
            preferred = (data, provenance, coverage(data, run_at))
            if preferred[2] == 48:
                return data, provenance
    except (OSError,ValueError,KeyError):
        pass
    # This path records the assumption, never presenting run time as publication.
    eligible = reference-timedelta(hours=4)
    run_at = eligible.replace(hour=(eligible.hour//6)*6,minute=0,second=0,microsecond=0)
    try:
        data = forecast(client,"icon_eu",run_at,forecast_days=4)
    except (OSError, ValueError, KeyError):
        if preferred:
            return preferred[0], {**preferred[1], "run_selection_reason": "partial_newer_run_older_run_unavailable"}
        raise
    if preferred and preferred[2] >= coverage(data, run_at):
        return preferred[0], {**preferred[1], "run_selection_reason": "best_available_partial_run"}
    return data,{"model_run_at":iso(run_at),"available_at":iso(run_at+timedelta(hours=4)),
                 "availability_basis":"estimated_four_hour_delay_live_metadata_unavailable_for_reference",
                 "availability_verified":False,
                 "run_selection_reason": "older_run_has_more_supported_hours" if preferred else "metadata_not_eligible"}


def enrich(snapshot, data_dir, client, enabled=True):
    from .wind_ml import corrected, features, probabilities
    snapshot["schema_version"] = "1.1"
    reference = parse_time(snapshot["generated_at"]).replace(minute=0,second=0,microsecond=0)
    snapshot["forecast_reference_time"] = iso(reference)
    artifact,report,error = load_artifact(data_dir) if enabled else (None,None,"ml_disabled")
    for point in snapshot["forecast"]:
        point["ml"] = {"wind_speed_kt":point.get("wind_speed_kt"),
                       "wind_from_deg_true":point.get("wind_from_deg_true"),
                       "wind_gust_kt":point.get("wind_gust_kt"),
                       "p_rwy18_weather_usable":None,"p_od07":None,"p_od25":None,
                       "model_version":None,"source_model":point.get("model"),
                       "model_run_at":point.get("model_run_at"),
                       "forecast_reference_time":iso(reference),
                       "lead_time_hours":int((parse_time(point["valid_time"])-reference).total_seconds()/3600),
                       "prediction_status":"fallback_raw_forecast","probability_status":"unavailable",
                       "fallback_reason":error}
    summary = {"status":"fallback_raw_forecast","fallback_reason":error,
               "model_version":report.get("model_version") if report else None,
               "forecast_reference_time":iso(reference),"forecast_hours_available":0,
               "operating_direction_status":"blocked_missing_independent_labels"}
    snapshot["ml_model"] = summary
    if artifact is None:
        return snapshot
    try:
        run,provenance = explicit_live_run(client,reference)
        import numpy as np
        from threadpoolctl import threadpool_limits
        by_time = {r["valid_time"]:r for r in run["hourly"]}
        inputs,positions,source_rows = [],[],[]
        run_at = parse_time(provenance["model_run_at"])
        for i,point in enumerate(snapshot["forecast"]):
            weather = by_time.get(point["valid_time"])
            if weather is None:
                point["ml"]["fallback_reason"] = "explicit_icon_eu_forecast_missing"
                continue
            components = uv(weather.get("wind_speed_kt"),weather.get("wind_from_deg_true"))
            lead = (parse_time(weather["valid_time"])-run_at).total_seconds()/3600
            if components is None or not 5 <= lead <= 72:
                point["ml"]["fallback_reason"] = "outside_trained_input_domain"
                continue
            inputs.append({"valid_time":weather["valid_time"],"model_lead_hours":lead,
                           "raw_u_kt":components[0],"raw_v_kt":components[1],"raw_gust_kt":weather.get("wind_gust_kt")})
            positions.append(i)
            source_rows.append(weather)
        if not inputs:
            raise ValueError("No explicit ICON-EU rows in the trained domain")
        raw = np.asarray([[r["raw_u_kt"],r["raw_v_kt"],r["raw_gust_kt"]] for r in inputs],dtype=float)
        with threadpool_limits(limits=2):
            values = corrected(artifact,np.asarray([features(r) for r in inputs]),raw)
            chance = probabilities(artifact,inputs,values)
        active = any(artifact["selected"].values())
        for i,index in enumerate(positions):
            u,v,gust = values[i]
            speed = float(math.hypot(u,v))
            direction = float(math.degrees(math.atan2(-u,-v))%360) if speed >= 0.5 else None
            weather = {"wind_speed_kt":speed,"wind_from_deg_true":direction,
                       "wind_gust_kt":float(gust) if math.isfinite(gust) else None}
            ml = {**snapshot["forecast"][index]["ml"],**weather,**provenance,
                  "model_version":MODEL_VERSION,"source_model":"icon_eu",
                  "model_lead_hours":inputs[i]["model_lead_hours"],
                  "fetched_at":source_rows[i]["fetched_at"],
                  "raw_wind_speed_kt":source_rows[i]["wind_speed_kt"],
                  "raw_wind_from_deg_true":source_rows[i].get("wind_from_deg_true"),
                  "raw_wind_gust_kt":source_rows[i].get("wind_gust_kt"),
                  "selected_corrections":artifact["selected"],
                  "prediction_status":"ml_corrected" if active else "raw_icon_eu_validation_fallback",
                  "fallback_reason":None if active else "corrections_did_not_improve_validation",
                  "p_rwy18_weather_usable":float(chance[i]) if math.isfinite(chance[i]) else None,
                  "probability_status":artifact["probability_status"] if math.isfinite(chance[i]) else "unavailable_missing_gust_or_calibration",
                  "runway_wind":runway_conditions(weather)}
            snapshot["forecast"][index]["ml"] = ml
        summary.update({"status":"ml_corrected" if active else "raw_icon_eu_validation_fallback",
                        "fallback_reason":None if active else "corrections_did_not_improve_validation",
                        "forecast_hours_available":len(inputs),**provenance,
                        "trained_at":report["trained_at"],"selected_corrections":artifact["selected"],
                        "partitions":report["partitions"],"probability_status":artifact["probability_status"],
                        "historical_availability_verified":False,
                        "test_summary":report["test"]["all_1_to_48h"],"metrics_url":"/api/model-metrics",
                        "limitations":report["limitations"]})
    except (ImportError,OSError,ValueError,KeyError,TypeError) as exc:
        summary["fallback_reason"] = f"ml_inference_unavailable: {exc}"
        for point in snapshot["forecast"]:
            point["ml"]["fallback_reason"] = summary["fallback_reason"]
    return snapshot
