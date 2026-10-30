# Eastbound and westbound forecast

The [original challenge brief](challenge/README.md) defines one airport-wide operating direction for the three parallel runways. Landing direction is aircraft movement, not the side of the airport from which the aircraft approaches.

| Predicted OD | Landings | Centre-runway departures | Runway 18 departures |
| --- | --- | --- | --- |
| 07, eastbound | Towards the east, approaching from the west; ends 07L / 07R | Towards the east on 07C | Southbound on 18, subject to its separate weather limits |
| 25, westbound | Towards the west, approaching from the east; ends 25R / 25L | Towards the west on 25C | Southbound on 18, subject to its separate weather limits |
| Unknown | No east/west or landing-runway prediction | No Centre-runway prediction | Physical direction remains south; operational status is unknown |

These are the brief's runway roles and expected airport configuration, not assignments to individual flights. An arrival list and each aircraft's assigned landing runway are not supplied by this feature.

## Read and refresh

```bash
source .venv/bin/activate
python -m fra_forecast refresh --live-only --no-departures
python -m fra_forecast refresh-comparison
python -m fra_forecast serve
```

`GET /api/forecast` now includes `forecast[].direction_forecast` and top-level `operating_direction_outlook`. The direction block uses a compatible independently trained OD prediction when available; otherwise it explicitly uses the existing weather-rule prediction. Main forecast fields remain unchanged. The raw D2/EU baseline retains its 15-minute timeline where supplied and hourly fallback thereafter.

`GET /api/forecast-comparison` exposes the same blocks, using the validation-selected corrected weather when the independent OD model is unavailable. This is the **ML-corrected weather plus challenge rules** path, not a model trained on actual operating directions. The selected wind model and rule-derived direction are identified in the output. The UI can consume this endpoint for the selected-weather outlook and retain the main forecast as its baseline comparison.

The live run selector now checks the full 48-hour wind coverage within the trained
model-lead range. The implementation smoke check caught a metadata-selected 09:00
ICON-EU run that covered only 26 future targets; the eligible 06:00 run restored
all 48. It records `run_selection_reason: older_run_has_more_supported_hours`
and retains the older run's explicit estimated-availability status. If the older
run cannot be fetched, known hours from the newer run remain available and gaps
stay unknown. Missing gust alone does not discard known wind direction.

## Per-hour JSON

| Field | Meaning |
| --- | --- |
| `status`, `operating_direction`, `movement_direction` | Available/unavailable; 07/25/null; eastbound/westbound/null |
| `basis` | `independently_trained_od_model`, `challenge_rules_raw_weather`, or `challenge_rules_selected_weather` |
| `model_version`, `wind_model` | OD model identity when used and weather model/candidate identity |
| `p_od07`, `p_od25`, `certainty_score`, `certainty_basis`, `probability_status` | Learned probabilities only when valid; otherwise null with an explicit unavailable basis |
| `learned_model_status`, `learned_model_reason` | Why a learned prediction was used or unavailable; invalid probabilities fall back visibly |
| `runway_plan.landings` | Movement direction, true heading, approach side, and landing runway ends |
| `runway_plan.centre_departures` | Matching movement direction, heading, and Centre runway end |
| `runway_plan.runway18_departures` | Always southbound/180 degrees/18; separate weather suitability and unknown official status |
| `runway_plan.individual_flight_assignment` | Always null; no flight assignment data exists |

Comparison forecasts additionally include `weather_model_agreement`: raw ICON-EU and GFS source directions, number agreeing, and fraction supporting the selected direction. The fraction is populated only with both sources present. Boosting, Ridge, and the blend are excluded as extra votes because they share ICON-EU inputs. Agreement is **not** the probability of actual 07/25 operations and is not inserted into `certainty_score`.

`operating_direction_outlook` counts eastbound/westbound/unknown hourly targets, groups consecutive targets with the same direction and method, and supplies the next change. Group endpoints are `first_target` / `last_target`, not proof of uninterrupted operation between samples. Each period contains the runway layout; RWY18 weather is per-hour, not asserted for an entire period. Missing hours split groups. When model and weather fallbacks mix, change detection follows the displayed hourly sequence and is marked `mixed_learned_and_weather_hourly_sequence`. Source snapshot age/status still applies; fresh output formatting does not make stale input current.

The chatbot airport tool forwards the per-hour runway plan and describes east/west movement without inventing per-flight runway assignments. It retains existing source timestamps and freshness handling. No UI was implemented.

Replay CSV/JSON add `expected_operating_direction`, `expected_direction_basis`, `landing_movement_direction`, `landing_approach_from`, comma-separated `landing_runway_ends`, `centre_departure_direction`, `centre_departure_runway_end`, and `runway18_departure_direction`. Existing learned `operating_direction`, probabilities, and export completion criteria are unchanged: a weather-only export remains incomplete for the learned-OD requirement.

## Remaining model gap

The independent-label training, calibration, evaluation, and live model path already exist in `operations_ml.py`. There is still no accepted historical label file, so its actual-OD probabilities and accuracy remain unavailable. The latest [bounded source check](operations-label-research.md) retrieved real DFLD history and found explicit east/west indicators, but did not establish their exact timestamp/interval semantics. It does not justify filling the interval CSV with guessed transitions or training on wind-derived labels.

This increment makes the requested 07/25 **forecast and runway interpretation** usable. It does not establish that the actual-OD model beats the PDF baseline. The existing one-page model card's incomplete-OD status remains correct.
