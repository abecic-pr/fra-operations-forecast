# Application and model data

Recommended data contract, 30 October 2026. Scope: Frankfurt/EDDF, operating direction 07/25, meteorological usability of RWY18 and an hourly forecast up to 48 h. Sources and verified links are in `data-sources.md`.

The requirements are extracted from the user's PDF `AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf`, page 1, sections 1–4. The additional fields below are implementation recommendations, not additional requirements from the organisers.

## Data the person monitoring the application must be able to obtain

| Data | Recommended field | Content / unit | Priority |
|---|---|---|---|
| Airport and time zone | `airport_icao`, `display_timezone` | EDDF, Europe/Berlin | P0 |
| Current observed operating direction | `observed_operating_direction` | `07`, `25` or `unknown`; never a weather forecast presented as an observation | P0 |
| Since when the current direction applies | `operating_direction_since` | Timestamp, or null if not known | P0 |
| Source and check time of the direction | `operating_direction_source`, `operating_direction_observed_at` | DFS/UNH, Fraport or derived from flights, with a confidence label | P0 |
| Mean wind speed | `wind_speed_kt` | Knots; with the averaging period | P0 |
| Direction the wind blows from | `wind_from_deg_true` | 0–360° relative to true north; null for unknown/variable direction | P0 |
| Direction variability | `wind_variable`, `wind_sector_from_deg`, `wind_sector_to_deg` | Keep VRB and the range from the raw METAR | P0 |
| Wind gusts | `wind_gust_kt`, `gust_from_deg_true` | Maximum and its direction when known; null is not 0 | P0 |
| Headwind/tailwind component for 07, 25 and 18 | `runway_wind[].headwind_kt`, `tailwind_kt` | Calculated from direction, speed and runway orientation | P0 |
| Crosswind component and gust component | `runway_wind[].crosswind_kt`, `gust_crosswind_kt` | Separately for each direction, flagged as an approximation if the gust direction is not known | P0 |
| Margin to thresholds | `tailwind_margin_kt`, `crosswind_margin_kt` | A positive value means remaining margin; boundary conditions according to the rules below | P0 |
| Estimate of current meteorological usability of 18 | `rwy18_weather_state` | `usable`, `not_usable`, `uncertain`, `unknown` | P0 |
| Confirmed operational status of 18 | `rwy18_operational_status` | `open`, `closed`, `restricted`, `unknown`; only with an appropriate source | P0 |
| Forecast direction for each future hour | `forecast[].operating_direction` | `07`, `25` or `unknown` | P0 |
| Direction probabilities | `forecast[].p_od07`, `p_od25` | Number 0–1; sum to 1 when the classification is available | P0 |
| Probability of usability of 18 | `forecast[].p_rwy18_weather_usable` | Number 0–1; clearly refers to weather conditions | P0 |
| Hourly wind and gust forecast | `forecast[].wind_speed_kt`, `wind_from_deg_true`, `wind_gust_kt` | Same units and definitions as the observations | P0 |
| Next expected direction change | `next_od_change` | From/to which direction, time or time window, probability and status | P0 |
| Next expected change in usability of 18 | `next_rwy18_change` | Deterioration/improvement, time window and probability | P0 |
| Reason for the estimate or warning | `reason_codes`, `reason_text` | E.g. tailwind, crosswind gusts, duration of unfavourable wind, model disagreement | P0 |
| Data age and quality | `data_age_seconds`, `quality_status` | Fresh, stale, incomplete, no data; per source | P0 |
| Issue time and horizon | `forecast_issued_at`, `valid_time`, `lead_time_hours` | Do not mix up the generation time and the time the forecast applies to | P0 |
| Additional meteorological context | `visibility_m`, `ceiling_ft_agl`, `weather_codes`, `temperature_c`, `dew_point_c`, `qnh_hpa` | Visibility, base of the lowest BKN/OVC layer or vertical visibility, phenomena, temperature, dew point, pressure | P1 |
| Warnings and non-weather reasons | `weather_alerts`, `operational_restrictions` | SIGMET/CAP/NOTAM with area and validity interval | P1 |
| Model quality on the test | `model_metrics_by_horizon` | Results for 1, 6, 24 h, test period and number of samples/events | P0 for evaluation |

