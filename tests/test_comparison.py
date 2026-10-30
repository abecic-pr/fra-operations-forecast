from datetime import datetime, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fra_forecast import comparison
from fra_forecast.domain import UTC, iso, parse_time, runway_conditions
from fra_forecast.ml_data import uv
from fra_forecast.sources import write_json

try:
    import numpy as np
except ImportError:
    np = None


def rows():
    start = parse_time("2026-05-01T00:00:00Z")
    return [{"decision_time": iso(start+timedelta(days=d)), "valid_time": iso(start+timedelta(days=d, hours=h)),
             "model_lead_hours": h+4, "lead_time_hours": h, "raw_u_kt": 1., "raw_v_kt": 2., "raw_gust_kt": 5.,
             "target_u_kt": 2., "target_v_kt": 2., "target_gust_kt": 6., "target_gust_from_deg_true": 250.}
            for d in range(12) for h in range(1, 11)]


class Constant:
    def __init__(self, value):
        self.value = value

    def predict(self, x):
        return np.full(len(x), self.value)


@unittest.skipIf(np is None, "optional ML dependencies")
class ComparisonTests(unittest.TestCase):
    def test_weather_probability_baseline_uses_identical_known_cases(self):
        records = rows()[:2]
        records[0].update(raw_u_kt=0., raw_v_kt=0., raw_gust_kt=5.)
        artifact = {"models": {}, "calibrations": {"raw_icon_eu": {}}}
        with patch("fra_forecast.comparison.probabilities", return_value=np.array([0.8, 0.6])):
            result = comparison.evaluate(records, artifact)
        matched = result["all_1_to_48h"]["candidates"]["raw_icon_eu"]["weather"]["probability"]["matched_baselines"]["challenge_rules"]
        self.assertEqual(matched["samples"], 1)
        self.assertEqual(matched["excluded_probability_cases"], 1)
        self.assertAlmostEqual(matched["model_brier_score"], 0.16)
        self.assertEqual(matched["baseline_brier_score"], 0)

    def test_probability_status_preserves_sparse_event_warning(self):
        report = {"test": {"all_1_to_48h": {"candidates": {"linear_correction": {"weather": {"unique_adverse_valid_times": 1}}}}}}
        self.assertEqual(comparison.probability_status(report, "linear_correction"), "provisional_low_event_coverage")
        self.assertEqual(comparison.probability_status({}, "raw_icon_eu"), "provisional_low_event_coverage")

    def test_selection_uses_full_reference_cohorts_and_rejects_missing_cases(self):
        records = rows()
        raw = np.tile([1., 2., 5.], (len(records), 1))
        good = np.tile([2., 2., 6.], (len(records), 1))
        predictions = {n: raw.copy() for n in comparison.CANDIDATES}
        predictions["linear_correction"] = good.copy()
        self.assertEqual(comparison.choose_policy(records, predictions)["winner"], "linear_correction")
        predictions["linear_correction"][0, 2] = np.nan
        policy = comparison.choose_policy(records, predictions)
        self.assertEqual(policy["winner"], "raw_icon_eu")
        self.assertFalse(policy["candidates"]["linear_correction"]["full_reference_coverage"])
        predictions["linear_correction"] = raw + 30
        self.assertEqual(comparison.choose_policy(records, predictions)["winner"], "raw_icon_eu")

    def test_blend_handles_north_wraparound_and_missing_member_gust(self):
        record = rows()[0]
        original, target = uv(10, 359), uv(10, 1)
        record.update(raw_u_kt=original[0], raw_v_kt=original[1], raw_gust_kt=12.)
        estimators = {"u": Constant(target[0]-original[0]), "v": Constant(target[1]-original[1]), "gust": Constant(0)}
        artifact = {"models": {n: {"estimators": dict(estimators)} for n in ("linear_correction", "boosting_correction")}}
        values = comparison.values(artifact, [record])
        weather = comparison.wind_dict(values["equal_blend"][0])
        self.assertLess(min(weather["wind_from_deg_true"], 360-weather["wind_from_deg_true"]), 1)
        self.assertGreater(weather["wind_speed_kt"], 9.9)
        artifact["models"]["linear_correction"]["estimators"]["gust"] = None
        weather = comparison.wind_dict(comparison.values(artifact, [record])["equal_blend"][0])
        self.assertIsNone(weather["wind_gust_kt"])

    def test_persistence_scores_include_raw_on_exactly_same_rows(self):
        records = rows()
        for record in records:
            record.update(persistence_u_kt=2., persistence_v_kt=2., persistence_gust_kt=6.)
        records[0].update(persistence_u_kt=None, persistence_v_kt=None, persistence_gust_kt=None, target_u_kt=100.)
        result = comparison.evaluate(records, {"models": {}, "calibrations": {}})["all_1_to_48h"]
        persistence = result["candidates"]["persistence"]
        self.assertEqual(persistence["samples"], 119)
        self.assertEqual(persistence["raw_on_same_rows"]["samples"], 119)
        self.assertEqual(result["reference_wind_rows"], 120)
        self.assertLess(persistence["raw_on_same_rows"]["vector_rmse_kt"], result["candidates"]["raw_icon_eu"]["vector_rmse_kt"])

    def test_one_candidate_has_unknown_spread(self):
        self.assertEqual(comparison.disagreement({"raw": {"wind_speed_kt": 5}})["status"], "unknown")

    def test_future_snapshot_is_not_initial_direction(self):
        reference = parse_time("2026-10-30T12:00:00Z")
        with TemporaryDirectory() as folder:
            snapshot = {"observed_operations": {"operating_direction": "07", "since": "2026-10-29T00:00:00Z",
                                                 "observed_at": iso(reference+timedelta(minutes=5))}}
            self.assertIsNone(comparison.observed_initial(snapshot, folder, reference))

    def test_live_fallback_keeps_48_hours_and_does_not_rewrite_legacy(self):
        reference = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)-timedelta(hours=3)
        points = [{"valid_time": iso(reference+timedelta(hours=h)), "ml": {
            "source_model": "icon_eu", "raw_wind_speed_kt": 5, "raw_wind_from_deg_true": 250,
            "raw_wind_gust_kt": 8, "model_run_at": iso(reference-timedelta(hours=6)),
            "available_at": iso(reference-timedelta(hours=2)), "availability_verified": False}} for h in range(1, 49)]
        with TemporaryDirectory() as folder:
            path = Path(folder)/"forecast.json"
            write_json(path, {"forecast_reference_time": iso(reference), "generated_at": iso(reference), "forecast": points})
            before = path.read_bytes()
            report = comparison.refresh(folder, include_gfs=False)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(report["status"], "stale_snapshot")
            self.assertEqual(len(report["forecast"]), 48)
            self.assertEqual(report["policy"]["winner"], "raw_icon_eu")
            self.assertTrue(all(p["selected"]["p_rwy18_weather_usable"] is None for p in report["forecast"]))
            self.assertIsNone(report["forecast"][0]["candidates"]["persistence"]["wind_speed_kt"])
            points.pop()
            write_json(path, {"forecast_reference_time": iso(reference), "generated_at": iso(reference), "forecast": points})
            with self.assertRaises(ValueError):
                comparison.refresh(folder, include_gfs=False)

    def test_model_report_hash_is_checked(self):
        import sklearn
        from fra_forecast.wind_ml import save_artifact, FEATURES, ARTIFACT_VERSION
        from fra_forecast.ml_live import load_artifact
        artifact = {"artifact_version": ARTIFACT_VERSION, "features": FEATURES, "model_version": comparison.MODEL_VERSION,
                    "sklearn_version": sklearn.__version__, "experiment_id": "test"}
        report = {"model_version": comparison.MODEL_VERSION, "trained_at": "2026-05-01T00:00:00Z", "experiment_id": "test"}
        with TemporaryDirectory() as folder:
            save_artifact(folder, artifact, report)
            self.assertIsNone(load_artifact(folder, comparison.MODEL_VERSION)[2])
            write_json(Path(folder)/"models"/comparison.MODEL_VERSION/"metrics.json", {**report, "experiment_id": "tampered"})
            self.assertEqual(load_artifact(folder, comparison.MODEL_VERSION)[2], "model_metrics_hash_mismatch")
