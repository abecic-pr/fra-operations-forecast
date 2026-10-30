from datetime import timedelta
import unittest

from fra_forecast.dataset import build_dataset, dataset_report
from fra_forecast.domain import DirectionState, iso, parse_time, prediction_features, runway_conditions, wind_components
from fra_forecast.pipeline import live_snapshot
from fra_forecast.sources import parse_forecast, parse_unh


START = parse_time("2026-10-20T00:00:00Z")


def weather(minutes=0, speed=5, direction=250, gust=5):
    return {"valid_time": iso(START + timedelta(minutes=minutes)), "wind_speed_kt": speed,
            "wind_from_deg_true": direction, "wind_gust_kt": gust,
            "model": "icon_d2", "resolution_minutes": 15,
            "available_at": iso(START + timedelta(hours=4)),
            "availability_basis": "estimated_four_hour_model_delay"}


class RuleTests(unittest.TestCase):
    def test_components(self):
        self.assertAlmostEqual(wind_components(20, 70, 70)["headwind_kt"], 20)
        self.assertAlmostEqual(wind_components(20, 250, 70)["tailwind_kt"], 20)
        self.assertAlmostEqual(wind_components(20, 160, 70)["crosswind_kt"], 20)

    def test_landing_limit_is_inclusive(self):
        state = DirectionState("07")
        self.assertEqual(state.step(weather(speed=10))["operating_direction"], "25")

    def test_departure_limit_is_inclusive(self):
        self.assertEqual(runway_conditions(weather(speed=14.99, direction=0, gust=15))["18"]["weather_state"], "usable")
        self.assertEqual(runway_conditions(weather(speed=15, direction=0, gust=15))["18"]["weather_state"], "not_usable")

    def test_crosswind_exceeds_40_including_gust(self):
        self.assertEqual(runway_conditions(weather(direction=90, gust=40))["18"]["weather_state"], "usable")
        self.assertEqual(runway_conditions(weather(direction=90, gust=40.01))["18"]["weather_state"], "not_usable")

    def test_persistence_strictly_over_30_minutes(self):
        state = DirectionState("07")
        for minute in (0, 15, 30):
            self.assertEqual(state.step(weather(minute))["operating_direction"], "07")
        self.assertEqual(state.step(weather(45))["operating_direction"], "25")

    def test_gap_resets_persistence(self):
        state = DirectionState("07")
        state.step(weather())
        result = state.step(weather(60))
        self.assertEqual(result["operating_direction"], "07")
        self.assertIn("gap_resets_persistence", result["reason_codes"])

    def test_steps_must_increase(self):
        state = DirectionState("07")
        state.step(weather())
        with self.assertRaises(ValueError):
            state.step(weather())

    def test_unknown_wind_and_missing_gust(self):
        self.assertIsNone(wind_components(5, "VRB", 70))
        self.assertEqual(wind_components(0, None, 70)["crosswind_kt"], 0)
        self.assertEqual(runway_conditions(weather(gust=None))["18"]["weather_state"], "unknown")
        self.assertIsNone(DirectionState().step(weather(direction=None))["operating_direction"])

    def test_unknown_gust_does_not_hide_known_tailwind_limit(self):
        self.assertEqual(runway_conditions(weather(speed=15, direction=0, gust=None))["18"]["weather_state"], "not_usable")


class DataTests(unittest.TestCase):
    def test_explicit_timezone_required(self):
        with self.assertRaises(ValueError):
            parse_time("2026-10-20T12:00:00")
        self.assertEqual(iso(parse_time("2026-10-20T12:00:00+02:00")), "2026-10-20T10:00:00Z")

    def test_unh_uses_observed_state_and_never_backfills(self):
        body = b"<p>BR 07 Ost Betriebsrichtung seit 20. Oct., 09.54 Uhr</p><p>Prognose BR 25 West</p>"
        parsed = parse_unh(body, "2026-10-20T10:00:00Z")
        self.assertEqual(parsed["operating_direction"], "07")
        self.assertEqual(parsed["since"], "2026-10-20T07:54:00Z")
        self.assertFalse(parsed["historical_label"])
        with self.assertRaises(ValueError):
            parse_unh(b"Prognose BR 25 West", "2026-10-20T10:00:00Z")

    def test_forecast_units_and_missing_gust(self):
        data = {"hourly": {"time": ["2026-10-20T05:00"], "wind_speed_10m": [5],
                            "wind_direction_10m": [250], "wind_gusts_10m": [None]},
                "hourly_units": {"wind_speed_10m": "kn", "wind_gusts_10m": "kn"}}
        meta = {"fetched_at": "2026-10-30T00:00:00Z"}
        row = parse_forecast(data, "icon_d2", meta, START)["hourly"][0]
        self.assertIsNone(row["wind_gust_kt"])
        self.assertEqual(row["available_at"], "2026-10-20T04:00:00Z")
        data["hourly_units"]["wind_speed_10m"] = "km/h"
        with self.assertRaises(ValueError):
            parse_forecast(data, "icon_d2", meta, START)

    def test_future_labels_and_observations_are_not_initial_inputs(self):
        observations = [weather(180, speed=2), weather(240, speed=80), weather(300, speed=90)]
        label = {"start": START, "end": START + timedelta(days=1),
                 "available": START + timedelta(hours=6), "operating_direction": "07",
                 "rwy18_weather_usable": "1", "source": "independent test fixture"}
        rows = build_dataset([{"run_at": iso(START), "hourly": [weather(240), weather(300)]}], observations, [label])
        row = rows[0]
        self.assertEqual(row["lead_time_hours"], 1)
        self.assertIsNone(row["initial_operating_direction"])
        self.assertEqual(row["past_wind_speed_kt"], 2)
        self.assertEqual(row["reference_wind_speed_kt"], 90)
        self.assertEqual(row["target_operating_direction"], "07")
        features = prediction_features(row, None, 1)
        row["reference_wind_speed_kt"] = 999
        row["target_operating_direction"] = "25"
        self.assertEqual(features, prediction_features(row, None, 1))

    def test_missing_labels_do_not_create_accuracy(self):
        rows = build_dataset([{"run_at": iso(START), "hourly": [weather(300)]}], [], [])
        report = dataset_report(rows, [], [])
        self.assertEqual(report["status"], "ready_for_labels")
        self.assertEqual(report["operating_direction_labels"], 0)
        self.assertIsNone(report["operational_model_metrics"])

    def test_live_alignment_fallback_and_null_probabilities(self):
        eu = [{**weather(i * 60), "model": "icon_eu", "resolution_minutes": 60} for i in range(49)]
        d2 = [weather(60)]
        result = live_snapshot(START + timedelta(minutes=10),
                               {"icon_eu": {"hourly": eu}, "icon_d2": {"hourly": d2}},
                               None, [], None, [])
        self.assertEqual(len(result["forecast"]), 48)
        self.assertEqual(result["data_quality"]["forecast_hours_available"], 48)
        self.assertEqual(result["forecast"][0]["model"], "icon_d2")
        self.assertEqual(result["forecast"][-1]["model"], "icon_eu")
        for row in result["forecast"]:
            self.assertGreater(parse_time(row["valid_time"]), START + timedelta(minutes=10))
            self.assertIsNone(row["p_od07"])


if __name__ == "__main__":
    unittest.main()
