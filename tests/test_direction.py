from datetime import timedelta
import unittest

from fra_forecast.direction import agreement, enrich, enrich_comparison, prediction, runway_plan
from fra_forecast.domain import iso, parse_time

START = parse_time("2026-10-30T12:00:00Z")


def point(hour, direction="07", learned=None):
    return {"valid_time": iso(START+timedelta(hours=hour)), "operating_direction": direction,
            "model": "icon_d2", "rwy18_weather_state": "usable", "operations_ml": learned,
            "p_od07": None, "p_od25": None}


def model(direction="25"):
    return {"status": "available", "operating_direction": direction, "p_od07": 0.2, "p_od25": 0.8,
            "probability_status": "uncalibrated_model_probability", "model_version": "test-only"}


class DirectionTests(unittest.TestCase):
    def test_runway_movement_and_approach_are_opposites(self):
        for direction, movement, approach, landing, centre in [
                ("07", "eastbound", "west", ["07L", "07R"], "07C"),
                ("25", "westbound", "east", ["25R", "25L"], "25C")]:
            plan = runway_plan(direction, "not_usable")
            self.assertEqual(plan["landings"]["movement_direction"], movement)
            self.assertEqual(plan["landings"]["approach_from"], approach)
            self.assertEqual(plan["landings"]["runway_ends"], landing)
            self.assertEqual(plan["centre_departures"]["movement_direction"], movement)
            self.assertEqual(plan["centre_departures"]["runway_end"], centre)
            self.assertEqual(plan["runway18_departures"]["movement_direction"], "southbound")
            self.assertEqual(plan["runway18_departures"]["weather_state"], "not_usable")
            self.assertEqual(plan["runway18_departures"]["official_operational_status"], "unknown")
            self.assertIsNone(plan["individual_flight_assignment"])

    def test_missing_direction_never_defaults_to_east_or_west(self):
        result = prediction(point(1, None))
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["movement_direction"])
        self.assertEqual(result["runway_plan"]["landings"]["runway_ends"], [])
        self.assertEqual(result["runway_plan"]["runway18_departures"]["movement_direction"], "southbound")

    def test_baseline_is_usable_but_does_not_invent_certainty(self):
        snapshot = {"forecast": [point(h) for h in range(1, 49)],
                    "next_operating_direction_change": {"status": "no_change_within_horizon"}}
        enrich(snapshot)
        self.assertEqual(snapshot["operating_direction_outlook"]["hours_eastbound"], 48)
        self.assertEqual(len(snapshot["operating_direction_outlook"]["periods"]), 1)
        self.assertIsNone(snapshot["forecast"][0]["direction_forecast"]["certainty_score"])
        self.assertIsNone(snapshot["forecast"][0]["p_od07"])
        self.assertEqual(snapshot["operating_direction_outlook"]["next_change"]["status"], "no_change_within_horizon")

    def test_valid_model_is_separate_from_rule_baseline(self):
        snapshot = {"forecast": [point(1, learned=model())],
                    "operations_model": {"next_change": {"status": "change_expected", "method": "predicted_hourly_class_change"}}}
        enrich(snapshot)
        self.assertEqual(snapshot["forecast"][0]["operating_direction"], "07")
        forecast = snapshot["forecast"][0]["direction_forecast"]
        self.assertEqual(forecast["movement_direction"], "westbound")
        self.assertEqual(forecast["certainty_score"], 0.8)
        self.assertEqual(forecast["probability_status"], "uncalibrated_model_probability")
        self.assertEqual(snapshot["operating_direction_outlook"]["next_change"]["method"], "predicted_hourly_class_change")

    def test_invalid_model_probabilities_fall_back_with_reason(self):
        for learned in [model("07"), {**model(), "p_od25": None}, {**model(), "p_od07": float("nan")}, {**model(), "p_od25": True}]:
            forecast = prediction(point(1), learned)
            self.assertEqual(forecast["movement_direction"], "eastbound")
            self.assertIsNone(forecast["certainty_score"])
            self.assertEqual(forecast["learned_model_reason"], "invalid_od_model_probabilities")

    def test_provider_agreement_does_not_count_correlated_corrections(self):
        candidates = {name: {"operating_direction": "07"} for name in ("raw_icon_eu", "boosting_correction", "linear_correction", "equal_blend")}
        candidates["raw_gfs"] = {"operating_direction": "25"}
        result = agreement(candidates, "07")
        self.assertEqual(result["available_sources"], 2)
        self.assertEqual(result["fraction_supporting_prediction"], 0.5)
        candidates.pop("raw_gfs")
        self.assertIsNone(agreement(candidates, "07")["fraction_supporting_prediction"])

    def test_comparison_uses_selected_direction_and_splits_missing_hours(self):
        snapshot = {"forecast": [{"valid_time": iso(START+timedelta(hours=h)),
                                 "selected": {**point(h, "25"), "effective_candidate": "linear_correction"},
                                 "candidates": {}} for h in (1, 3)],
                    "next_rule_direction_change": {"status": "unknown"}}
        enrich_comparison(snapshot)
        self.assertEqual(snapshot["forecast"][0]["direction_forecast"]["wind_model"], "linear_correction")
        self.assertEqual(snapshot["operating_direction_outlook"]["hours_westbound"], 2)
        self.assertEqual(len(snapshot["operating_direction_outlook"]["periods"]), 2)

    def test_mixed_fallback_change_follows_the_displayed_sequence(self):
        snapshot = {"forecast": [point(1), point(2, learned=model())],
                    "next_operating_direction_change": {"status": "no_change_within_horizon"}}
        enrich(snapshot)
        change = snapshot["operating_direction_outlook"]["next_change"]
        self.assertEqual(change["status"], "change_expected")
        self.assertEqual(change["from"], "07")
        self.assertEqual(change["to"], "25")
        self.assertEqual(change["method"], "mixed_learned_and_weather_hourly_sequence")
