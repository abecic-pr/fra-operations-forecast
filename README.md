# FRA Operations Forecast

Forecasting runway operating direction and Runway 18 weather suitability at Frankfurt Airport.

FRA Operations Forecast is a research prototype for the **FraAlliance challenge at AI Week Frankfurt 2026**. The project aims to turn weather observations and forecasts into a probabilistic outlook for airport operations over the next 48 hours.

**Status:** Public weather ingestion, a versioned challenge-rule baseline, 48-hour JSON output, a historical dataset export, and a local JSON API. The Runway 18 frontend provides Dashboard and Map modes with an animated wind layer, timeline playback and shared dynamic demo data. Live UI integration remains pending; the temporary data-preview UI has been removed. Machine-learning training remains to be implemented. Baseline probabilities are `null`; independent historical operating labels are still needed for model evaluation.

## Run the frontend locally

Use Node.js 22.12+ or 20.19+.

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173/ or the map at http://127.0.0.1:5173/#map.
The frontend currently uses explicitly labeled synthetic wind data. It does not
request the backend or refresh live providers. Only Runway 18 is highlighted.
The color layer shows total wind speed; the chart shows departure tailwind.
Map, chart and summary share the same forecast time.

```sh
npm run check:wind
npm run build
```

See [frontend wind integration](docs/frontend-wind.md) for the provider boundary,
schema 1.0 adapter, controls, demo limitations and later API integration. See
[map data sources](public/data/README.md) for OSM and satellite attribution.
Use separate branches and test locally before pushing; the shared project
knowledge-base rule is in [AGENTS.md](AGENTS.md).

## Objective

Develop and evaluate a machine-learning model that predicts:

- **Operating direction:** whether Frankfurt is expected to use direction 07 (eastbound) or 25 (westbound).
- **Runway 18 suitability:** the probability that wind conditions allow departures from Runway 18 West.
- **Upcoming changes:** the next likely operating-direction change and its uncertainty.

The model should improve on the weather-rule baseline defined in the challenge brief.

## Planned forecast outputs

| Output | Description |
| --- | --- |
| Hourly outlook | Predictions for each hour through a 48-hour horizon |
| Operating direction | Predicted 07/25 direction and associated probabilities |
| Runway 18 suitability | Probability of suitable wind conditions for departures |
| Change outlook | Expected timing or time window of the next direction change |
| Wind conditions | Wind speed, direction, gusts, and runway-relative components |
| Data freshness | Observation time, forecast issue time, and source information |

Weather suitability and observed runway use are separate concepts. A period without departures does not by itself establish that a runway was unavailable.

## Data approach

The planned dataset combines airport weather observations, archived weather forecasts, and recorded operating-direction or runway-use data. Candidate weather sources include:

- [DWD Open Data](https://opendata.dwd.de/) for station observations and numerical forecasts.
- [Aviation Weather Center](https://aviationweather.gov/data/api/) for EDDF METAR and TAF reports.
- [Open-Meteo](https://open-meteo.com/en/docs) for forecast access, including [individual archived model runs](https://open-meteo.com/en/docs/single-runs-api).

Each record should preserve its source, units, observation or valid time, and the time it became available. Final source selection, coverage, and limitations will be documented alongside the implementation.

## Evaluation

Evaluate forecasts on held-out periods at **1-hour, 6-hour, and 24-hour lead times**. Only information available when each forecast would have been issued may be used as input.

Compare the model with the challenge's rule-based baseline and a persistence baseline. Report classification performance, probability calibration, and change-timing error where reliable reference labels are available.

## Working with the repository

```bash
git clone https://github.com/abecic-pr/aiw26.git
cd aiw26
```

Python 3.11 or newer is required. The current backend uses only the standard library.

```bash
# Current observations and 48-hour forecast; requires internet access.
python3 -m fra_forecast refresh --live-only

# Also collect 14 days of observations and seven archived daily forecast runs.
python3 -m fra_forecast refresh

# Run focused offline checks.
python3 -m unittest discover -s tests -v

# Serve forecast JSON at http://127.0.0.1:8000/api/forecast.
python3 -m fra_forecast serve
```

Outputs are written to the ignored `data/` directory. The teammate can consume
`data/forecast.json`; its contract is documented in [docs/backend-data.md](docs/backend-data.md).
The API exposes saved forecasts and source diagnostics, plus a manual refresh
endpoint. It serves no HTML or static UI assets. It binds only to `127.0.0.1`;
choose a different port with `serve --port 8001`. The teammate's frontend can
proxy `/api/*` to this server; see the integration notes in the data contract.

Brand assets and illustrative design references are in [branding/](branding/README.md).

Supply independently verified labels with `--labels path/to/operations.csv`,
using the header in [examples/operations-labels.csv](examples/operations-labels.csv).
The template intentionally contains no invented records. Historical forecast
publication times currently use a clearly marked four-hour estimate, so this
dataset is not yet evidence of leakage-free model accuracy.

The six-hour hackathon constraint and division of work are recorded in
[AGENTS.md](AGENTS.md). The teammate owns UI; backend work prioritizes runnable increments.

## Project context

Built for **AI Week Frankfurt, 30 October 2026**, based on the FraAlliance brief *Frankfurt Airport Operating Direction Forecast*.

The prototype is intended for research and demonstration. Its predictions are not operational air traffic control instructions.
