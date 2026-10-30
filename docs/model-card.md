# FRA Operations Forecast - model card

30 October 2026 | Research demo | Conditional OD probability improvement; partial challenge completion

## Purpose and models

48 hourly wind, RWY18 weather-usability probability, airport-wide 07/25 and certainty, and hourly change windows. Wind: validation-selected Ridge correction of ICON-EU u/v/gust. OD: equal probability blend of two balanced logistic classifiers. Both use forecast components, gust/missing flag, horizon, available initial OD and one-hour-old DWD wind/gust. The second adds runway-aligned wind, six-hour recency decay, UTC hour cycles and trailing 3/6-hour forecast winds. Train-only preprocessing; two purged development splits select the blend. RWY18 uses 256 joint residual draws. Weather suitability is distinct from official status or use.

## Sources and label quality

[Open-Meteo ICON-EU runs](https://open-meteo.com/en/docs/single-runs-api); [DWD 01420 wind/gust](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/); [DFLD actual direction based on Fraport](https://www.dfld.de/Mess/Language/MessHelpG.html). Live context: [AWC EDDF](https://aviationweather.gov/data/api/) and [UNH/DFS direction](https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/). [Open-Meteo GFS](https://open-meteo.com/en/docs/gfs-api) remains an unranked comparison source.

Recovered 182 days / 8,736 half-hour direction displays, Apr 30-Oct 29. Retained 4,259 hourly points only where adjacent display categories agree. These are provisional stable-state proxies, not exact switch intervals. Europe/Berlin alignment checked against METAR; Oct 25 DST day excluded. Source sampling instant is unverified; transition filtering makes the evaluation subset easier. History remains local, with retrieval times and hashes; redistribution rights unverified.

## Time design and probability limits

Issue partitions: train Apr 30-Aug 15; selection Aug 16-Sep 2; calibration Sep 3-20; test Sep 21-Oct 26, with overlapping targets purged. ICON publication assumes +4 h; DWD +1 h. Historical publication and later revisions are unverified. Retrieved historical OD is target-only, never backdated as initial state. Calibration's forward check lacks eastbound cases: OD probabilities remain uncalibrated. Certainty is max(class probability), not verified reliability.

## Measured 07/25 quality

Validation (3,199 cases): accuracy 92.53% -> 95.75%; balanced accuracy 92.60% -> 93.43%; Brier 0.07471 -> 0.03872. Earlier purged training check: accuracy 89.39% -> 93.84%. Below: inspected later period, explicitly exploratory; same stable-label cases. Higher accuracy / lower Brier is better.

| Lead | Cases | Rule accuracy | ML accuracy | Rule Brier | ML Brier |
| --- | --- | --- | --- | --- | --- |
| 1 h | 135 | 71.9% | 78.5% | 0.2815 | 0.1884 |
| 6 h | 134 | 78.4% | 77.6% | 0.2164 | 0.1853 |
| 24 h | 134 | 76.1% | 76.1% | 0.2388 | 0.1933 |

All 1-48 h (6,500 cases, 854 distinct targets): accuracy 74.72% -> 77.60%; balanced accuracy 74.79% -> 77.85%; Brier 0.25277 -> 0.18763. Probability scores improve at 1/6/24 h; 24 h accuracy ties; 6 h is one case behind (104 versus 105 correct). Initial-state persistence and exact switch timing are unscored because independent as-of states / exact intervals are absent.

## Wind, RWY18 and remaining delivery

Wind vector RMSE at 1/6/24 h: raw 4.232/4.489/4.518 -> Ridge 2.951/3.005/3.209 kt (144 cases each). RWY18 Brier at those leads: 0.000016/0.006957/0.006997 vs rules 0/0.006944/0.006944. All-hour matched Brier 0.001197 vs rules 0.001159; one distinct adverse timestamp, eight forecast cases, all missed at threshold 0.5. Rare-event skill is not established. Next change uses hourly class crossings; exact >30-minute persistence / within-hour reversals remain unresolved. Fresh holdout, precise switch labels, and jury dates/schema are outstanding.

## Reproducibility

Rules fraalliance-2026-v1: landing 10 kt, departure 15 kt, crosswind >40 kt, persistence >30 min. Wind wind-comparison-v1; OD operations-v3 / `277d8d037ca31002de2e`; scikit-learn 1.9.1. OD evidence cutoff `2026-10-30T13:39:14Z`; earlier replay excludes it. Code, commands, hashes, full metrics and limitations: docs/ml-improvement.md. The earlier delivery ZIP predates this OD extension.
