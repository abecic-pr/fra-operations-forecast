# Backend data contract, version 1.1

Run `python3 -m fra_forecast refresh --live-only` from the repository root.
No third-party Python packages or API keys are needed. Refreshes are manual via
the command or API. The command exits nonzero if no forecast hours are available;
partial source failures are recorded in the JSON and may still produce usable output.

## Frontend file: `data/forecast.json`

All timestamps are ISO 8601 UTC. Wind speeds are knots; directions are the
direction wind comes **from**, measured clockwise from true north. Missing values
are `null`, never zero. `forecast` always contains 48 whole-hour points strictly
after `generated_at`; `lead_time_hours` can therefore be fractional.

| Field | Meaning |
| --- | --- |
| `schema_version`, `generated_at`, `ruleset` | Contract, freshness and versioned challenge thresholds |
| `observed_operations` | Current public UNH/DFS direction snapshot; official RWY18 status remains unknown |
| `current_weather`, `metar`, `dwd_observation` | Selected latest observation and the separate provider observations |
| `current_runway_wind` | Headwind, tailwind, mean/gust crosswind, margins and weather suitability for 07/25/18 |
| `forecast[]` | Valid time, model, source, wind fields, estimated direction and RWY18 weather state |
| `forecast[].runway_wind` | Per-runway derived wind components when forecast data exists |
| `forecast[].reason_codes` | Rule decisions or missing-data explanation |
| `p_od07`, `p_od25`, `p_rwy18_weather_usable` within each point | Always `null` for the deterministic baseline |
| `next_operating_direction_change`, `next_rwy18_weather_change` | First rule-based change window; probability is `null` |
| `data_quality`, `limitations` | Missing sources, observation age, coverage and approximation details |

Consumers must handle absent optional fields on missing forecast points. Weather
states are `usable`, `not_usable`, or `unknown`. Direction is `07`, `25`, or `null`.
The initial direction comes from the current observed snapshot when available;
otherwise it is inferred from wind and labeled accordingly. It is not official
airport status. Live model-run timestamps are unknown and remain `null`.

ICON-D2 supplies 15-minute inputs where available; ICON-EU hourly inputs cover
the remaining horizon. Hourly samples cannot resolve the >30-minute persistence
rule precisely. Gust crosswind uses mean direction when gust direction is absent.
Missing gust data produces unknown suitability unless a known component already
exceeds a limit. These limitations must travel with the output.

## Historical outputs

- `observations.csv`: DWD wind and gust observations, converted from m/s to knots.
- `metar-history.csv`: IEM EDDF observations, keeping raw METAR text.
- `archived-forecasts.json`: separate daily ICON-D2 model runs.
- `training-dataset.csv`: forecast inputs, baseline results, future reference
  weather, and independent operations labels if supplied. Fields beginning with
  `reference_` or `target_` are evaluation data, never prediction inputs.
- `dataset-report.json`: row counts, missing fields, time validation, and wind
  forecast diagnostics at 1/6/24 hours. Operational accuracy is not fabricated.
- `operations-snapshots.jsonl`: newly retrieved current operations snapshots;
  the page's `since` value is not used to invent historical labels.
- `sources.json` and `raw/`: URLs, retrieval times, response hashes and raw
  responses. Successive live responses are retained.

Label CSV intervals use `valid_from <= time < valid_to`, explicit timezones,
nonoverlapping intervals, and a nonempty source. `available_at` controls whether
a label may initialize a historical forecast. Direction is `07`, `25`, blank or
`unknown`; RWY18 weather suitability is `0`, `1`, blank or `unknown`. Keep actual
runway use and official operational status separate from weather suitability.

Historical publication time is estimated as model-run time plus four hours;
DWD historical observations use an estimated one-hour delay. These are unverified
assumptions. Resolve them before claiming a leakage-free backtest. Wind correction
training and held-out wind evaluation are implemented; see [wind-ml.md](wind-ml.md).
Actual operating-direction training and evaluation still require independent labels.

## Additive ML fields in version 1.1

Existing raw wind fields, rule outputs, baseline `p_*` fields and their semantics
are retained. The top-level `probability_status` describes that legacy baseline.
Use the separate `ml_model` and per-hour `ml.probability_status` for ML status.

`forecast_reference_time` is the UTC whole-hour reference immediately before
generation. Its future targets are exactly reference+1 through reference+48 hours.
`generated_at` remains the actual retrieval/generation time; existing fractional
`lead_time_hours` remains measured from generation. `ml.lead_time_hours` is the
integer horizon measured from the hourly reference. ML source runs are selected
as available by the reference, with availability assumptions explicitly recorded.

