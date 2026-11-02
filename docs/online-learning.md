# Online learning: the forecast learns from its own errors every hour

Added 2 November 2026 at the user's request (an extension, not a challenge-PDF deliverable).

## What it does

Every refresh (the UI triggers one every 10 minutes; once per clock hour a new issue is archived):

1. **Remember** the 48 hourly forecasts we published: raw wind speed, wind direction and 2 m temperature, plus the learned value we actually showed.
2. **Verify** every archived forecast whose valid time has passed and whose DWD station 01420 (Frankfurt Airport) measurement has arrived. The checks are the same quality rules as the wind model: QN 2/3, an exact valid-time match, and no nearest-time or future joins.
3. **Score first, then learn** (test-then-train). The error of the value we *published* is logged before the model sees the measurement. Only then is the model updated, so every reported score is out of sample.
4. **Correct** the new 48-hour forecast with the updated model.

What we call it: this is **supervised online learning**. The method is adaptive model output statistics, a time-decayed recursive regression, which is the weather-service practice for station-level bias correction. It is **not reinforcement learning**. There is no action, policy or reward, only forecast error. Calling it RL would not survive a technical question from FraAlliance, DFS or DWD. A genuine RL framing would need a decision with a cost (for example, when to recommend a runway-direction or staffing change) and is a possible later step.

## Model

The model is one weighted ridge regression per *(weather model, variable, lead bucket)*:

- **Weather models:** ICON-D2 and ICON-EU.
- **Variables:** wind as u/v, and temperature.
- **Lead buckets:** 1–3, 4–6, 7–12, 13–24 and 25–48 h.

Inputs are the raw forecast, the UTC hour (sin/cos) and an intercept. Three settings control learning:

- **Shrinkage:** the model is pulled toward the raw forecast with a prior worth 24 verified hours. A new bucket starts as exactly the raw forecast.
- **Forgetting:** older errors fade with a 720-hour time constant, so the model follows seasonal and regime changes.
- **Equal weight per hour:** each verified hour counts once per bucket, however many issues forecast it.

Large corrections fall back to raw: more than 15 kt of wind change or more than 8 °C of temperature change.

The code is pure standard library (`fra_forecast/online.py`), so the live pipeline does not need the optional ML dependencies.

The 720 h memory and the 24 h prior were chosen on the ICON-EU replay of issues from 7 May to 2 September only. The grid covered memory of 72–720 h, prior of 6–72 h, and diurnal terms on or off. Earlier fixed-step bias (EWMA) and unregularised RLS variants were rejected on the same data. EWMA did not help, and RLS diverged numerically. During that prototyping, raw-versus-corrected test-period totals for those rejected variants were printed once. The chosen configuration was not evaluated on the test period before it was selected.

## Measured results (chronological replay)

`python -m fra_forecast learn-online --days 30` replays archived forecasts hour by hour:

- **ICON-EU:** 180 days from `data/ml/dataset.json`.
- **ICON-D2:** the last 30 days of 00/06/12/18 UTC runs.

Each forecast is corrected only with errors measured before its issue time. Publication is assumed at ICON +4 h and DWD +1 h, as in the wind model.

**ICON-EU test issues, 21 September – 26 October 2026.** This is the same period, and the same cases per lead, as the [model card](model-card.md). Lower is better.

| Lead | Cases | Raw vector RMSE | Learned | Static Ridge (model card) | Raw speed MAE | Learned |
| --- | --- | --- | --- | --- | --- | --- |
| 1 h | 144 | 4.23 kt | **2.86 kt** | 2.95 kt | 2.91 kt | **1.51 kt** |
| 6 h | 144 | 4.49 kt | **2.88 kt** | 3.01 kt | 3.25 kt | **1.66 kt** |
| 24 h | 144 | 4.52 kt | **3.12 kt** | 3.21 kt | 3.22 kt | **1.84 kt** |
| All 1–48 h | 9,792 | 4.43 kt | **3.29 kt** (−26%) | — | 3.07 kt | **1.78 kt** |

Direction MAE improves only slightly (22.0° → 20.9° across all leads). Most of the gain is in wind speed, where the raw grid-point forecast is systematically off at the station.

**ICON-D2, the last 30 days.** This is the model the live dashboard mostly uses.

| Lead | Cases | Raw vector RMSE | Learned | Raw temperature MAE | Learned |
| --- | --- | --- | --- | --- | --- |
| 1 h | 120 | 4.29 kt | 3.13 kt | 0.96 °C | 0.93 °C |
| 6 h | 120 | 4.51 kt | 3.07 kt | 0.95 °C | 0.87 °C |
| 24 h | 117 | 4.91 kt | 3.87 kt | 1.14 °C | 1.04 °C |
| All | 5,046 | 4.56 kt | 3.56 kt (−22%) | 1.14 °C | 1.08 °C |

Temperature has only 30 days of history, so its gain is small. It will grow as the live loop accumulates errors.

Read these results with care:

- **The comparison with the static Ridge is indicative only.** It uses the same cases and targets, but this replay itself is retrospective.
- **Better wind error has not yet been shown to improve runway decisions.** Operating direction and RWY18 still use the raw forecast. The learned wind is published alongside it as `online` (see below). Feeding it into the 07/25 model needs retraining and its own evaluation.
- **Historical availability times are assumptions.** DWD retrospective values may contain later corrections.

## Using it

```bash
python -m fra_forecast learn-online --days 30   # warm start + backtest (cached runs are reused)
python -m fra_forecast refresh --live-only      # each refresh verifies, learns and corrects
python -m fra_forecast serve                    # GET /api/online-learning, /how-it-works
```

Files live in the ignored `data/online/` folder:

- `state.json` holds the model, pending forecasts and the 7-day verification log.
- `report.json` is served as `/api/online-learning`.
- `backtest.json` holds the full replay metrics.

Rerunning `learn-online` replaces the learned model with a fresh replay. Pending live forecasts and the live log are kept.

The loop only learns while refreshes run. Locally, that means keeping the dashboard open or scheduling `refresh --live-only` hourly.

On Vercel the state is per-instance and resets on a cold start. The deployment bundle (`scripts/prepare_deployment.py`) ships the warmed state. Durable, shared learning needs persistent storage, such as Vercel Blob or a small database, and is the next infrastructure step.

## JSON additions (additive, schema unchanged)

- `forecast[].temperature_c` is the raw 2 m temperature (°C). `null` when not supplied.
- `forecast[].online` has these fields:
  - `wind_speed_kt`, `wind_from_deg_true` and `temperature_c` are the learned values.
  - `raw_*` repeat the raw inputs.
  - `wind_gust_kt` is the raw gust; gusts are not corrected.
  - `runway_wind` holds the runway components of the learned wind.
  - `source_model`, `lead_bucket_hours`, `training_weight_hours`, `model_version` (`online-v1`).
  - `status` is one of `learned_correction`, `cold_start_raw_forecast`, `raw_forecast_guarded` or `unavailable_missing_forecast`.
- `online_learning` (top level) has `status`, `updated_at`, `verified_this_refresh`, `pending_forecasts`, `report_url` and `limitations`.
- `GET /api/online-learning` returns:
  - `live`: verified counts, cumulative raw and learned vector RMSE, and the last 7 days by lead (1/6/24 h).
  - `recent`: the last 24 one-hour-ahead forecasts against the measurement, as raw, learned and actual speed, direction and temperature.
  - `backtest` and `limitations`.
