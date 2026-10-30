# Parallel runway flight overview

Scope agreed 30 October 2026: the new landing/departure overview covers **07L/25R, 07C/25C and 07R/25L**, excluding departure-only RWY18. Runway 18 remains the primary application focus and leads the dashboard. The parallel-runway flight overview is secondary, under Other runways & flights. The map defaults to the original Runway 18 status and measured/forecast chart; Other runways is an optional view.

`GET /api/traffic` reads `data/traffic.json`, collected with `python -m fra_forecast.traffic`. Normal weather refresh also collects traffic unless `--no-departures` is used. The UI polls the saved snapshot once per minute; external data refresh follows the existing refresh action. The collector requests the official FRA passenger arrivals and departures boards for 48 hours using bounded pagination, excluding completed/cancelled/ground services. Sources include coverage and error metadata. This is not a complete private/cargo aircraft inventory.

The initial live collection contained 993 arrivals and 1,051 departures. **Neither runway assignments nor aircraft positions are supplied**. Real flights remain Unassigned. Published estimated/scheduled board times are not wheels-off/touchdown times. Airport-wide unassigned flights appear in a searchable, paginated fallback list; they are never called confirmed users of the selected runway.

## Future source boundary

Traffic schema 1.0: `generated_at`, `sources` (arrivals/departures with `status`), and `flights` with `id`, `number`, `operation` (`landing` / `departure`), `airport` (origin for arrivals, destination for departures), `scheduled_at`, optional `estimated_at`, `status`, `assigned_runway`, `assignment_status` and `position`.

A future source may set `assignment_status: confirmed` and an actual runway end (`07L`, `25R`, `07C`, `25C`, `07R`, `25L`) or its canonical pair. Only confirmed assignments participate in next-movement selection; snapshots older than 15 minutes or over five minutes in the future do not. Cancelled/completed/past flights are excluded. The exact runway end, when supplied, determines the wind projection, rather than silently substituting an airport forecast direction.

A future `position` object needs numeric `latitude`, `longitude`, `heading_deg_true`, an ISO `observed_at` and HTTPS `source_url`. The adapter validates coordinates against the airport region and numeric ranges. Map positions older than two minutes or more than five seconds in the future are hidden. No aircraft position is inferred from a flight time, airport name or assigned runway. RWY18 assignments are excluded from this feature.

## Presentation

Dashboard and map share the selected parallel runway and Live schedule / Design preview choice. Separate landing/departure cards show sample tailwind and gust crosswind, with thresholds **tailwind <10 kt for landing, <15 kt for departure; crosswind ≤40 kt including gusts**. Unknown gust or direction prevents a green result. Yellow is a visual caution from 4 kt below a limit (6 kt landing tailwind, 11 kt departure tailwind, 36 kt crosswind). These are wind suitability states, not ATC clearance or official runway availability.

By default the next fresh, known, confirmed assigned flight selects the applicable limit and active status card. Its published board time selects exact/bracketing hourly forecast samples (or a next-hour proxy within one hour); probabilities are not interpolated, gaps are not extrapolated and matching endpoints do not establish continuous suitability. With no next assignment, both limits stay visible and current observed weather is shown on reported OD. The map forecast uses the exact assigned runway end when known, otherwise the backend hourly operating direction.

Design preview is explicitly simulated and initially off. It provides illustrative assigned flights and moving aircraft for the three parallel runways; it demonstrates landing/departure automatic limits without pretending the public schedule has positions. Wind data remains the project forecast. Airport direction arrows continue to describe the challenge runway roles, rather than individual assignments.

Antonio handoff: add independently sourced, timestamped confirmed runway assignments and ADS-B/ground positions to this contract. Verify provider coverage, update cadence and positions before enabling real map markers. Preserve nulls and source provenance until then.

Runway 18 restriction planning now retains confirmed 18 departures in the shared adapter. The parallel-runway view still excludes them. See docs/frontend-wind.md for impact matching, draft alternatives and missing operational availability data.
