from datetime import datetime
import tempfile
import unittest
from unittest.mock import patch
from fra_forecast.domain import UTC
from fra_forecast.traffic import refresh_traffic
from fra_forecast.departures import normalize_flight

class TrafficTests(unittest.TestCase):
    def test_arrived_flights_are_excluded(self):
        self.assertEqual(normalize_flight({'status':'Arrived'},'2026-10-30T12:00:00Z','arrivals')[1],'finished_or_cancelled')

    def test_sources_and_null_assignments_are_preserved(self):
        row={'flight_id':'a','flight_number':'LH 123','destination':'London','aircraft_type':'A320',
             'scheduled_departure_at':'2026-10-30T13:00:00Z','estimated_departure_at':None,
             'status':'Scheduled','fetched_at':'2026-10-30T12:00:00Z'}
        def collect(*args,**kwargs):
            return [row],{'url':'https://www.frankfurt-airport.com/'+kwargs['flighttype'], 'status':'partial'}
        with tempfile.TemporaryDirectory() as root,patch('fra_forecast.traffic.fetch_departures',side_effect=collect):
            result=refresh_traffic(root,datetime(2026,10,30,12,tzinfo=UTC),client=object())
        self.assertEqual({f['operation'] for f in result['flights']},{'landing','departure'})
        self.assertEqual(len({f['id'] for f in result['flights']}),2)
        self.assertTrue(all(f['assigned_runway'] is None and f['position'] is None for f in result['flights']))
        self.assertEqual(result['sources']['arrivals']['status'],'partial')
