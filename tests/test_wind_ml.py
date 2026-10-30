from datetime import timedelta
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fra_forecast.domain import iso, parse_time
from fra_forecast.ml_data import build_rows, observation_target, uv
from fra_forecast.ml_live import enrich, explicit_live_run, load_artifact
from fra_forecast.pipeline import live_snapshot
from fra_forecast.sources import parse_dwd_zip
from fra_forecast.wind_ml import (ARTIFACT_VERSION, FEATURES, MODEL_VERSION,
                                  chronological_split, features)

try:
    import numpy as np
except ImportError:
    np = None

START = parse_time("2026-05-01T00:00:00Z")


def observation(at, speed=5, direction=359, gust=10):
    return {"valid_time":iso(at),"wind_speed_kt":speed,"wind_from_deg_true":direction,
            "wind_gust_kt":gust,"gust_from_deg_true":direction,
            "wind_quality_code":"3","gust_quality_code":"3"}


def sample(day=0, hour=0, lead=1):
    decision=START+timedelta(days=day,hours=hour)
    return {"decision_time":iso(decision),"valid_time":iso(decision+timedelta(hours=lead)),
            "forecast_available_at":iso(decision),"model_run_at":iso(decision-timedelta(hours=4)),
            "lead_time_hours":lead,"model_lead_hours":lead+4,
            "raw_u_kt":1,"raw_v_kt":2,"raw_gust_kt":5}


class WindDataTests(unittest.TestCase):
    def test_direction_wraparound_and_calm(self):
        self.assertLess(math.dist(uv(10,359),uv(10,1)),0.4)
        self.assertEqual(uv(0,None),(0,0))
        self.assertIsNone(uv(10,None))
        self.assertIsNone(uv(10,999))

    def test_target_requires_exact_time_and_six_gust_samples(self):
        at=START+timedelta(hours=1)
        rows=[observation(at-timedelta(minutes=10*i),gust=10+i) for i in range(6)]
        index={r["valid_time"]:r for r in rows}
        self.assertEqual(observation_target(index,at)["target_gust_kt"],15)
        del index[iso(at-timedelta(minutes=20))]
        self.assertIsNone(observation_target(index,at)["target_gust_kt"])
        self.assertIsNone(observation_target(index,at+timedelta(minutes=10)))

    def test_quality_one_is_not_a_training_target(self):
        row=observation(START)
        row["wind_quality_code"]="1"
        self.assertIsNone(observation_target({iso(START):row},START))

    def test_wind_and_gust_quality_flags_survive_zip_parsing(self):
        import io, zipfile
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w") as archive:
            archive.writestr("produkt_test.txt","STATIONS_ID;MESS_DATUM;QN;FF_10;DD_10;eor\n1420;202605010000;3;2;359;eor\n")
        row=parse_dwd_zip(buffer.getvalue(),START,START+timedelta(hours=1))[0]
        self.assertEqual(row["wind_quality_code"],"3")
        self.assertAlmostEqual(row["wind_speed_kt"],2*1.943844)

    def test_features_ignore_all_future_targets_and_observations(self):
        row=sample()
        original=features(row)
        row.update(target_u_kt=999,target_gust_kt=999,persistence_u_kt=1000,target_operating_direction="07")
        self.assertEqual(original,features(row))
        self.assertEqual(len(original),len(FEATURES))

    def test_purge_all_target_overlap_between_partitions(self):
        rows=[sample(day,hour,lead) for day in range(60) for hour in (0,6,12,18) for lead in range(1,69)]
        groups,report=chronological_split(rows)
        self.assertGreater(report["purged_rows"],0)
        names=list(groups)
        for previous,current in zip(names,names[1:]):
            self.assertLess(max(r["valid_time"] for r in groups[previous]),
                            min(r["decision_time"] for r in groups[current]))
        bad={**rows[0],"forecast_available_at":iso(START+timedelta(hours=1))}
        with self.assertRaises(ValueError):
            chronological_split([bad]+rows[1:])

    def test_build_rows_uses_future_weather_only_as_targets(self):
        at=START+timedelta(hours=5)
        observations=[observation(at-timedelta(minutes=10*i)) for i in range(6)]
        weather={"valid_time":iso(at),"wind_speed_kt":8,"wind_from_deg_true":90,
                 "wind_gust_kt":12,"fetched_at":"2026-10-30T00:00:00Z"}
        rows=build_rows([{"run_at":iso(START),"hourly":[weather]}],observations)
        self.assertEqual(rows[0]["lead_time_hours"],1)
        self.assertAlmostEqual(rows[0]["raw_u_kt"],-8)
        self.assertIsNone(rows[0]["persistence_u_kt"])
        self.assertEqual(rows[0]["target_wind_speed_kt"],5)


