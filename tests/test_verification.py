import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from fra_forecast.domain import parse_time
from fra_forecast.verification import comparison_payload, remember_forecast

NOW = parse_time('2026-10-30T12:30:00Z')


def write_source(root, rows, valid_hash=True):
    folder = Path(root) / 'raw/dwd_wind_now'
    folder.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('produkt_test.txt', 'STATIONS_ID;MESS_DATUM;QN;FF_10;DD_10\n' + '\n'.join(rows))
    body = buffer.getvalue()
    (folder / 'sample.bin').write_bytes(body)
    (folder / 'sample.json').write_text(json.dumps({
        'source': 'dwd_wind_now', 'status': 'ok', 'http_status': 200,
        'fetched_at': '2026-10-30T12:20:00Z',
        'url': 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/10minutenwerte_wind_01420_now.zip',
        'sha256': hashlib.sha256(body).hexdigest() if valid_hash else 'incorrect',
    }))


class VerificationTests(unittest.TestCase):
    def test_quality_time_and_source_checks(self):
        with tempfile.TemporaryDirectory() as root:
            write_source(root, ['01420;202610301200;2;3.6;0',
                                '01420;202610301210;1;3.6;0',
                                '01420;202610301230;2;3.6;0',
                                '99999;202610301140;2;3.6;0',
                                '01420;202610301150;2;-999;0'])
            result = comparison_payload(root, NOW)
            self.assertEqual(len(result['observations']), 1)
            point = result['observations'][0]
            self.assertAlmostEqual(point['tailwind_kt'], 3.6 * 1.943844)
            self.assertTrue(point['eligible'])
            self.assertTrue(point['provisional'])
            self.assertEqual(point['quality_code'], '2')

    def test_hash_mismatch_excludes_measurements(self):
        with tempfile.TemporaryDirectory() as root:
            write_source(root, ['01420;202610301200;2;3.6;0'], valid_hash=False)
            self.assertEqual(comparison_payload(root, NOW)['observations'], [])

    def test_archives_never_backdate_or_rewrite(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = {'schema_version': '1.0', 'generated_at': '2026-10-30T10:00:00Z', 'forecast': [
                {'valid_time': '2026-10-30T10:00:00Z', 'runway_wind': {'18': {'tailwind_kt': 100}}},
                {'valid_time': '2026-10-30T12:00:00Z', 'runway_wind': {'18': {'tailwind_kt': 9}}},
            ]}
            remember_forecast(root, snapshot, parse_time('2026-10-30T11:00:00Z'))
            snapshot['forecast'][1]['runway_wind']['18']['tailwind_kt'] = 999
            remember_forecast(root, snapshot, parse_time('2026-10-30T11:30:00Z'))
            records = comparison_payload(root, NOW)['issued_forecasts']
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['tailwind_kt'], 9)
            self.assertEqual(records[0]['issued_at'], '2026-10-30T11:00:00Z')

    def test_future_archive_is_not_used(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'issued-forecasts.jsonl'
            path.write_text(json.dumps({'issued_at': '2026-10-30T13:00:00Z',
                'generated_at': '2026-10-30T11:00:00Z', 'forecast': [
                {'valid_time': '2026-10-30T12:00:00Z', 'tailwind_kt': 9}]}) + '\n')
            self.assertEqual(comparison_payload(root, NOW)['issued_forecasts'], [])


if __name__ == '__main__':
    unittest.main()
