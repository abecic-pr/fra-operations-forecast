# Runway 18 departure assessment contract, version 1.0

This feature attaches RWY18 weather to upcoming flights from Frankfurt Airport's
public departure board. It is a list of FRA flights **assessed for RWY18 weather**,
not confirmed RWY18 departures. The source provides neither assigned runways nor
estimated wheels-off times. `p_departure_from_rwy18` remains `null`.

## Run and integrate

```bash
# Fetch weather, optional ML enrichment, and the flight-board records together.
python -m fra_forecast refresh --live-only

# Reuse saved weather and refresh only the flight list.
python -m fra_forecast refresh-departures --hours 48

python -m fra_forecast serve
```

`GET /api/runway18/departures` reads `data/runway18-departures.json`.
The weather snapshot links to it with `runway18_departures_url`. The departure
snapshot has its own schema version 1.0 and does not change weather schema 1.1.
All normalized timestamps are UTC; display timezone is Europe/Berlin. Speeds and
wind components are knots, directions are from true north.

The default horizon is 48 hours; `--hours` accepts 1–48. Normal weather refresh
also refreshes flights; use `--no-departures` for weather-only work. No automatic
external polling or retraining is added. The teammate owns the UI.

## Flight records

| Field | Meaning |
| --- | --- |
| `flight_id`, `flight_number`, `codeshares` | One primary service, with codeshares kept as aliases |
| `airline`, `aircraft_type`, `destination_iata`, `destination` | Published flight identity/context |
| `scheduled_departure_at`, `estimated_departure_at` | Times published by the board, distinct from takeoff |
| `estimated_takeoff_at`, `assigned_runway` | `null`; not supplied by this source |
| `assessment_at`, `assessment_time_basis` | Estimated departure when available, otherwise schedule; explicitly a proxy |
| `assessment_time_is_takeoff_estimate` | `false`; no taxi delay or wheels-off estimate is invented |
| `status`, `terminal`, `gate` | Published departure-board information |
| `source`, `source_url`, `source_updated_at`, `fetched_at` | Provenance and freshness |
| `runway18` | RWY18-only weather assessment described below |

Identified rail/bus services, cancelled services, already departed and off-block
records are excluded. Off-block services may still be taxiing; without a takeoff
estimate they are outside this upcoming-published-departure feature. Codeshares
are not expanded into multiple flights. Duplicate source IDs are merged.

## RWY18 weather and uncertainty

Each record's `runway18` specifies runway `18`, southbound takeoff, true heading
180 degrees, `assignment_status: unknown`, and `p_departure_from_rwy18: null`.
Those fields are separate from weather suitability and official runway status.

The weather matcher uses ML output when its prediction status is available,
including validation-selected raw ICON-EU fallback. Otherwise it uses the raw
weather/rule baseline. `forecast_samples` includes only RWY18 components, winds,
weather state, provisional weather probability and source-model provenance.

| `time_alignment` | Interpretation |
| --- | --- |
| `exact_hour` | Assessment time matches one forecast hour; its weather probability can be copied |
| `bracketing_hours` | Use the hourly forecast before and after the assessment time |
| `next_hour_proxy` | Before the first forecast hour, use that next hour only if within 60 minutes |
| `outside_forecast_horizon` | No extrapolation beyond the last forecast hour or more than 60 minutes before the first |
| `forecast_gap` | Missing hourly coverage prevents a continuous bracket |
| `forecast_unavailable` | No saved forecast points |

For a 14:30 assessment, show the 14:00 and 15:00 forecasts. Do not interpolate
their probabilities into a fabricated 14:30 estimate. The optional
`sample_probability_range` is the min/max of the provided probability samples,
not a confidence interval or probability of suitability throughout that interval.
`p_weather_usable` is populated only for an exact hourly match. Even then it is
weather at a departure-time proxy, not a probability that the flight uses RWY18.

`weather_state` is `usable`, `not_usable`, `unknown`, or `changing`. `changing`
means the bracketing samples disagree. Matching usable endpoints does not establish
continuous usability between samples; `scope` explicitly says
`weather_at_forecast_samples_only`. ML probability statuses and the low-event
coverage limitation travel with each sample. Probability fields stay null when
the model/calibration data is unavailable.

The assessment includes the weather snapshot timestamp, age, and `data_status`;
a weather snapshot older than two hours is marked stale. Forecast data can end
before the departure-list horizon, producing unknown assessments near its end.
The challenge's 15 kt departure tailwind and >40 kt crosswind limits are retained.

## Source and coverage

The official [departure board](https://www.frankfurt-airport.com/en/flights-and-transfer/departures.html)
uses a public JSON feed at
`https://www.frankfurt-airport.com/en/_jcr_content.flights.json/filter`.
This is a website interface, not a documented API availability guarantee.
Requests use its public `flighttype`, `time`, `page`, `perpage` and `lang`
parameters, with no account or API key. Raw responses and request metadata are
cached separately under `data/raw/fra_departures/` and
`data/runway18-departures-sources.json`.

The query starts six hours before refresh to catch delayed flights. Flights are
then filtered by their latest published departure time to the requested future
window. Delays originating more than six hours earlier may be missed. The public
passenger board may omit cargo/private services and provides no aircraft-specific
RWY18 assignment or eligibility decision.

Pagination is bounded to 60 pages of up to 50 records, stopping after the requested
horizon, an empty page or a repeated-page guard. Its `hasnext` flag was observed
false while later pages contained records, so it is not used as an end condition.
The source metadata reports completeness, stop reason, excluded-record counts,
pages fetched and errors. The live board may change while pages are fetched.

`source.status` is `available`, `partial`, or `unavailable`. Partial results remain
visible with explicit coverage/error information. An unavailable source is not
reported as a genuine zero-flight day. `flight_count` counts primary upcoming
services in this snapshot, not the number assigned to RWY18.