class ArtifactTests(unittest.TestCase):
    def test_missing_and_incompatible_model_fallback(self):
        with TemporaryDirectory() as root:
            self.assertEqual(load_artifact(root)[2],"model_artifact_missing")
            folder=Path(root)/"models"/MODEL_VERSION
            folder.mkdir(parents=True)
            (folder/"manifest.json").write_text(json.dumps({"artifact_version":999,"features":FEATURES}))
            self.assertEqual(load_artifact(root)[2],"model_artifact_incompatible")

    def test_raw_values_and_48_hour_targets_survive_missing_model(self):
        hourly=[{**observation(START+timedelta(hours=h)),"model":"icon_eu","resolution_minutes":60} for h in range(49)]
        snapshot=live_snapshot(START,{"icon_eu":{"hourly":hourly}},None,[],None,[])
        raw=[r["wind_speed_kt"] for r in snapshot["forecast"]]
        with TemporaryDirectory() as root:
            enrich(snapshot,root,None)
        self.assertEqual(snapshot["schema_version"],"1.1")
        self.assertEqual(raw,[r["wind_speed_kt"] for r in snapshot["forecast"]])
        for hour,row in enumerate(snapshot["forecast"],1):
            self.assertEqual(parse_time(row["valid_time"]),START+timedelta(hours=hour))
            self.assertEqual(row["ml"]["lead_time_hours"],hour)
            self.assertIsNone(row["p_od07"])
            self.assertIsNone(row["ml"]["p_rwy18_weather_usable"])

    def test_live_metadata_is_as_of_the_hourly_reference(self):
        reference=START+timedelta(hours=12)
        class Client:
            def json(self,*args):
                return {"last_run_initialisation_time":(START+timedelta(hours=6)).timestamp(),
                        "last_run_availability_time":(START+timedelta(hours=10)).timestamp()},{}
        with patch("fra_forecast.ml_live.forecast",return_value={"hourly":[]}) as fetch:
            _,provenance=explicit_live_run(Client(),reference)
        self.assertTrue(provenance["availability_verified"])
        self.assertLessEqual(parse_time(provenance["available_at"]),reference)
        self.assertEqual(fetch.call_args.args[2],START+timedelta(hours=6))

    def test_short_newer_run_does_not_truncate_48_hour_forecast(self):
        reference = START+timedelta(hours=13)
        newer, older = START+timedelta(hours=9), START+timedelta(hours=6)
        class Client:
            def json(self, *args):
                return {"last_run_initialisation_time": newer.timestamp(),
                        "last_run_availability_time": (START+timedelta(hours=12)).timestamp()}, {}
        def data(run, hours):
            return {"hourly": [{"valid_time": iso(run+timedelta(hours=h)), "wind_speed_kt": 8,
                                "wind_from_deg_true": 70, "wind_gust_kt": None} for h in range(hours+1)]}
        with patch("fra_forecast.ml_live.forecast", side_effect=lambda client, model, run, **kw: data(run, 30 if run == newer else 72)):
            selected, provenance = explicit_live_run(Client(), reference)
        self.assertEqual(provenance["model_run_at"], iso(older))
        self.assertFalse(provenance["availability_verified"])
        self.assertEqual(provenance["run_selection_reason"], "older_run_has_more_supported_hours")
        self.assertIn(iso(reference+timedelta(hours=48)), [p["valid_time"] for p in selected["hourly"]])
        with patch("fra_forecast.ml_live.forecast", side_effect=[data(newer, 30), OSError("offline")]):
            partial, provenance = explicit_live_run(Client(), reference)
        self.assertEqual(provenance["model_run_at"], iso(newer))
        self.assertEqual(provenance["run_selection_reason"], "partial_newer_run_older_run_unavailable")