P0 = first version; P1 = useful addition after the basic flow. A field can be mandatory in the contract and still be `null`/`unknown` when the source is not available. That is more accurate than inventing values.

`next_*_change` should have the status `change_expected`, `no_change_within_horizon` or `unknown`. A null time without a status is not sufficient. An hourly forecast does not justify apparent minute-level precision for a change; an interval is more appropriate. The probability of an event within an interval is not the same as the probability of one class in one hour.

## Input data to store for the model

| Dataset | Minimum fields | Why |
|---|---|---|
| Wind observations | Time, speed, direction, gust, gust direction, measurement interval, quality flags | Main predictors and component calculation |
| Recent history | Last 10/30/60/180 min, u/v components, variability, maxima, change in direction/speed | Distinguishes a passing gust from a persistent change |
| Current operations | Observed OD, time of last change, status of 18 if known, data age | Persistence and the model's initial state |
| Forecast runs | Model, run, availability time, valid time, horizon, wind/gusts | Future conditions without using information that did not yet exist |
| Additional meteorology | Temperature, dew point, pressure and its change, visibility, clouds, precipitation | Test whether it improves prediction |
| Spatial/vertical context | Nearby stations, forecast grid-cell coordinate, wind above ground | Possible arrival of a change from the direction of the Taunus |
| Outcomes for learning | Actual OD over time, OD changes, actual runway of a flight, status of 18 and reason, label source | For training and independent evaluation |
| Provenance of each record | URL/product, station identifier, download time, raw record, parser version | Reproducibility and distinguishing sources |

Proposed initial feature set: `u10`, `v10`, gust, tailwind and crosswind component for 07/25/18, current OD, duration of the current OD, tailwind duration, wind trend over 30/60 min, and forecast u/v and gusts for the target hour. Add temperature/pressure/upper-level wind only after comparing results. Seasonal and hour-of-day indicators can be useful, but do not on their own replace meteorological inputs.

Wind from DWD, Bright Sky and Meteostat can come from the same station. Do not count such copies as three independent measurements.

## Challenge rules and derived data

For the baseline, use the orientations from the PDF: 07 = 70°T, 25 = 250°T, 18 = 180°T. For the actual geometry, store verified orientations from the AIP or metadata separately; do not mix magnetic runway designators with true north.

For speed `V`, the direction the wind blows from `theta` and runway orientation `psi`:

```text
delta = theta - psi                    # trigonometry uses radians
headwind = V * cos(delta)              # positive: headwind
tailwind = max(0, -headwind)
crosswind = abs(V * sin(delta))
```

If the gust direction is known, calculate the gust components from it. If not, using the mean direction with the gust speed is an approximation and must be flagged. Do not combine mismatched maxima and directions from different intervals as if they were the same event. For VRB or a wide direction range, a range of components can be shown instead of a single falsely precise value.

| Rule from the PDF | Data that must exist |
|---|---|
| Tailwind for landing must be < 10 kt; at ≥ 10 kt an OD change follows | Tailwind component on the currently active direction |
| Tailwind for take-off must be < 15 kt | Component for the selected departure runway |
| On RWY18, a tailwind component ≥ 15 kt prevents take-off | `tailwind_18_kt`, deviation from 15 kt |
| Crosswind > 40 kt, including gusts, closes the runway | Mean crosswind component and gust crosswind component |
| A weaker tailwind can last up to 30 min before a change | Time series and duration of the uninterrupted interval, not just a single hourly average |

Examples from the challenge: 090°/20 kt gives approximately 18.8 kt tailwind component on direction 25; 330°/20 kt gives approximately 17.3 kt tailwind on RWY18.

Interpret the margin `limit - component` together with the operator: for tailwind, a margin of 0 means the prohibited threshold has been reached, while the crosswind threshold in the PDF is strictly `>40`. Store `ruleset_version` for such boundary conditions.

If both parallel directions are unfavourable because of crosswind, this should be a separate restriction status. A forced choice of 07/25 does not mean that operations are possible. Operating direction and runway availability are not the same target variable.

Fraport publicly describes a change at approximately 5 kt tailwind component, which differs from the 10 kt in the challenge. For comparison with the hackathon baseline, keep the PDF rules, and learn actual outcomes from independent observations. [Source for the actual operational context](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/laerm-und-luft/flugbetrieb/betriebsrichtung.html).

## Time, units and missing data

