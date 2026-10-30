# FRA Operations Forecast - model card

30 October 2026 | Hackathon research demo | Partial challenge completion

## Purpose and outputs

48 hourly forecasts of Frankfurt wind and provisional RWY18 weather usability. The separate Section 3 baseline predicts airport-wide 07/25 and change windows. Learned actual OD, certainty, and change accuracy remain unavailable without independent historical labels. Weather suitability is not official runway status or actual use.

## Model and key drivers

Validation selected Ridge residual correction (alpha=1) over raw ICON-EU, boosting, and a fixed equal blend; observation persistence is a reference. Inputs: raw u/v wind, gust and missing indicator, model lead, UTC hour and season. Train-only imputation/scaling; no importance ranking claimed. RWY18 probabilities resample 256 joint residual draws from separate calibration pools. The optional AI coordinator explains the frozen selection; it cannot change numeric weights.

## Sources and time design

[Open-Meteo explicit ICON-EU runs](https://open-meteo.com/en/docs/single-runs-api) supply forecast inputs; [DWD station 01420](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/) supplies 10-minute wind and preceding-hour maximum gust targets. Live context: [AWC EDDF METAR](https://aviationweather.gov/data/api/) and [UNH/DFS current OD](https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/). [GFS via Open-Meteo](https://open-meteo.com/en/docs/gfs-api) passed four 96-hour probes but has no ranked historical evaluation. Source retrieval metadata and hashes are saved.

Issue-date partitions (2026): train Apr 30-Aug 15; selection Aug 16-Sep 02; calibration Sep 03-20; test Sep 21-Oct 26, targets through Oct 29. Earlier targets crossing the next partition were purged (1,224 rows). Selection used 3,248 matched 1-48 h cases. Historical forecast availability assumes four hours for ICON-EU, six for GFS; observations assume one hour. Publication history and later DWD corrections are unverified.

## Measured quality - lower scores are better

Validation vector RMSE: raw 5.517 -> selected 4.377 kt; gust MAE: 3.751 -> 3.019 kt. Below: previously inspected test period, explicitly exploratory; 144 cases per horizon. Wind errors are knots. RWY18 Brier is compared with Section 3 on the same cases.

| Lead | Raw vector RMSE | Selected vector RMSE | Selected gust MAE | Selected RWY18 Brier | Section 3 Brier |
| --- | --- | --- | --- | --- | --- |
| 1 h | 4.232 | 2.951 | 2.473 | 0.000016 | 0.000000 |
| 6 h | 4.489 | 3.005 | 2.704 | 0.006957 | 0.006944 |
| 24 h | 4.518 | 3.209 | 2.680 | 0.006997 | 0.006944 |

Across 1-48 h: selected Brier 0.001195 vs always-usable 0.001157 (6,912 cases); matched Section 3 comparison 0.001197 vs 0.001159 (6,902 cases). Eight adverse forecast cases represent only ONE distinct adverse timestamp; all were missed at probability threshold 0.5, with zero false warnings. No reliable rare-event calibration or operational baseline improvement is established. Actual-OD accuracy and change timing cannot yet be scored.

## Limits and delivery status

Probabilities: provisional_low_event_coverage. Hourly inputs cannot resolve exact >30-minute persistence or within-hour reversals; missing gusts stay missing. Correction candidates share ICON-EU inputs and are correlated. Season/generalization and untouched holdout performance remain unverified. The brief does not supply jury dates, issue times, or file schema. Replay/export works: an internal demo issue produced 48 weather rows, null learned OD, and an explicit incomplete report. Agent provider execution requires configuration and is unverified. This is not an operational aviation system.

## Reproducibility

Rules: fraalliance-2026-v1 (landing 10 kt, departure 15 kt, crosswind >40 kt, persistence >30 min). Model: wind-comparison-v1; experiment ed131c7b15d7291b15a5; scikit-learn 1.9.1. Dataset SHA-256: 66fe17ae25c62ea2fda4031a678e4bfe379f27a268ea98dc4dfd56098aa2de1b. Frozen artifacts, source metadata, reports and dataset are in the local demo bundle; commands and full identities are in docs/model-comparison.md. Model fitting/selection/calibration cutoff: 2026-09-21 00:00 UTC.
