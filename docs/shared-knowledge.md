# Shared knowledge snapshot

Read-only repository copy of the shared FRA Operations Forecast Page, captured 30 October 2026 before the combined direction UI push. The live Page remains authoritative for collaboration updates: https://chatgpt.com/space/page_fe8b5e3a0f788191867be7f4e42de933

ML/history update: recovered 182 days of DFLD 07/25 displays and trained `operations-v3` from 4,259 conservative stable-state point proxies. Recent DWD wind plus forecast-history features improve probability scores at 1/6/24 hours. Direction accuracy wins at 1 hour, ties at 24 hours, and trails the rules by one case at 6 hours; overall accuracy is 77.60% versus 74.72% for rules. These are exploratory results on a previously inspected period; exact switch labels and RWY18 rare-event skill remain unresolved. See [measured results and reproduction](ml-improvement.md). The model's first eligible hourly reference is 14:00 UTC / 15:00 Berlin, after its actual evidence cutoff. Source history is local; redistribution rights are unverified.

Team hub for the FraAlliance challenge at AI Week Frankfurt, 30 October 2026. Build a 48-hour outlook for Frankfurt Airport operating direction 07/25 and Runway 18 weather suitability within a six-hour hackathon budget.

# Collaboration rule

# Current priority

Antonio: connect the OpenAI bot from codex/design when ready, then verify a real tool-backed answer, chart, map and follow-up. Keep OpenAI disconnected until configured. Preserve missing data and the distinction between wind suitability and official status. Reconcile main schema 1.1/ML changes before enabling them in this UI.

# Project links

