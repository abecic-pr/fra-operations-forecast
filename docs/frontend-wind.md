# Runway 18 wind UI

The active frontend uses **dynamic demo data**, not live weather. It focuses on Runway 18. Other runway geometry remains in the original OSM extract but is not highlighted, labeled or selectable by the app.

## Local development

Use Node.js 22.12+ or 20.19+.

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173/#map. The Dashboard and Map share the same dataset and selected forecast hour. The map has satellite and street-map backgrounds, a Runway 18 overlay, a synthetic wind-speed color field, and animated particles that travel with the wind. The legend reports total wind speed in knots; the chart reports the tailwind component on the 180-degree runway.

Use the 12/24/48-hour controls, timeline, chart selection or forecast playback to change the forecast time. Map layers provides wind visibility and animation controls. Reduced-motion preferences default to a still wind field. Pan and zoom rebuild the geographic field, and animation is cleaned up when the layer or Map view is removed.

## Replace demo data later

`src/data/wind.ts` is the only weather boundary:

- `WindProvider.load(signal)` returns a normalized `WindDataset` containing timestamps, vector components, gusts, runway-relative components, weather state and a nullable probability.
- `demoWindProvider` is active in `src/main.tsx`. It generates 49 time-stamped points and synthetic spatial variation around EDDF. All probabilities remain null.
- `backendWindProvider('/api/forecast')` is an inactive integration option. Its adapter matches Antonio's schema 1.0 in [backend-data.md](backend-data.md): `forecast[].wind_speed_kt`, `wind_from_deg_true`, `wind_gust_kt`, `runway_wind['18']`, `rwy18_weather_state`, and `p_rwy18_weather_usable`.
- Directions are meteorological **from** true north. The renderer consumes eastward/northward vectors; it does not fetch or generate weather. Chart, map and summary use the same selected valid time.
- Missing values remain null and plot gaps. Future samples are not presented as current observations. Model confidence is not fabricated from deterministic suitability.

Antonio's current snapshot supplies an **airport point forecast**, not a spatial wind grid. The adapter sets `spatialMode: 'uniform-airport'`. That view must be described as uniform airport wind; the synthetic spatial variation must not be retained as if it were real. A future real grid can replace `sampleField` while the canvas and controls remain unchanged.

To connect after agreement, change the provider in `src/main.tsx`, start Antonio's loopback API, and add a same-origin Vite `/api` proxy following [backend-data.md](backend-data.md). Do not silently fall back from a failed live request to demo data. The current version does not request the API or refresh outside providers.

Weather suitability and observed runway use are distinct from official runway status. Demo status is based on the case's 15 kt departure tailwind and >40 kt crosswind limits. Gust crosswind uses the mean direction for this synthetic fixture. Next change is the first hourly weather-state change; it is not a calibrated prediction.

## Verification

```sh
npm run check:wind
npm run build
```

The wind checks cover direction conversion, runway thresholds, gust/missing-data behavior, map/chart agreement at EDDF, interpolation, issue/valid-time alignment and the backend adapter. Preview the production build with `npm run preview` at http://127.0.0.1:4173.
