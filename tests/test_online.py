import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fra_forecast.domain import iso
from fra_forecast.online import Learner, replay, solve, step

START = datetime(2026, 10, 1, tzinfo=timezone.utc)


def sample(at, lead, raw_u, actual_u, raw_t=10.0, actual_t=12.0):
    return {"issued_at": iso(at - timedelta(hours=lead)), "valid_time": iso(at),
            "available_at": iso(at + timedelta(hours=1)), "lead": lead, "model": "icon_d2",
            "raw": {"u": raw_u, "v": 0.0, "t": raw_t}, "actual": {"u": actual_u, "v": 0.0, "t": actual_t}}


def observation(at, speed, direction=270.0):
    return {"valid_time": iso(at), "wind_quality_code": "3", "gust_quality_code": "3",
            "wind_speed_kt": speed, "wind_from_deg_true": direction, "wind_gust_kt": speed + 3}


class OnlineLearningTest(unittest.TestCase):
    def test_solve(self):
        self.assertEqual([[round(v, 9) for v in row] for row in solve([[2, 1], [1, 3]], [[3], [5]])], [[0.8], [1.4]])

    def test_cold_start_is_the_raw_forecast(self):
        (u, v), weight = Learner().predict("icon_d2", "wind", 3, iso(START), (4.0, -2.0))
        self.assertAlmostEqual(u, 4.0)
        self.assertAlmostEqual(v, -2.0)
        self.assertEqual(weight, 0.0)

    def test_learns_a_systematic_error_without_seeing_the_future(self):
        # Truth is 0.8 * forecast + 2 kt; the replay must shrink error over time.
        rows = [sample(START + timedelta(hours=h), 1, 10.0 + (h % 7), 0.8 * (10.0 + (h % 7)) + 2) for h in range(400)]
        _, scored = replay(rows)
        learned = sum(abs(r["learned"]["u"] - r["actual"]["u"]) for r in scored[-48:])
        raw = sum(abs(r["raw"]["u"] - r["actual"]["u"]) for r in scored[-48:])
        self.assertAlmostEqual(scored[0]["learned"]["u"], scored[0]["raw"]["u"])  # nothing known yet
        self.assertLess(learned, raw / 2)
        self.assertLess(abs(scored[-1]["learned"]["t"] - 12.0), 0.5)

    def test_live_step_scores_published_value_then_learns(self):
        with tempfile.TemporaryDirectory() as folder:
            issued = START
            at = issued + timedelta(hours=1)
            snapshot = {"forecast": [{"valid_time": iso(at), "lead_time_hours": 0.5, "model": "icon_d2",
                                      "wind_speed_kt": 10.0, "wind_from_deg_true": 270.0, "temperature_c": 8.0}]}
            step(folder, snapshot, [], {}, now=issued)
            self.assertEqual(snapshot["forecast"][0]["online"]["status"], "cold_start_raw_forecast")
            # An observation before the valid time does not exist yet: nothing is verified.
            report = step(folder, {"forecast": []}, [observation(at - timedelta(minutes=10 * i), 14.0) for i in range(6, 12)], {},
                          now=issued + timedelta(minutes=30))
            self.assertEqual(report["live"]["verified_forecasts_all_leads"], 0)
            observations = [observation(at - timedelta(minutes=10 * i), 14.0) for i in range(6)]
            report = step(folder, {"forecast": []}, observations, {iso(at): 9.5}, now=at + timedelta(minutes=20))
            self.assertEqual(report["live"]["verified_forecasts_all_leads"], 1)
            recent = report["recent"][0]
            self.assertAlmostEqual(recent["learned"]["wind_speed_kt"], 10.0)  # what was published, not refit
            self.assertAlmostEqual(recent["actual"]["wind_speed_kt"], 14.0)
            self.assertEqual(recent["actual"]["temperature_c"], 9.5)
            state = json.loads((Path(folder) / "online" / "state.json").read_text())
            self.assertEqual(state["pending"], [])
            self.assertTrue(any(cell["weight"] > 0 for cell in state["cells"].values()))
            later = {"forecast": [{"valid_time": iso(at + timedelta(hours=1)), "lead_time_hours": 0.5, "model": "icon_d2",
                                   "wind_speed_kt": 10.0, "wind_from_deg_true": 270.0, "temperature_c": 8.0}]}
            step(folder, later, observations, {}, now=at + timedelta(minutes=30))
            online = later["forecast"][0]["online"]
            self.assertEqual(online["status"], "learned_correction")
            self.assertGreater(online["wind_speed_kt"], 10.0)
            self.assertTrue(math.isfinite(online["temperature_c"]))


if __name__ == "__main__":
    unittest.main()
