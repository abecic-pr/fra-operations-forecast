from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fra_forecast.dataset import label_at, load_labels
from fra_forecast.domain import parse_time
from fra_forecast.operations_history import parse_day, training_points
from fra_forecast.operations_ml import change_scores
from fra_forecast.sources import write_csv


def page(day="20.07.2026", directions=None):
    directions = directions or ["25"]*48
    bars = []
    for titles in (["Windrichtung N / 0°, 5kn"]*48,
                   [f"Betriebsrichtung {'West' if d == '25' else 'Ost'} ({d})" if d else "unbekannt" for d in directions]):
        bars.append('<div class="LaermGraphLegende--24h">'+''.join(
            f'<img class="LaermGraphLegendeBild--24h" title="{title}">' for title in titles)+'</div>')
    return (f'<input name="D" value="{day}">'+''.join(bars)).encode()


class HistoryTests(unittest.TestCase):
    meta = {"url": "https://example.test/history", "fetched_at": "2026-10-30T13:00:00Z", "sha256": "test"}

    def test_alignment_unknown_slots_transitions_and_point_only_labels(self):
        directions = ["25"]*24+["07"]*24
        directions[6] = None
        records = parse_day(page(directions=directions), date(2026, 7, 20), self.meta)
        self.assertEqual(records[0]["display_from"], "2026-07-19T22:00:00Z")
        self.assertEqual(records[6]["operating_direction"], "unknown")
        self.assertEqual(records[24]["operating_direction"], "07")
        points = training_points(records)
        self.assertNotIn("2026-07-20T10:00:00Z", {p["valid_from"] for p in points})
        with TemporaryDirectory() as folder:
            path = Path(folder)/"labels.csv"
            write_csv(path, points)
            labels = load_labels(path)
        at = parse_time(points[0]["valid_from"])
        self.assertIsNotNone(label_at(labels, at))
        self.assertIsNone(label_at(labels, at+timedelta(minutes=1)))
        self.assertIsNone(label_at(labels, at, known_by=at))
        self.assertEqual(change_scores({}, labels, 24)["reason"], "point_labels_do_not_establish_exact_switch_times")

    def test_wrong_date_truncated_page_and_dst_are_rejected(self):
        for body, day in [(page(), date(2026, 7, 21)),
                          (page(directions=["25"]*47), date(2026, 7, 20)),
                          (page("25.10.2026"), date(2026, 10, 25))]:
            with self.assertRaises(ValueError):
                parse_day(body, day, self.meta)
