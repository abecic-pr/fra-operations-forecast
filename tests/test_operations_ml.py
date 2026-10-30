from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fra_forecast.domain import iso, parse_time
from fra_forecast.operations_ml import change_scores, evaluate, labeled_rows, train, predict
from fra_forecast.sources import write_csv, write_json
from fra_forecast.dataset import LABEL_COLUMNS

try:
    import sklearn
except ImportError:
    sklearn = None


@unittest.skipIf(sklearn is None, "optional ML dependencies")
class OperationsTests(unittest.TestCase):
    def test_missing_target_does_not_remove_weather_step_from_baseline(self):
        import numpy as np
        start = parse_time("2026-05-01T00:00:00Z")
        weather = [{"decision_time": iso(start), "valid_time": iso(start+timedelta(hours=h)), "lead_time_hours": h,
                    "raw_wind_speed_kt": 5, "raw_wind_from_deg_true": 70, "raw_gust_kt": 8}
                   for h in (1, 2, 3)]
        labels = [{"start": start, "end": start+timedelta(minutes=90), "available": start,
                   "operating_direction": "25", "source": "test"},
                  {"start": start+timedelta(minutes=150), "end": start+timedelta(hours=4), "available": start,
                   "operating_direction": "07", "source": "test"}]
        rows = labeled_rows(weather, labels)
        with patch("fra_forecast.operations_ml.class_probabilities", side_effect=lambda a, x: np.full(len(x), 0.8)):
            result = evaluate(rows, {"probability_status": "test"}, weather, labels)
        self.assertEqual(result["horizons"]["all_1_to_48h"]["challenge_rules"]["accuracy"], 1)

    def test_change_scoring_uses_interval_boundaries_and_excludes_gaps(self):
        start = parse_time("2026-05-01T00:00:00Z")
        labels = [{"start": start+timedelta(minutes=a), "end": start+timedelta(minutes=b), "available": start,
                   "operating_direction": direction, "source": "test"}
                  for a, b, direction in [(0, 75, "25"), (75, 90, "07"), (90, 420, "25")]]
        points = [{"valid_time": iso(start+timedelta(hours=h)), "model": "25", "challenge_rules": "25"} for h in range(1, 7)]
        result = change_scores({iso(start): points}, labels, 6)["candidates"]["model"]
        self.assertEqual(result["missed_changes"], 1)
        self.assertEqual(result["issue_cases"], 1)
        labels.pop(1)
        result = change_scores({iso(start): points}, labels, 6)["candidates"]["model"]
        self.assertEqual(result["issue_cases"], 0)
        self.assertEqual(result["excluded_issues"], 1)

    def test_future_label_is_target_only(self):
        start = parse_time("2026-05-01T00:00:00Z")
        row = {"decision_time": iso(start), "valid_time": iso(start+timedelta(hours=1)), "lead_time_hours": 1,
               "raw_wind_speed_kt": 10, "raw_wind_from_deg_true": 90, "raw_gust_kt": 12}
        label = {"start": start, "end": start+timedelta(days=1), "available": start+timedelta(hours=2),
                 "operating_direction": "07", "source": "independent synthetic test fixture"}
        result = labeled_rows([row], [label])[0]
        self.assertIsNone(result["initial_operating_direction"])
        self.assertEqual(result["target_operating_direction"], "07")
        label["operating_direction"] = "25"
        self.assertEqual(result["x"], labeled_rows([row], [label])[0]["x"])

    def test_empty_labels_create_unavailable_report_without_model(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/"labels.csv"
            write_csv(path, [], LABEL_COLUMNS)
            report = train(folder, path)
            self.assertEqual(report["reason"], "missing_independent_labels")
            self.assertFalse((Path(folder)/"models").exists())

    def test_real_training_path_with_explicit_synthetic_test_labels(self):
        from fra_forecast.ml_live import load_artifact
        from fra_forecast.domain import FEATURE_NAMES
        from fra_forecast.operations_ml import MODEL_VERSION
        start = parse_time("2026-05-01T00:00:00Z")
        labels, rows = [], []
        for day in range(60):
            issue = start+timedelta(days=day)
            direction = "07" if day % 2 else "25"
            labels.append({"valid_from": iso(issue), "valid_to": iso(issue+timedelta(days=1)), "available_at": iso(issue),
                           "operating_direction": direction, "source": "synthetic independent labels: tests only"})
            for h in range(1, 24):
                rows.append({"decision_time": iso(issue), "valid_time": iso(issue+timedelta(hours=h)),
                             "forecast_available_at": iso(issue), "lead_time_hours": h,
                             "raw_wind_speed_kt": 12, "raw_wind_from_deg_true": 70 if direction == "07" else 250,
                             "raw_gust_kt": 15})
        with TemporaryDirectory() as folder:
            label_path = Path(folder)/"labels.csv"
            write_csv(label_path, labels, LABEL_COLUMNS)
            write_json(Path(folder)/"ml"/"dataset.json", {"data_version": "wind-training-v1", "rows": rows})
            report = train(folder, label_path, progress=lambda *a, **k: None)
            self.assertEqual(report["status"], "trained")
            artifact, _, error = load_artifact(folder, MODEL_VERSION, FEATURE_NAMES)
            self.assertIsNone(error)
            point = predict(artifact, {"wind_speed_kt": 12, "wind_from_deg_true": 70, "wind_gust_kt": 15}, "07", 6)
            self.assertEqual(point["operating_direction"], "07")
            self.assertAlmostEqual(point["p_od07"]+point["p_od25"], 1)
            self.assertIn("1", report["test"]["horizons"])
            self.assertIn("6", report["test"]["horizons"])
            self.assertIn("24", report["test"]["horizons"])