@unittest.skipIf(np is None,"Install the optional [ml] dependencies for numerical ML tests")
class NumericalTests(unittest.TestCase):
    def test_corrupt_artifact_is_a_fallback(self):
        import sklearn
        with TemporaryDirectory() as root:
            folder=Path(root)/"models"/MODEL_VERSION
            folder.mkdir(parents=True)
            bad=b"not a joblib artifact"
            (folder/"model.joblib").write_bytes(bad)
            (folder/"manifest.json").write_text(json.dumps({"artifact_version":ARTIFACT_VERSION,
                "features":FEATURES,"sklearn_version":sklearn.__version__,
                "model_sha256":hashlib.sha256(bad).hexdigest()}))
            self.assertEqual(load_artifact(root)[2],"model_artifact_invalid")

    def test_validation_fallback_and_gust_physical_bound(self):
        from fra_forecast.wind_ml import corrected
        class Correction:
            def __init__(self,value): self.value=value
            def predict(self,x): return np.full(len(x),self.value)
        artifact={"selected":{"wind":False,"gust":False},
                  "estimators":{"u":Correction(100),"v":Correction(100),"gust":Correction(-100)}}
        raw=np.array([[3,4,6]],dtype=float)
        np.testing.assert_array_equal(corrected(artifact,np.zeros((1,len(FEATURES))),raw),raw)
        low_gust=np.array([[3,4,4]],dtype=float)
        np.testing.assert_array_equal(corrected(artifact,np.zeros((1,len(FEATURES))),low_gust),low_gust)
        artifact["selected"]["gust"]=True
        result=corrected(artifact,np.zeros((1,len(FEATURES))),raw)
        np.testing.assert_array_equal(result[:,:2],raw[:,:2])
        self.assertEqual(result[0,2],5)

    def test_runway_limits_and_gust_direction(self):
        from fra_forecast.wind_ml import weather_outcome
        values=np.array([[0,-14.99,15],[0,-15,15],[40,0,40],[40.01,0,40.01],[0,20,45]],dtype=float)
        result=weather_outcome(values)
        np.testing.assert_array_equal(result,[1,0,1,0,1])
        self.assertEqual(weather_outcome(values[-1:],[90])[0],0)

    def test_missing_gust_is_unknown_and_does_not_hide_known_limit(self):
        from fra_forecast.wind_ml import weather_outcome
        result=weather_outcome(np.array([[1,2,np.nan],[0,-16,np.nan]]))
        self.assertTrue(np.isnan(result[0]))
        self.assertEqual(result[1],0)

    def test_joint_residual_probabilities_are_bounded_and_reproducible(self):
        from fra_forecast.wind_ml import probabilities
        pool=np.array([[0,-2,1],[0,2,-1]],dtype=float).repeat(60,axis=0)
        artifact={"calibration":{"5-12":pool}}
        rows=[sample()]
        predicted=np.array([[0,-14,20]],dtype=float)
        first=probabilities(artifact,rows,predicted)
        np.testing.assert_array_equal(first,probabilities(artifact,rows,predicted))
        self.assertGreater(first[0],0)
        self.assertLess(first[0],1)
        self.assertTrue(np.isnan(probabilities({"calibration":{}},rows,predicted)[0]))

    def test_brier_and_reliability_include_probability_one(self):
        from fra_forecast.wind_ml import probability_metrics
        result=probability_metrics([0,1,.5],[0,1,1])
        self.assertAlmostEqual(result["brier_score"],1/12)
        self.assertAlmostEqual(result["always_usable_brier_score"],1/3)
        self.assertEqual(sum(r["samples"] for r in result["reliability"]),3)

    def test_direction_error_wraps_and_excludes_calm(self):
        from fra_forecast.wind_ml import regression_metrics
        p=np.array([[*uv(10,359),15],[*uv(.1,90),1]])
        y=np.array([[*uv(10,1),15],[*uv(.1,270),1]])
        result=regression_metrics(p,y)
        self.assertAlmostEqual(result["direction_mae_deg"],2)
        self.assertEqual(result["direction_samples"],1)


if __name__ == "__main__":
    unittest.main()