Each `forecast[]` point adds `ml`:

| Field | Meaning |
| --- | --- |
| `wind_speed_kt`, `wind_from_deg_true`, `wind_gust_kt` | Validation-selected corrected winds, or explicitly labeled raw fallback |
| `raw_wind_speed_kt`, `raw_wind_from_deg_true`, `raw_wind_gust_kt` | The exact ICON-EU inputs when inference succeeds |
| `source_model`, `model_run_at`, `model_lead_hours`, `fetched_at` | Explicit source run and retrieval provenance |
| `available_at`, `availability_basis`, `availability_verified` | Metadata-confirmed live availability, or an explicit estimated delay |
| `model_version`, `selected_corrections` | Artifact identity and wind/gust validation gates |
| `prediction_status`, `fallback_reason` | `ml_corrected`, `raw_icon_eu_validation_fallback`, or `fallback_raw_forecast` |
| `p_rwy18_weather_usable`, `probability_status` | Provisional weather-suitability estimate, or `null` with an unavailable status |
| `runway_wind` | Components and challenge-rule weather states from the selected winds |
| `p_od07`, `p_od25` | `null`: no operating-direction model has independent labels |

Calm predictions below 0.5 kt have unknown direction. Missing gusts remain `null`.
The `ml_model` summary includes availability, selected corrections, partition
dates, test scores and limitations. `/api/model-metrics` returns the full report.
Missing, corrupt, dependency-incompatible or unsupported artifacts retain the
raw forecast and report an explicit fallback. No ML dependency is required to
run the baseline. ML output does not replace the baseline's direction-change forecast.

## Local JSON API and frontend integration

Start `python3 -m fra_forecast serve`. The server exposes these routes at
`http://127.0.0.1:8000`, with no HTML, static UI assets, or directory listing:

| Route | Result |
| --- | --- |
| `GET /api/forecast` | Version 1.1 snapshot, preserving baseline fields and adding separate ML blocks |
| `GET /api/sources` | The latest source diagnostics |
| `GET /api/model-metrics` | Full locally trained model evaluation, or 404 if unavailable |
| `POST /api/refresh` | Fetch current data and return the new snapshot |

The refresh action requires the `X-FRA-Refresh: 1` header and rejects a different
browser origin. Only one refresh runs at a time. There is no automatic polling
of external providers. Baseline field meanings and calculations are unchanged.

For frontend development, proxy `/api/*` through the frontend's own server to
this loopback API. Preserve the browser-facing `Host` header on proxied requests
so the refresh origin check can match it. CORS is not enabled. A frontend server
can also read the saved JSON directly.

```javascript
const forecast = await fetch('/api/forecast').then(response => response.json());
// Explicit refresh; callers should handle non-2xx errors and source_errors.
const updated = await fetch('/api/refresh', {
  method: 'POST',
  headers: { 'X-FRA-Refresh': '1' },
}).then(response => response.json());
```

Missing files return 404, a concurrent refresh returns 409, and a rejected
origin or missing refresh header returns 403. Individual provider failures may
still return a partial snapshot with HTTP 200: inspect `data_quality.source_errors`
and `forecast_hours_available`. A refresh failure outside that fallback returns
502. Responses are not cached.

The temporary inspection UI has been removed. The teammate owns the replacement
UI. Preserve the distinctions between observations, forecasts, predictions,
missing gusts, weather suitability, observed use, and official runway status.

## Live observation comparison extension

The local UI now uses the live API and requests refreshed sources every 10 minutes while visible, with read-only polling every 30 seconds and a manual refresh control. The API itself still performs no autonomous background polling.

`GET /api/verification` returns screened provisional DWD station 01420 mean-wind observations and archived issued forecasts, while accepting additive `/api/forecast` schemas 1.0 and 1.1. The archive is `data/issued-forecasts.jsonl`. Only predictions valid after actual archive time are saved; past values are not backfilled. The green trace requires source/hash, station, timestamp, finite-value and QN 2/3 checks. These measurements remain provisional. See [frontend wind integration](frontend-wind.md) for comparison rules and refresh behavior.

`POST /api/chat` adds read-only airport/flight questions using a backend OpenAI key.
It has its own response schema and leaves the existing forecast/departure outputs
unchanged. See [the chatbot contract](chatbot.md) for configuration, request and
response fields, source evidence, history limits and error handling.

## Additive comparison and operating-direction outputs

