from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from fra_forecast.departures import (Runway18Weather, build_departure_snapshot,
                                    fetch_departures, normalize_flight)
from fra_forecast.domain import iso, parse_time, runway_conditions

NOW=parse_time("2026-10-30T12:00:00Z")


def flight_raw(**changes):
    return {"id":"test-fixture-001","fnr":"TEST 001","ac":"A320","alname":"Test fixture airline",
            "iata":"AAA","apname":"Fixture airport","sched":"2026-10-30T14:30:00+0100",
            "esti":"2026-10-30T15:00:00+0100","status":"Gate open","cs":["TEST 002"],
            "lu":"2026-10-30T13:00:00+0100",**changes}


def point(at, speed=5, direction=180, gust=10, probability=.8):
    weather={"wind_speed_kt":speed,"wind_from_deg_true":direction,"wind_gust_kt":gust}
    return {"valid_time":iso(at),**weather,"model":"icon_d2",
            "runway_wind":runway_conditions(weather),
            "ml":{**weather,"source_model":"icon_eu","model_run_at":iso(NOW-timedelta(hours=6)),
                  "prediction_status":"raw_icon_eu_validation_fallback",
                  "probability_status":"provisional_low_event_coverage",
                  "p_rwy18_weather_usable":probability,"runway_wind":runway_conditions(weather)}}


def snapshot(points=None):
    return {"generated_at":iso(NOW),"forecast":points or [point(NOW+timedelta(hours=h)) for h in (1,2,3)]}


class DepartureTests(unittest.TestCase):
    def test_offsets_delays_codeshares_and_takeoff_time_are_separate(self):
        flight,error=normalize_flight(flight_raw(),iso(NOW))
        self.assertIsNone(error)
        self.assertEqual(flight["scheduled_departure_at"],"2026-10-30T13:30:00Z")
        self.assertEqual(flight["assessment_at"],"2026-10-30T14:00:00Z")
        self.assertEqual(flight["assessment_time_basis"],"estimated_departure_proxy")
        self.assertEqual(flight["codeshares"],["TEST 002"])
        self.assertIsNone(flight["estimated_takeoff_at"])
        self.assertIsNone(flight["assigned_runway"])

    def test_scheduled_time_is_only_a_proxy(self):
        flight,_=normalize_flight(flight_raw(esti=None),iso(NOW))
        self.assertEqual(flight["assessment_time_basis"],"scheduled_departure_proxy")
        self.assertFalse(flight["assessment_time_is_takeoff_estimate"])

    def test_trains_cancelled_and_off_block_are_excluded(self):
        self.assertEqual(normalize_flight(flight_raw(ac="TRS"),iso(NOW))[1],"ground_transport")
        for status in ("Cancelled","Canceled","Departed","Off Block"):
            self.assertEqual(normalize_flight(flight_raw(status=status),iso(NOW))[1],"finished_or_cancelled")

    def test_naive_time_is_rejected(self):
        self.assertEqual(normalize_flight(flight_raw(sched="2026-10-30T14:30"),iso(NOW))[1],"invalid_timestamp")

    def test_exact_weather_probability_is_not_a_runway_assignment_probability(self):
        weather=Runway18Weather(snapshot(),NOW)
        result=weather.assess(NOW+timedelta(hours=2))
        self.assertEqual(result["time_alignment"],"exact_hour")
        self.assertEqual(result["p_weather_usable"],.8)
        self.assertIsNone(result["p_departure_from_rwy18"])
        self.assertEqual(result["takeoff_direction"],"south")
        self.assertEqual(result["assignment_status"],"unknown")

    def test_half_hour_keeps_probability_samples_separate(self):
        weather=Runway18Weather(snapshot([point(NOW+timedelta(hours=1),probability=.2),
                                        point(NOW+timedelta(hours=2),probability=.9)]),NOW)
        result=weather.assess(NOW+timedelta(hours=1,minutes=30))
        self.assertEqual(result["time_alignment"],"bracketing_hours")
        self.assertIsNone(result["p_weather_usable"])
        self.assertEqual(result["sample_probability_range"],{"min":.2,"max":.9})
        self.assertEqual(len(result["forecast_samples"]),2)

    def test_changing_weather_and_no_extrapolation_beyond_end(self):
        weather=Runway18Weather(snapshot([point(NOW+timedelta(hours=1)),
                                        point(NOW+timedelta(hours=2),speed=20,direction=0,gust=25)]),NOW)
        self.assertEqual(weather.assess(NOW+timedelta(hours=1,minutes=30))["weather_state"],"changing")
        self.assertEqual(weather.assess(NOW+timedelta(hours=2,minutes=1))["time_alignment"],"outside_forecast_horizon")

    def test_near_term_proxy_gaps_staleness_and_missing_forecast(self):
        weather=Runway18Weather(snapshot(),NOW+timedelta(hours=3))
        self.assertEqual(weather.assess(NOW+timedelta(minutes=20))["time_alignment"],"next_hour_proxy")
        self.assertEqual(weather.assess(NOW+timedelta(hours=2))["data_status"],"stale")
        self.assertEqual(Runway18Weather({},NOW).assess(NOW)["time_alignment"],"forecast_unavailable")
        gaps=Runway18Weather(snapshot([point(NOW+timedelta(hours=1)),point(NOW+timedelta(hours=3))]),NOW)
        self.assertEqual(gaps.assess(NOW+timedelta(hours=2))["time_alignment"],"forecast_gap")

    def test_live_feed_pagination_does_not_trust_false_hasnext(self):
        class Client:
            calls=[]
            def json(self,source,url):
                self.calls.append(url)
                if len(self.calls)==1:
                    return {"data":[flight_raw()],"hasnext":False}, {"fetched_at":iso(NOW)}
                return {"data":[flight_raw(),flight_raw(id="test-fixture-003",fnr="TEST 003",
                        sched=iso(NOW+timedelta(hours=4)),esti=None)],"hasnext":False}, {"fetched_at":iso(NOW)}
        client=Client()
        with patch("fra_forecast.departures.time.sleep"):
            flights,source=fetch_departures(client,NOW,NOW+timedelta(hours=2),max_pages=3,progress=lambda *a,**k:None)
        self.assertEqual(len(client.calls),2)
        self.assertEqual(len(flights),1)
        self.assertTrue(source["coverage_complete"])

    def test_repeated_page_and_provider_failure_are_explicit(self):
        class Client:
            def json(self,*args):
                return {"data":[flight_raw()]},{"fetched_at":iso(NOW)}
        with patch("fra_forecast.departures.time.sleep"):
            flights,source=fetch_departures(Client(),NOW,NOW+timedelta(hours=48),progress=lambda *a,**k:None)
        self.assertEqual(source["coverage_end_reason"],"repeated_page")
        self.assertEqual(source["status"],"partial")
        class Broken:
            def json(self,*args): raise OSError("fixture unavailable")
        flights,source=fetch_departures(Broken(),NOW,NOW+timedelta(hours=48),progress=lambda *a,**k:None)
        self.assertEqual(source["status"],"unavailable")
        self.assertEqual(flights,[])

    def test_output_contains_only_runway18_assessments_and_no_invented_assignments(self):
        flight,_=normalize_flight(flight_raw(),iso(NOW))
        result=build_departure_snapshot([flight],{"status":"available"},snapshot(),NOW)
        self.assertEqual(result["runway"],"18")
        self.assertEqual(result["flight_count"],1)
        self.assertNotIn("p_od07",result["departures"][0])
        self.assertIsNone(result["departures"][0]["runway18"]["p_departure_from_rwy18"])


if __name__=="__main__": unittest.main()