- Store all times as UTC with an explicit `Z`/offset. Use Europe/Berlin for display. During the change between summer and winter time, local time is not a unique key.
- Distinguish `observed_at`, `interval_start/end`, `issued_at`, `model_run_at`, `available_at`, `fetched_at`, `valid_time`. Model initialisation precedes publication; in testing, a run must not be available before its actual publication time. [Open-Meteo explanation of runs](https://open-meteo.com/en/docs/single-runs-api).
- `generationtime_ms` in the Open-Meteo response is the API request processing time, not the issue time of the weather forecast.
- Use knots for operational thresholds: m/s × 1.943844; km/h ÷ 1.852. Keep the original units as well. Bright Sky uses km/h for speed, and the verified Open-Meteo query explicitly requests `kn`.
- Average wind direction circularly or via u/v components; the average of 350° and 10° is not 180°. For the meteorological direction the wind blows from: `u=-V*sin(theta)`, `v=-V*cos(theta)`.
- Calm, variable direction and missing direction are three different states. `VRB` is not zero degrees. The absence of a reported gust in a METAR is not evidence that the gust is 0 kt.
- METAR visibility and clouds have their own units and codes. In the tested AWC JSON, `visib="6+"` is not six metres; raw `9999` means at least 10 km. Parse `CAVOK`, `NSC`, `BKN` and `OVC` correctly, without inventing an exact visibility/base.
- Filling a missing gust field must not silently turn an unknown gust component into "safe". Lower the estimate's quality or return `unknown` for the affected check.
- Check the last **valid record**, not just HTTP 200. Proposed staleness thresholds should be configurable per source and tied to the measured cadence.
- Keep the original METAR/TAF and the incoming forecast response: the parser can miss direction variability, special groups or later amendments.

## Actual outcomes, probabilities and testing

Do not merge four different kinds of data into one field: **weather measurement**, **numerical weather forecast**, **official/observed operations status** and **our model's prediction**.

For RWY18, separate:

- `rwy18_weather_usable`: estimate based on wind and the given rules.
- `rwy18_used`: whether a take-off was observed in a defined interval.
- `rwy18_operational_status`: confirmed open/closed/restricted.

The first can be calculated without flights. The second requires traffic data. The third requires a reliable operational source. Zero take-offs is not a negative label for the first or the third. If there are no actual labels, clearly report that the model has not yet been validated against actual operations; training on labels produced by the same rules does not prove improvement over the baseline.

Do not invent probabilities from the distance to a threshold. Obtain them from a model or ensemble members, then check calibration on separate dates. The share of ensemble members meeting a criterion is an initial estimate, not automatically a calibrated probability. "80%" must have a verifiable statistical meaning.

Test chronologically, with separate training, calibration and test sets, and prevent future target intervals from overlapping across the boundaries. For each moment t, use only inputs whose `available_at <= t`. A later TAF AMD/COR, reanalysis or subsequently corrected records must not slip in unnoticed as data known at the time.

| Result for the report | Why it is needed |
|---|---|
| Accuracy and balanced accuracy / F1 per direction | A dominant direction can hide weak detection of the rarer class |
| Brier score or log loss and a calibration check | Quality of the probabilities, not just the categories |
| Precision/recall of changes and change-time error | Changes are often the most important events for the operator |
| RWY18 recall of unusability and number of false alerts | Separate missed unfavourable conditions from overly frequent alerts |
| Number of cases, number of changes and coverage share | Shows how representative the evaluation is |
| The same metrics for 1, 6 and 24 h | Explicit requirement of the PDF |
| Comparison with the physical rules and with persistence of the current state | Needed to show the model's contribution |

The exact output for the jury (column names, test days, how the hour is labelled and the meaning of the RWY18 target) is not specified on the attached page. When joining with their dataset, this must be aligned; do not assume that one hour contains only one direction if a change occurred during it.

## Out of scope for the first version

UV index, apparent temperature, air quality, soil moisture, solar radiation, multi-month climate averages, and data on passengers, gates, baggage and finances are not a priority for this task. Radar, satellite images, details of all flights and several parallel commercial weather APIs add work before the key problem of actual labels is solved.

If time is limited: **DWD wind + gusts, METAR, archived ICON runs, observed OD and status/use of 18, derived components, 48 hourly predictions, change time and data quality** make up a minimal meaningful set.