[GitHub repository](https://github.com/abecic-pr/fra-operations-forecast) · [README and setup](https://github.com/abecic-pr/fra-operations-forecast#readme) · [Issues](https://github.com/abecic-pr/fra-operations-forecast/issues) · [Pull requests](https://github.com/abecic-pr/fra-operations-forecast/pulls)

# Work split

| Area | Responsibility |
| --- | --- |
| Data and backend | Source integration, dataset exports, runway components, baseline, evaluation and JSON contract |
| UI | Philipp’s dashboard, 48-hour outlook, quality states and API integration |
| Together | Resolve operational labels, agree the handoff, integrate and rehearse the demo |

# Current status

Antonio’s main through 1aaf46e (forecast comparison and east/west runway outlook) has been merged into the local codex/design branch, preserving both contributors’ work. His backend comparison, independent-OD model path, coordinator and flight chatbot are included. The frontend accepts schema 1.0/1.1 and uses the new per-hour direction_forecast when supplied. Reported operations at Now and predicted movements during playback are labeled separately. The dashboard has a north-up OSM runway model; the map shows landing and departure arrows across the airport. Learned actual-OD probabilities still need independent historical labels; no confidence is invented. OpenAI remains disconnected for Antonio. Status: 30 October 2026; local checks complete, push being finalized.

# Design handoff

**Design chat snapshot: 30 October 2026.** Philipp owns design; Antonio gathers data and develops the backend. Runway 18 remains the only runway in scope. The right inspector is narrower, the summary is much smaller, and eyebrow labels are removed. Both panels fit the desktop viewport. Dashboard, map and timeline now share the live provider. Buttons now share soft press feedback, selections slide, switches animate, the layer panel eases open/closed, and chart/playback/refresh controls have subtle transitions. System reduced-motion settings suppress decorative motion. The production build and wind/color-boundary checks passed; browser checks covered layer switches, horizons, keyboard timeline selection and green/unknown states, with no console warnings or errors. This design is published on codex/design at 2ee9c04. The map remains focused on Runway 18; dashboard design preview also illustrates Centre 07C/25C.

## Repository alignment

The combined airport-direction UI and Antonio main history through 1aaf46e are tested on codex/design and ready for the requested GitHub push. All 111 backend tests pass with the declared optional ML dependency installed in an isolated environment; frontend wind/direction checks and production build pass. Browser checks confirm the real map arrows, dashboard airport model, reported/forecast distinction, unavailable-direction gaps, timeline and map controls, with no console warnings or errors. No merge into main is performed. Antonio’s /api/chat is preserved; the dashboard visual assistant uses /api/weather-bot with its own status and preview routes. Verification and issued-forecast archiving remain intact; OpenAI remains disconnected.

GitHub confirmed during push that aiw26 was renamed to fra-operations-forecast. The old URL redirects to the same repository. The local remote and README now use the confirmed name; there is no separate-repository mismatch.

## App and design decisions

- **Dashboard:** Primary metrics are observed Runway 18 tailwind, gust crosswind and the next flagged forecast hour. Takeoff tailwind must remain below 15 kt; landing tailwind below 10 kt; crosswind above 40 kt including gusts exceeds the shared case limit. The stricter landing rule drives airport-wide 07/25 direction switches and does not create a landing mode on southbound-only Runway 18. The backend already implements these limits and >30-minute persistence; only the UI/data adapter was extended. Current observation KPIs remain fixed during forecast selection. A satellite map preview with wind animation and real RWY18 geometry opens the full map; selected-time components and peak next-six-hour tailwind sit beside it. Reported OD/source/since time, current landing tailwind and the baseline next direction change appear below. Three synchronized charts show RWY18 departure tailwind (15 kt), gust crosswind (40 kt) and landing tailwind on hourly forecast OD (10 kt). The 6/12/24/48h display window starts at forecast issue time; next flagged hour and peak next 6h use the actual clock. Raw source details and missing data are visible. Current/max/average total speed remain supporting metrics. Flights remain Unassigned unless the source provides actual assignments; OpenAI remains disconnected. The dashboard now includes a compact north-up airport model using real OSM runway geometry. Landing arrows identify Northwest and South; departure arrows identify Centre and southbound-only RWY18. In OD07 all parallel movements point east (070°T); OD25 points west (250°T). The full map shows the same configuration with an Eastbound/Westbound badge and separate landing/departure key. Aircraft arrows are distinct from wind particles, never individual flight assignments or an official operational-status assertion. At Now the configuration comes from reported operations; forecast selection uses Antonio’s enriched per-hour direction and explicit method. Missing/disconnected directions suppress the parallel arrows; 18’s fixed physical direction remains south. Both landing and takeoff prefer headwind, with the brief’s permitted tailwind thresholds and landing-led switching rules unchanged.

- **Apple design reference:** [Emil Kowalski's Apple Design skill](https://github.com/emilkowalski/skills/tree/main/skills/apple-design) was installed locally at Philipp's request. It is an independent skill, not an official Apple release, and is available automatically from the next turn. The KPI design applies system typography, size-specific spacing, restrained depth, shared scales and reduced-motion/contrast support. No app dependencies were added. Production build, wind/KPI calculations and browser review passed; no console warnings or errors were reported.

- **Map view:** full-screen satellite imagery with OpenStreetMap Runway 18 geometry and a street-map fallback. Other runway overlays, labels and selectors are hidden. Wind particles follow geographically sampled vectors; color shows total wind speed in knots. The legend distinguishes wind-from direction from the direction particles travel.

- **Airport layers and runway colors:** controls for wind speed/flow, animation, Runway 18 and the airport boundary. The runway geometry, summary dot and border share the selected time's wind-suitability color: green within limits; yellow at ≥11 kt tailwind or ≥36 kt mean/gust crosswind (4 kt below the limits); red at ≥15 kt tailwind or >40 kt mean/gust crosswind, or backend not_usable. Yellow is a visual proximity warning, not a predicted closure probability. Missing data stays gray unless known wind warrants yellow/red; connection loss stays gray. These are wind conditions, not an official operational closure feed. Existing backend limits and persistence rules remain unchanged. Reduced-motion preferences default to a still wind field.

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

The published implementation passes the production build, wind/comparison/color/departure checks and all 36 backend tests. Browser checks cover compact map panels, real clock, provisional measured wind, interaction states, dashboard flight details and the chatbot’s real-data preview. Local chat endpoints return an explicit missing-key response and reject cross-origin requests. No console warnings or errors were reported. OpenAI provider calls are mocked in tests; a real completion remains unverified by explicit user choice.

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

Dashboard validation: production build, wind/color/departure adapter checks and all 36 backend tests passed. Browser checks verified real flights, flight details, demo switching and the hero/queue layout; no console warnings or errors were reported. Published with the AI-bot handoff on codex/design.

## AI Weather Bot handoff

Philipp requested a chatbot with project data access, graphics and maps. The dashboard panel and Python backend are implemented and published on codex/design at 2ee9c04. At Philipp's explicit request, leave OpenAI disconnected; Antonio will connect it from the repository. No API key is committed and no real OpenAI completion has been tested.

The bot uses OpenAI Responses with server-side credentials, medium internal reasoning, read-only data retrieval and strict structured replies. It returns a concise explanation and source IDs, not hidden chain-of-thought. Charts use actual saved baseline values and preserve missing-data gaps; interactive OpenStreetMap responses show real Runway 18 geometry. A clearly labeled non-AI data preview works without a key.

Data access covers normalized project JSON/CSV/JSONL, checked measurements, past issued forecasts, operations snapshots, departures, available local metrics, source records, documentation and a dated shared-knowledge snapshot. It excludes secrets, arbitrary files, raw ZIP/binary caches and model weights. The app does not fetch this Page live; docs/shared-knowledge.md is its dated reference copy. Missing ML artifacts remain unavailable. Data is read-only; the bot cannot close runways or assign flights.

Setup and contract: docs/ai-weather-bot.md and .env.example. API routes are GET /api/chat/status, GET /api/chat/preview and POST /api/chat. Same-origin requests, bounded inputs/tool rounds and one active answer limit local use. OpenAI model defaults to gpt-5-mini, configurable on the backend. Conversation state stays in browser memory and requests use store:false.

- [ ] Antonio: add a server-only OPENAI_API_KEY, verify model access and test a real tool-backed answer, follow-up question, chart, map and missing-data case. The UI checks configuration automatically; key presence is not provider authentication. Keep the key out of VITE_ variables, commits and browser storage.

- [ ] Antonio: reconcile the broader main ML/schema 1.1 integration with this schema 1.0 design branch before enabling corrected weather/probabilities.

Validation: production build, wind/departure/color checks and all 36 backend tests pass. Mocked API tests cover tool calls and output validation; local endpoint tests confirm preview, missing-key 503 and cross-origin 403. Browser review confirmed the preview chart, interactive map, evidence section and disconnected question handling with no console warnings or errors.

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

## Concurrent integration reconciled

Antonio’s design-branch merge b5e8ab5 arrived during upload. Its `/api/weather-bot` dashboard contract and module name are retained alongside the separate `/api/chat` flight assistant. Its verification archive fix accepts additive schema 1.1 while preserving baseline components; its additional route and archive tests are retained. Airport direction visuals and enriched forecast adapter remain from this design increment.

## Parallel runway traffic increment — 30 October 2026

User clarified the new flight feature covers all parallel runways except RWY18. Added official FRA arrival/departure board collection and GET /api/traffic, searchable paginated flights, separate landing/departure wind cards, confirmed-next-flight limit selection and simulated plane preview. Initial collection: 993 arrivals and 1,051 departures, with no source runway assignments or aircraft coordinates. Live mode remains Unassigned and hides aircraft markers; preview is explicitly simulated. Antonio must add confirmed runway assignments, exact runway ends and fresh source-timestamped positions to docs/airport-traffic.md. Historical wind analysis and the new main presentation page are retained. Main upload is being finalized.

Antonio’s hosting commit ad9fdda is also merged. Its Vercel/API changes and tile cleanup fix are preserved; traffic.json is added to the deployment snapshot allowlist. The final combined frontend build passes. No production deployment is performed by this chat; this handoff publishes the code to main.

## Runway 18 priority restored — 30 October 2026

Philipp corrected the interface hierarchy: Runway 18 is the central purpose of the software. The parallel-runway flight feature is supporting context, not a replacement. The dashboard again leads with Runway 18 KPIs, status and wind preview; Other runways & flights is a secondary expandable section. The map defaults to the original compact Runway 18 status panel and WindForecast chart (forecast, screened measurements, clock and playback), with its status-colored runway highlight and close framing. Other runways is available through an explicit optional map view. No forecasting rules, data sources or backend features are removed.

## Current dashboard priority and restriction planning

Runway 18 current departure wind, next temporary wind-restriction window and flight review lead the dashboard. Details remain expandable. Yellow now begins 4 kt below critical limits (11 departure tailwind, 6 landing tailwind, 36 mean/gust crosswind). Existing hard limits are unchanged; 18 is departure-only. Native raw 15-minute forecast samples are exposed additively for estimated short windows, without filling gaps or claiming exact closures. Confirmed 18 flights and unassigned possible overlaps are separate; board times are proxies. Centre alternatives are local drafts, weather screened but not officially available/capacity checked. A labeled example exercises a 30-minute restriction in two hours. Antonio must supply confirmed assignments, runway movement times and actual availability/capacity before operational rerouting.
