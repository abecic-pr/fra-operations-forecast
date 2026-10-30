# Runway 18 live wind UI

The current local UI uses Antonio's live schema 1.0/1.1 API (raw baseline fields). The synthetic provider remains available for development but is not an automatic fallback.

## Local development

Use Python 3.11+ and Node.js 22.12+ or 20.19+.

```sh
python3 -m fra_forecast refresh --live-only --history-days 1 --archive-days 0
python3 -m fra_forecast serve
```

In another terminal:

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173/#map. Vite proxies `/api` to the loopback Python server with the original Host header. The UI reads saved data every 30 seconds and refreshes external sources every 10 minutes while visible. Refresh weather triggers a manual update. It retains last received data with a connection-lost label if a later request fails; it does not silently invent demo data.

## Chart and time

The narrower right inspector has a compact Runway 18 summary and a tailwind chart. Eyebrow labels have been removed. A six-hour history window precedes the 12/24/48-hour forecast. Axis timestamps and the live clock marker are UTC. The real clock remains independent of forecast playback. Latest reading shows the observation timestamp, not a claim that the measurement was taken this second.

- Blue: issued forecast tailwind, in knots, for Runway 18 heading 180 degrees true.
- Green: actual DWD station 01420 tailwind calculated from mean measured speed and direction. Points must pass source URL, response hash, station, timestamp, finite value and QN 2/3 checks. Recent values remain explicitly provisional, not final quality-controlled ground truth.
- The green line never extends into the future or bridges large missing-data gaps. Measurements are not fabricated from forecasts.
- Measured wind is separate from official runway operational status. The latest general airport observation can be EDDF METAR, while the green comparison series uses the DWD station matching the model location.