`forecast[].direction_forecast` and top-level `operating_direction_outlook` now
provide explicit eastbound/westbound movement, landing approach side/runway ends,
Centre departure runway, and the separate southbound RWY18 interpretation.
They are present in both forecast endpoints. See the exact [07/25 contract](operating-direction.md).
Weather-derived output is labeled by its basis and never filled with invented
actual-OD probabilities; existing baseline and learned fields are preserved.

Implementation commands, validation policy, and examples are in
[model-comparison.md](model-comparison.md). The snapshot stays version 1.1; the
following optional blocks do not change legacy baseline or departure fields.

- `forecast[].operations_ml`: `status`, `reason` when unavailable, learned
  `operating_direction`, `p_od07`, `p_od25`, and `certainty_score`. Available
  predictions also have `model_version`, `probability_status`,
  `certainty_basis: model_class_probability`, and `initial_direction_known`.
  All learned values are null without a compatible independently trained artifact.
- `operations_model`: artifact availability/reason and `next_change`. Its method
  is `predicted_hourly_class_change`; earliest/latest bracket the first class
  change, with null event probability. Unknown initial state is not a change.
  A missing interval widens the window and marks `uncertain_due_to_gap`.
- Existing per-hour `operating_direction` and top-level change remain the rule
  baseline. `forecast[].ml` remains the legacy wind artifact and retains its
  probability identity. Read the separate comparison endpoint for the newly
  selected wind correction; do not mix a model's wind with another's probability.

| GET route | Saved JSON and meaning |
| --- | --- |
| `/api/discovery` | `comparison/discovery.json`: coverage, missing fields, validation patterns, bounded GFS probe and source provenance |
| `/api/model-comparison` | `comparison/evaluation.json`: immutable experiment ID, dataset hash, partitions, validation policy, exploratory test and calibration reports |
| `/api/forecast-comparison` | `comparison/forecast.json`: 48 aligned candidate/selected forecasts and disagreement |
| `/api/forecast-agent` | `comparison/agent.json`: last coordinator result, configuration/failure status, numeric decision, explanation, inspected evidence refs and tool trace |
| `/api/operations-metrics` | `operations-evaluation.json`: independent-label OD report or explicit unavailable reason |

These routes are read-only and return 404 until their command has produced a
file. They do not train, refresh, or invoke a paid model. Saved comparison reports
use schema `1.0` independently of the main forecast snapshot.

`forecast-comparison` contains `model_version`, `experiment_id`,
`forecast_reference_time`, `generated_at`, `snapshot_generated_at`,
`snapshot_age_seconds`, `status`, `policy`, `source_errors`, `model_error`,
`limitations`, `next_rule_direction_change`, and the copied `operations_model`.
Each `forecast[]` item has `valid_time`, integer `lead_time_hours`, `candidates`,
`selected`, `disagreement`, and the existing learned `operations_ml` block.

Candidate keys: `raw_icon_eu`, `persistence`, `boosting_correction`,
`linear_correction`, `equal_blend`, `raw_gfs`. Each contains wind in knots/degrees
true, `source_model`, source run/availability/retrieval metadata,
`prediction_status`, `selection_eligible`, rule OD/runway components, and separate
`p_rwy18_weather_usable` / `probability_status`. Persistence instead carries its
observation timestamp. Unavailable values are null; only raw and selected
candidates have their own calibrated residual pools. `raw_gfs` is unranked.

`selected` adds `policy_winner`, `effective_candidate`, exact `weights`, and
`fallback_reason`. Its OD is still deterministic. `disagreement` has candidate
count, speed/gust ranges, largest vector difference, and conflicting RWY18
weather states; it is descriptive, not probabilistic uncertainty.

The comparison is `stale_snapshot` after two hours, `unavailable` if every
selected wind is missing, otherwise `available`; inspect each hour for partial
coverage. A newly generated comparison can still refer to an old snapshot.
The coordinator rechecks age and matching experiment IDs before recommending
the saved policy. Preserve these caveats in the UI.

Submission exports use a separate internal schema `1.0`: 48 rows per explicit
issue, with source/model metadata and null learned OD when unavailable.
`report.json` carries coverage, artifact/data identities, availability assumptions,
and `jury_schema_confirmed: false`; `incomplete` is not submission-ready.

The merged visual dashboard assistant is preserved separately at `/api/weather-bot`, `/api/weather-bot/status` and `/api/weather-bot/preview`; Antonio’s `/api/chat` contract is unchanged. Both use backend-only credentials and remain disconnected when no key is configured.
