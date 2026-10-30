from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fra_forecast.domain import iso, parse_time
from fra_forecast.sources import write_csv
from fra_forecast.submission import eligible_artifact, export, issue_times

START = parse_time("2026-10-20T12:00:00Z")


class Client:
    checks = []


def forecast_fixture(client, model, run_at, forecast_days=4):
    return {"hourly": [{"valid_time": iso(run_at+timedelta(hours=h)), "wind_speed_kt": 5,
                        "wind_from_deg_true": 250, "wind_gust_kt": 8,
                        "available_at": iso(run_at+timedelta(hours=4)), "fetched_at": "2026-10-30T12:00:00Z"}
                       for h in range(73)]}


class SubmissionTests(unittest.TestCase):
    def test_rejects_missing_duplicate_and_naive_issue_times(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/"issues.csv"
            for stamps in ([], [iso(START), iso(START)], ["2026-10-20T12:00:00"], ["2026-10-20T12:15:00Z"]):
                write_csv(path, [{"forecast_reference_time": s} for s in stamps], ["forecast_reference_time"])
                with self.assertRaises(ValueError):
                    issue_times(path)

    def test_artifact_cutoff_includes_calibration_outcomes(self):
        report = {"partitions": {name: {"last_target": iso(START-timedelta(hours=2))} for name in ("train", "selection", "calibration")}}
        self.assertTrue(eligible_artifact({"model_version": "legacy"}, report, START))
        report["partitions"]["calibration"]["last_target"] = iso(START)
        self.assertFalse(eligible_artifact({"model_version": "legacy"}, report, START))
        self.assertFalse(eligible_artifact({"data_cutoff": iso(START)}, {}, START))

    def test_replay_uses_archived_run_and_keeps_unknown_od(self):
        with TemporaryDirectory() as folder:
            issues = Path(folder)/"issues.csv"
            write_csv(issues, [{"forecast_reference_time": iso(START)}])
            with patch("fra_forecast.submission.forecast", side_effect=forecast_fixture) as fetch:
                report = export(folder, issues, Path(folder)/"submission", client=Client())
            self.assertEqual(fetch.call_args.args[2], START-timedelta(hours=6))
            self.assertEqual(report["rows"], 48)
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(report["issues"][0]["wind_hours"], 48)
            self.assertEqual(report["issues"][0]["od_probability_hours"], 0)
            import json
            points = json.loads((Path(folder)/"submission"/"forecasts.json").read_text())["forecast"]
            self.assertEqual(points[-1]["valid_time"], iso(START+timedelta(hours=48)))
            self.assertIsNone(points[0]["operating_direction"])
            self.assertEqual(points[0]["baseline_operating_direction"], "25")
            self.assertEqual(points[0]["expected_operating_direction"], "25")
            self.assertEqual(points[0]["landing_movement_direction"], "westbound")
            self.assertEqual(points[0]["landing_approach_from"], "east")
            self.assertEqual(points[0]["centre_departure_runway_end"], "25C")
            self.assertEqual(points[0]["runway18_departure_direction"], "southbound")

    def test_source_failure_does_not_remove_requested_hours(self):
        with TemporaryDirectory() as folder:
            issues = Path(folder)/"issues.csv"
            write_csv(issues, [{"forecast_reference_time": iso(START)}])
            with patch("fra_forecast.submission.forecast", side_effect=OSError("offline")):
                report = export(folder, issues, Path(folder)/"submission", client=Client())
            self.assertEqual(report["rows"], 48)
            self.assertEqual(report["issues"][0]["wind_hours"], 0)
            self.assertEqual(report["issues"][0]["source_error"], "offline")