[DWD's measurement and quality documentation](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/DESCRIPTION_obsgermany_climate_10min_wind_en.pdf) describes QN 2 as individually controlled and QN 3 as automatic control/correction; recent and now datasets are not final QC. The user approved checked provisional observations for this line.

## Honest forecast comparison

`GET /api/verification` is an additive endpoint; `/api/forecast` schemas 1.0 and 1.1 retain the raw baseline fields. It returns screened observations and past forecast points from `data/issued-forecasts.jsonl`. The server archives only future predictions when generating or first serving a snapshot, with actual archive time as `issued_at`. It does not backdate forecasts and does not rewrite an existing issued snapshot.

Only exact valid-time matches are scored, using a forecast issued before the measurement time. The UI uses the latest eligible issue per valid time and reports MAE in knots with the number of matched times. A 9 kt forecast and 7 kt observation has a 2 kt absolute error. Before matched history exists, the status says Awaiting forecast matches. Live observations alone do not establish model accuracy.

The source ZIP's mean-wind quality code is read directly; the merged observation CSV's code can refer to the separate gust product, so it is not used as mean-wind verification. Actual retrieval time records when data was available to this UI; the backend's historical publication-delay estimates are not treated as measured receipt times.

## Data boundary and limits

`src/data/wind.ts` normalizes backend vectors, observations and archived forecasts. Map, chart and summary do not fetch their own weather. Spatial mode is uniform airport wind: no real gridded field has been supplied. Switching to a real grid later requires changing the sampler, not the renderer. Model probabilities remain null for the deterministic baseline.

Tests:

```sh
npm run check:wind
python3 -m unittest discover -s tests -v
npm run build
```

Checks cover direction conversion, case thresholds, missing values, source/time/quality gates, immutable issues, no future observations or hindsight forecasts, and the 9-versus-7 kt comparison. Wind ML training and evaluation are implemented on main; held-out operating-direction evaluation still needs independent labels. The UI displays raw baseline fields, not additive ML probabilities.

## Motion and runway colors

All buttons share subtle press feedback. Segmented controls slide their selection, map-layer switches animate their thumb, the layer panel eases open and closed, chart horizon changes fade, playback icons settle, and refresh shows a rotating indicator. Motion respects the system's reduced-motion preference, including map recentering. The wind layer remains independently controllable.

Runway 18's geometry, status dot and summary border share a presentation color for the selected time. Green means the available weather state is usable, yellow means a measured/forecast component is at least 80% of a wind limit (tailwind ≥12 kt or mean/gust crosswind ≥32 kt), and red means wind limits are exceeded (tailwind ≥15 kt or mean/gust crosswind >40 kt), or the backend reports not usable. Yellow is a visual proximity warning, not a trained closure probability. Missing data stays gray unless a known component warrants yellow/red; a disconnected provider is gray. Text labels accompany color. This is weather suitability, not an official airport closure feed. The backend rules and persistence logic are unchanged.

## Dashboard departures and case directions

The dashboard hero follows Philipp's Weather Operations reference with centered Dashboard / Map view navigation. Next flights defaults to the real FRA board via `/api/runway18/departures`. The merged backend retains Antonio's departure collector, ML and comparison features. The wind adapter accepts schema 1.1 while continuing to display baseline fields; ML outputs remain available through the API. A three-hour live snapshot was collected locally. The board is polled every minute for updated saved data; external refresh remains the collector's responsibility. Refresh the saved list with `python3 -c 'from fra_forecast.departures import refresh_departures; refresh_departures(hours=3)'`.

Real flights appear under Unassigned because the source supplies neither assigned runways nor wheels-off times. Their estimated/scheduled departure times use Europe/Berlin, while the wind chart stays UTC. Source failures preserve the last received list with a connection label. Design preview is a separate explicitly synthetic two-lane example for Runway 18 and Centre 07C/25C; it never assigns a real flight by weather inference. Selecting a card shows its flight details.

Challenge PDF, page 1 sections 2 and 3: 07/25 can operate both ways, but the airport switches those runways together; mixed operating directions are not allowed. 25 is westbound (250°T), 07 eastbound (070°T). Runway 18 allows departures southbound only (180°T) in either OD. Tailwind ≥10 kt on landing runways forces an OD switch; smaller positive tailwind can persist up to 30 minutes, then the OD switches to the headwind direction. RWY18 tailwind ≥15 kt prevents takeoff, and crosswind >40 kt including gusts closes a runway. With RWY18 wind-limited, the case directs departures to Centre 07C/25C. These case rules are not individual aircraft clearances or confirmed flight assignments. R-54W in the sketch is replaced with the case's Centre runway designation.

## Primary dashboard wind KPIs

Current wind, Max wind (48h) and Average wind (48h) are the main dashboard cards, following Philipp's reference. These show **total wind speed**, not Runway 18 tailwind. Current wind uses only the latest observation in live mode, independent of map playback. Maximum and average use valid scalar wind speeds in the saved forecast's next 48 hours; the average is the arithmetic mean of available hourly speeds. Opposing wind vectors are not averaged together. Missing samples are excluded with an explicit available-hours count; no live observation or no forecast gives an unavailable value, not zero. The peak's valid time, observation time and forecast issue time remain visible. All three gauges share a labeled scale; there is no false 15 kt total-wind closure marker. Runway suitability and tailwind remain in a compact separate status strip.

The installed design reference is [Emil Kowalski's Apple Design skill](https://github.com/emilkowalski/skills/tree/main/skills/apple-design), an independent web-design skill, not an official Apple release. It is installed in the local Codex skills directory and available automatically from the next turn. Application code has no added animation or UI dependencies. Cards use system typography, restrained depth, a consistent grid, and reduced-motion/contrast support.

## Operational dashboard and distinct takeoff/landing limits

The main row now prioritizes Runway 18 observed tailwind, gust crosswind and the next forecast limit exceedance. The previous current/max/average total-wind cards remain under Wind speed overview. A satellite map preview with real Runway 18 geometry, uniform airport-point wind animation, pause/zoom and Open map is paired with selected-time wind components and peak tailwind in the next six hours. Current top-row observations do not change during forecast playback; the map and selected-time panel do. Freshness is calculated against the current clock.

The case PDF page 1 sections 2 and 3 distinguishes **departure tailwind <15 kt** from **landing tailwind <10 kt**. The landing threshold drives airport-wide 07/25 direction changes, including the Centre runway; this does not create a landing mode on departure-only southbound Runway 18. Crosswind **>40 kt**, including gusts, exceeds the shared limit. Exactly 40 kt is not above it. A positive landing tailwind below 10 kt may still trigger an OD change after more than 30 minutes. The backend already implements these rules; no limits or persistence logic were changed.

The normalized adapter now retains reported operating direction, its source/report/since times, forecast hourly directions, the baseline next OD change, raw METAR and source-error count. The landing chart projects each forecast vector onto that point's backend forecast direction (070/250 degrees true); missing direction produces a gap. It never applies the 10 kt landing line to RWY18.

Three synchronized charts show departure tailwind (15 kt line, checked provisional history and actual clock), gust crosswind (40 kt line), and landing tailwind (10 kt line). The 6/12/24/48-hour display window is measured from forecast issue time, which remains visible. The selected time updates map/details; current observations remain pinned. Peak-six-hour tailwind and the next flagged hour are evaluated from the current clock, excluding past predictions. A flagged forecast hour is not an exact closure minute; no-flag text applies only through the available forecast, and incomplete gust/component coverage remains Unknown.

Data-source details expose the raw report and explicit missing-data/model/official-status boundaries. No calibrated confidence or new operational labels are invented. OpenAI remains disconnected. Tests cover 10 versus 15 kt component projections, the exact 40 kt boundary, missing gusts, and future-only exceedance searches. Browser checks cover map preview, shared horizon and timeline changes, independent observed KPIs and source details.

## Airport movement directions and Antonio integration

The design branch now merges Antonio’s main through `1aaf46e` (forecast comparison and east/west outlook), preserving the backend comparison, independent-OD training, coordinator and flight-chat features. Both schema 1.0 and 1.1 are accepted. Hourly `direction_forecast.operating_direction` and its method take precedence over the legacy weather-rule direction; an explicitly unavailable new prediction does not fall back to a guessed direction. At Now, the airport model and map use `observed_operations`; at selected forecast times they use the backend prediction. Missing/disconnected directions suppress the parallel-runway arrows. Intervals spanning differing hourly directions remain unknown. Weather-rule outputs carry no invented certainty score.

The dashboard has a small north-up model drawn from the same OSM runway geometry as the real map. Cyan arrows identify landings on Northwest/South; navy (white on satellite) identifies Centre departures. All three use 070°T for OD07 or 250°T for OD25. RWY18 always points south and retains its separate weather-suitability color. These depict the brief’s runway configuration, never individual flight assignments or official closure status. The map fits the full airport; its location control restores that view. Wind particles still show air travel, independent of the aircraft arrows.

Both takeoff and landing prefer headwind; limited tailwind is allowed under the brief’s distinct thresholds. The backend’s existing persistence logic remains authoritative. Current reported direction and selected forecast can differ, and are labeled separately.

To preserve both collaborators’ chatbot contracts without changing Antonio’s `/api/chat`, the dashboard’s visual assistant now uses `/api/weather-bot` with `/status` and `/preview`. Its Python module/tests are `weather_bot.py` / `test_weather_bot.py`. The original backend chat remains at `/api/chat` with its own bounded tools and validation. Neither sends OpenAI requests without local backend credentials. Measurement verification and issued-forecast archiving are retained.
