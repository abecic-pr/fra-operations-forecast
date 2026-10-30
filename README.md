# aiw26

Frankfurt Airport operating direction and Runway 18 forecast for AI Week 2026.

Philipp owns design; Antonio gathers data. Read [the case notes](docs/CASE.md) for the targets, wind-rule baseline, evaluation requirements and proposed data handoff.

## Run locally

Use Node.js 22.12+ (or 20.19+) and npm.

```sh
npm ci
npm run dev
```

Open http://localhost:5173. The server is bound to this computer only. The current React + TypeScript page is a starting point with empty states; it has no weather feed or trained model.

Switch between **Dashboard** (forecast summary) and **Map view** (full-screen interactive map). Direct map link: http://localhost:5173/#map. The map defaults to Esri satellite imagery with real OpenStreetMap airport overlays; a street-map option is available in Map layers. It supports panning, zoom, runway selection and airport boundary / runway / terminal toggles. It requires internet for base-map tiles; the airport overlay is a bundled OSM extract. See [map data sources](public/data/README.md).

The floating panels show selected-runway status and a tailwind chart with 12/24/48-hour horizons. Forecasts remain empty until connected. **Preview sample** displays explicitly illustrative values for design review; it does not alter actual runway status. The case brief's 15 kt departure and 10 kt landing tailwind limits are chart references; crosswind including gusts is shown separately. This UI does not yet calculate wind components, predict availability, or connect to a backend.

Before pushing, check the production build:

```sh
npm run build
npm run preview
```

Preview is at http://localhost:4173. Stop either server with Ctrl+C.

## Work together

Use separate branches, for example `codex/design` and `codex/data`. Pull the latest `main` before starting a branch; commit and push your own branch, then merge through a pull request. Check the combined changes locally after merging.

- UI: `src/`
- Shared requirements and data handoff: `docs/CASE.md`
- Large local data downloads: `data/raw/` (ignored)
- Private data: `data/private/` (ignored)

Commit `package-lock.json` when dependencies change; use `npm ci` after pulling those changes. Do not commit secrets, `node_modules`, build output or large raw datasets. Nothing is deployed automatically by this starter.
