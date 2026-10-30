# Shared project knowledge snapshot

Snapshot read 30 October 2026. Source: https://chatgpt.com/space/page_fe8b5e3a0f788191867be7f4e42de933

Team hub for the FraAlliance challenge at AI Week Frankfurt, 30 October 2026. Build a 48-hour outlook for Frankfurt Airport operating direction 07/25 and Runway 18 weather suitability within a six-hour hackathon budget.

# Collaboration rule

# Current priority

Review the compact Runway 18 map with live weather and provisional checked measurements. Preserve Antonio's schema 1.0. Archive issued forecasts and compare them with later measurements before training or claiming accuracy.

# Project links

[GitHub repository](https://github.com/abecic-pr/fra-operations-forecast) · [README and setup](https://github.com/abecic-pr/fra-operations-forecast#readme) · [Issues](https://github.com/abecic-pr/fra-operations-forecast/issues) · [Pull requests](https://github.com/abecic-pr/fra-operations-forecast/pulls)

# Work split

| Area | Responsibility |
| --- | --- |
| Data and backend | Source integration, dataset exports, runway components, baseline, evaluation and JSON contract |
| UI | Philipp’s dashboard, 48-hour outlook, quality states and API integration |
| Together | Resolve operational labels, agree the handoff, integrate and rehearse the demo |

# Current status

Antonio's latest main commit a3a3f59 adds a wind ML pipeline and RWY18 departure-weather assessments. The local design branch copied his departure collector, contract and tests unchanged, added its GET route, and collected 102 upcoming services in a three-hour snapshot. The broader ML/schema 1.1 changes have not been merged or enabled in this UI; wind remains on its existing schema 1.0 adapter. The published design branch remains at a453696; subsequent live weather, micro animations and dashboard work remain local and unpushed. Operational training/evaluation still needs independent labels. Status: 30 October 2026.

# Design handoff

**Design chat snapshot: 30 October 2026.** Philipp owns design; Antonio gathers data and develops the backend. Runway 18 remains the only runway in scope. The right inspector is narrower, the summary is much smaller, and eyebrow labels are removed. Both panels fit the desktop viewport. Dashboard, map and timeline now share the live provider. Buttons now share soft press feedback, selections slide, switches animate, the layer panel eases open/closed, and chart/playback/refresh controls have subtle transitions. System reduced-motion settings suppress decorative motion. The production build and wind/color-boundary checks passed; browser checks covered layer switches, horizons, keyboard timeline selection and green/unknown states, with no console warnings or errors. Changes remain local and unpushed.

## Repository alignment

The tested UI is pushed to [codex/design](https://github.com/abecic-pr/fra-operations-forecast/tree/codex/design), latest commit [a453696](https://github.com/abecic-pr/fra-operations-forecast/commit/a4536963ea58145ce420ba3c2aacbf5600ffe633). The branch includes Antonio's existing main history; no merge into main has been performed.

GitHub confirmed during push that aiw26 was renamed to fra-operations-forecast. The old URL redirects to the same repository. The local remote and README now use the confirmed name; there is no separate-repository mismatch.

## App and design decisions

- **Dashboard:** Philipp's Weather Operations hero and centered Dashboard / Map view navigation are implemented. Runway 18 weather cards remain live. Next flights defaults to real upcoming FRA published departures, displayed as Unassigned because no runway assignment or wheels-off time is supplied. A separately labeled Design preview shows illustrative pill queues for Runway 18 and Centre 07C/25C, with no real assignment inference. Times use Europe/Berlin. Cards open flight details; controls retain micro animations.

- **Map view:** full-screen satellite imagery with OpenStreetMap Runway 18 geometry and a street-map fallback. Other runway overlays, labels and selectors are hidden. Wind particles follow geographically sampled vectors; color shows total wind speed in knots. The legend distinguishes wind-from direction from the direction particles travel.

- **Airport layers and runway colors:** controls for wind speed/flow, animation, Runway 18 and the airport boundary. The runway geometry, summary dot and border share the selected time's wind-suitability color: green within limits; yellow at ≥12 kt tailwind or ≥32 kt mean/gust crosswind (80% of the limits); red at ≥15 kt tailwind or >40 kt mean/gust crosswind, or backend not_usable. Yellow is a visual proximity warning, not a predicted closure probability. Missing data stays gray unless known wind warrants yellow/red; connection loss stays gray. These are wind conditions, not an official operational closure feed. Existing backend limits and persistence rules remain unchanged. Reduced-motion preferences default to a still wind field.

- **Forecast presentation:** 12/24/48-hour horizons and playback remain synchronized. A real current-time marker is independent of the selected forecast time. Blue shows issued forecasts; green shows actual measured tailwind, labeled provisional, and never extends into the future. A 9 kt prediction versus 7 kt measured plots green at 7 kt. MAE and match count appear only when actual timestamp-matched, previously issued forecasts exist. There were no eligible matches at initial connection; no accuracy is invented. The 15 kt departure and 40 kt crosswind rules remain unchanged.

The airport overlay contains real [OpenStreetMap airport geometry](https://www.openstreetmap.org/relation/5813621), bundled locally as GeoJSON with source links and ODbL attribution. The satellite background is [Esri World Imagery](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer), separate from the OSM overlays. Source credits remain visible. Base-map tiles need an internet connection.

## Local testing

The app uses React, TypeScript, Vite and Leaflet. On a computer with the app files, run:

```sh
npm ci
python3 -m fra_forecast refresh --live-only --history-days 1 --archive-days 0
python3 -m fra_forecast serve --port 8000
# In a second terminal:
npm run dev
```

Open http://127.0.0.1:5173/ for the dashboard or http://127.0.0.1:5173/#map for the map. These addresses refer to the viewer's own computer; they are not shared hosted links.

The previously published demo passed wind checks, the production build and 15 backend tests. The current local live-data iteration passes wind/comparison checks and all 19 backend tests, including source/time/quality screening, immutable forecast issues and exclusion of future observations. Browser review confirmed the compact panels, real clock and green measured series. The final production build also passed. Browser console checks reported no warnings or errors. The local changes remain uncommitted and have not been pushed.

## Backend data handoff

The local UI uses the previously integrated weather schema 1.0, plus /api/verification. Antonio's latest [main contract](https://github.com/abecic-pr/fra-operations-forecast/blob/main/docs/backend-data.md) describes schema 1.1 and ML additions pending broader integration here. His [departure contract](https://github.com/abecic-pr/fra-operations-forecast/blob/main/docs/runway18-departures.md) is integrated locally at GET /api/runway18/departures. The UI polls the saved board every minute; collecting fresh external flight data remains a backend refresh action. Actual flight runways and takeoff times remain null. Local docs/frontend-wind.md records the integration boundary.

- The backend supplies schema_version, generated_at, ruleset, provenance and data-quality fields. Wind directions are from true north; speeds are knots; timestamps are UTC.

- forecast contains 48 whole-hour future records. The frontend adapter reads wind_speed_kt, wind_from_deg_true, wind_gust_kt, runway_wind['18'], rwy18_weather_state and p_rwy18_weather_usable.

- next_rwy18_weather_change is a rule-based change window. It is distinct from next_operating_direction_change; both probabilities remain null for the deterministic baseline.

- Missing predictions as `null`; do not replace them with invented values.

**Spatial data boundary:** the backend supplies airport-point wind, so the live map uses a uniform airport wind field. No geographic grid is fabricated. Missing values remain null. The UI polls saved data every 30 seconds and refreshes sources every 10 minutes while visible, with manual refresh available. Connection failures retain the last data with a connection-lost label.

Antonio's collection needs weather observations, archived weather forecasts with their issue times, and timestamped operating outcomes. No recorded departure on Runway 18 does not by itself prove that the runway was unusable. Evaluate on held-out dates using only information available at forecast time, comparing against the wind-rule baseline at 1, 6 and 24 hours.

## Case operating direction rules

The challenge PDF, page 1 sections 2 and 3, permits both directions on the 07/25 system, with a single airport-wide switch: 25 westbound (250°T), 07 eastbound (070°T). Mixed 07/25 directions are not allowed. Runway 18 is departure-only, southbound (180°T), and can be used in either OD; there is no northbound takeoff mode for it.

Landing tailwind ≥10 kt forces an OD change. Smaller positive tailwind is tolerated up to 30 minutes; longer persistence switches to the headwind direction. RWY18 tailwind ≥15 kt prevents takeoff; crosswind >40 kt including gusts closes a runway. When 18 is wind-limited, the case routes departures via Centre 07C/25C. These describe case rules, not individual aircraft clearance or confirmed flight assignments.

- [ ] Antonio: find a source with actual runway assignments and takeoff times if available; preserve the distinction from published gate/departure-board times. Until then, real flights remain Unassigned in the dashboard.

Dashboard validation: production build, wind/color/departure adapter checks and all 30 backend tests passed. Browser checks verified real flights, flight details, demo switching and the hero/queue layout; no console warnings or errors were reported. Changes remain local.

## Next steps together

- [x] Confirm the repository rename and push codex/design with backend history preserved.

- [x] Confirm the adapter against a real live snapshot and enable local integration at Philipp's request.

- [x] Connect Dashboard, Map and timeline to a shared demo provider.

- [x] Add a 48-hour timeline and forecast playback; calibrated model confidence remains pending.

- [x] Test and publish the earlier combined demo branch. The newer live integration remains local.

- [ ] Complete held-out evaluation, the one-page model card and jury-day forecasts.

## Antonio forecast comparison and training todo

- [ ] Antonio: compare each archived prediction with real measured wind at the same valid time and averaging interval. Preserve issued_at, valid_time, model version, station, units and provenance; never reconstruct old predictions from newer forecasts.

- [ ] Use official DWD station 01420 measurements only after source, response hash, station, timestamp and mean-wind quality checks. Philipp approved QN 2/3 readings labeled provisional; finalized quality control may arrive later. The checks read the original mean-wind ZIP, not the quality field merged with gust observations.

- [ ] Report tailwind error and MAE/RMSE by forecast lead time, including 1, 6 and 24 hours. The UI already records future issued forecasts without backdating and displays only eligible matches.

- [ ] Train and improve models using historical prediction/measurement pairs with chronological training, validation and held-out test periods. Enforce actual data availability to avoid future leakage. Model training is still pending; measured wind alone does not establish official runway availability.

Quality reference: [DWD mean-wind measurement and quality documentation](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/DESCRIPTION_obsgermany_climate_10min_wind_en.pdf).

# Project pages

Use the linked pages below for the active plan and detailed references.
