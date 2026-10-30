# Frankfurt Airport operating direction forecast

Working interpretation of the supplied FraAlliance case brief, dated 30 October 2026. These are challenge requirements, not a claim that a working prediction model exists.

## Product outcome

For each hour through the next 48 hours, show:

- Runway 18 usability probability.
- Airport-wide operating direction: 07 (east, 070° true) or 25 (west, 250° true), with confidence.
- Next probable direction change time, allowing an unknown/no-change result.

Runway 18 only supports southbound departures (180° true), in either operating direction. The 07/25 runways switch direction together. Treat Runway 18 availability separately from operating direction.

## Baseline from the brief

- Use wind components relative to runway headings, not raw wind speed alone.
- Landing tailwind >= 10 kt forces an immediate direction change.
- Smaller tailwind can be accepted for up to 30 minutes; if it persists longer, switch to the headwind direction. This needs state and sub-hourly history.
- Runway 18 tailwind >= 15 kt prevents departures.
- Crosswind > 40 kt, including gusts, closes the affected runway.
- The provided 20 kt / 45° example concerns the 15 kt departure limit; landings have a stricter 10 kt limit.

These rules applied to weather forecasts form the baseline. The challenge requires a machine-learning forecast that improves on it. Agree on gust handling, missing data, historical direction state, and wind units/reference before implementing the baseline.

## Data work (Antonio)

Find and cite public weather observations (for example EDDF METAR), weather forecasts, and historical operating direction / Runway 18 outcomes. Actual availability labels may be harder to obtain than observed runway use: no departure on a runway does not prove that runway was unusable.

Retain UTC observation time, valid time, publication/issue time and source URL. Historical evaluation needs the forecast that was available at the time; later observations or revised weather products would leak future information.

Keep large raw downloads in ignored `data/raw/`, private material in ignored `data/private/`, and credentials in ignored environment files. Add small shareable examples only after checking their license and contents.

## Design work (Philipp)

Start with forecast issue time, airport operating direction, Runway 18 probability, a 48-hour timeline, and the next likely change. Make confidence, missing data, stale forecasts and baseline/model status visible. Keep observed conditions distinct from forecasts.

Philipp's first design draft establishes a full-screen satellite map with OpenStreetMap runway overlays and two glass panels. He confirmed that the upper panel follows the selected runway and shows status, confidence and next change; the lower panel charts tailwind in knots with 12/24/48-hour horizons. Crosswind including gusts is shown separately. The local app implements this design with empty forecast states and an optional, clearly labeled illustrative chart. It does not yet compute wind components or consume live forecasts.

The chart uses the brief's 15 kt departure and 10 kt landing tailwind limits as references, according to the runway's main role. Selected-runway highlighting is geographic selection, not availability. Paired 07/25 runway wind components must ultimately follow the forecast operating direction at each hour. Agree the meaning of selected-runway confidence and next status change with Antonio before connecting the backend.

## Proposed integration boundary

Agree on the payload together before wiring the app to Antonio's output:

- Forecast-level fields: issue time in UTC, model version, data mode (sample/live), source citations.
- 48 hourly records: valid time in UTC, Runway 18 usable probability (0–1), direction (`07` / `25`), probability of the selected direction (0–1).
- Optional next-change time in UTC and confidence; define how this is derived from the forecast.
- Missing results should be explicit `null`, never replaced by fabricated predictions.

No API or model has been implemented yet.

## Evaluation and submission

Use a held-out chronological period, with only information available at each forecast issue time. Compare the model and the rule baseline on identical cases at 1 h, 6 h and 24 h lead times. Agree on probability and classification metrics, report sample sizes and missing-label coverage. Do not invent quality scores.

The brief asks for the repository, a one-page model card (sources, evaluation, forecast drivers), and forecasts for jury test days.
