# FRA Operations Forecast

The [FraAlliance challenge brief](docs/challenge/README.md), with the unchanged original PDF alongside it, is this project's source of truth. Every project chat must read it under [AGENTS.md](AGENTS.md).

Forecasting runway operating direction and Runway 18 weather suitability at Frankfurt Airport.

FRA Operations Forecast is a research prototype for the **FraAlliance challenge at AI Week Frankfurt 2026**. The project aims to turn weather observations and forecasts into a probabilistic outlook for airport operations over the next 48 hours.

**Status:** Working weather ingestion and 48-hour forecast, validation-selected model comparison, GFS source comparison, discovery reports, optional AI coordinator, replay/export, and local JSON API. The one-page [model card](docs/model-card.md) records measured results and incomplete challenge deliverables. Learned operating direction still needs independent historical labels; the training/inference/evaluation code is implemented and those live probabilities remain `null`. Philipp’s dashboard and map display baseline wind, provisional measurements and real departures.

## Run the frontend locally

Use Node.js 22.12+ or 20.19+.

```sh
npm ci
# In a separate terminal, first start the Python data API below.
npm run dev
```

Open http://127.0.0.1:5173/ or the map at http://127.0.0.1:5173/#map.
The frontend now uses the local data API. Start it in a separate terminal:

```sh
python3 -m fra_forecast refresh --live-only --history-days 1 --archive-days 0
python3 -m fra_forecast serve
```

Only Runway 18 is highlighted. The blue chart line is forecast tailwind and the
green line is source-screened DWD measured tailwind, labeled provisional. The
clock marker shows actual UTC time independently of forecast playback. The UI
reads saved data every 30 seconds and requests fresh sources every 10 minutes
while visible. Manual refresh is also available. Never show an accuracy score
until an observation matches a forecast archived before that observation time.

```sh
npm run check:wind
npm run build
```

See [frontend wind integration](docs/frontend-wind.md) for the provider boundary,
schema 1.0/1.1 adapter, controls, demo limitations and later API integration. See
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
git clone https://github.com/abecic-pr/fra-operations-forecast.git
cd fra-operations-forecast
```

Python 3.11 or newer is required. The baseline backend uses the standard library; model comparison and training use the existing optional ML dependencies.

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
endpoint. A standalone presentation page is at `/how-it-works`. It binds only to `127.0.0.1`;
choose a different port with `serve --port 8001`. The teammate's frontend can
proxy `/api/*` to this server; see the integration notes in the data contract.

Brand assets and illustrative design references are in [branding/](branding/README.md).

## ML presentation page

Run `python3 -m fra_forecast serve`, then open
[How our ML works](http://127.0.0.1:8000/how-it-works). Restart an already-running
server to load the new route. This standalone page was added at the user's
request; the teammate's main UI remains separately owned.

The page explains data alignment, residual correction, empirical uncertainty,
and the 48-hour runway outputs. Select the four steps with a pointer or keyboard
arrow keys. Its validation comparison and 1/6/24-hour test scores come from the
existing `/api/model-comparison` report, with explicit exploratory-test and
missing-label limitations. Without local artifacts, the explanation still works
and the results show an unavailable state. It adds no dependencies, network
weather refreshes, or changes to forecast JSON. The teammate can link directly to
`/how-it-works`; a frontend proxy must forward that path and its assets, plus
`/api/model-comparison`. Page files are in `fra_forecast/presentation/`.

## Wind ML quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ml]'

# Cached public backfill: 180 completed days, four ICON-EU runs per day.
python -m fra_forecast prepare-ml --days 180

# Fit corrections, select on validation dates, calibrate on separate dates,
# and evaluate once on the chronological final test set.
python -m fra_forecast train-ml

# Load the local model and append ML outputs to the existing raw forecast.
python -m fra_forecast refresh --live-only
python -m fra_forecast serve
```

Read `forecast[].ml` for corrected wind and RWY18 weather probability. The existing
fields continue to contain the raw weather/rule baseline. See
[the ML guide](docs/wind-ml.md) for targets, time alignment, metrics, and fallbacks.
The first measured outcome is recorded in [the evaluation summary](docs/ml-evaluation.md).
Model metrics are available at `/api/model-metrics`. Training data, cached
responses, and model artifacts remain in the ignored `data/` directory.

Historical publication times are estimated, and DWD references may contain later
quality corrections. Reported backtests are conditional on those assumptions.
Probability outputs are provisional estimates; their reliability and rare-event
coverage must be read alongside the score. No improvement is assumed before evaluation.

## Runway 18 departure assessments

Normal refresh now also reads Frankfurt Airport's public departure-board feed
and matches each upcoming flight to RWY18 weather. No flight API key is needed.

```bash
# Refresh just the flight list using the saved weather snapshot.
python -m fra_forecast refresh-departures --hours 48

# Weather-only refresh if flight data is not needed.
python -m fra_forecast refresh --live-only --no-departures
```

Read `/api/runway18/departures` or `data/runway18-departures.json`.
The board provides schedules and departure estimates, but no estimated takeoff
times or assigned runways. Flights are assessed **for** RWY18 weather; they are
not presented as confirmed RWY18 departures. Individual runway-use probability
stays `null`. See [the departure data contract](docs/runway18-departures.md).

Supply independently verified labels with `--labels path/to/operations.csv`,
using the header in [examples/operations-labels.csv](examples/operations-labels.csv).
The template intentionally contains no invented records. Historical forecast
publication times currently use a clearly marked four-hour estimate, so this
dataset is not yet evidence of leakage-free model accuracy.

The six-hour hackathon constraint and division of work are recorded in
[AGENTS.md](AGENTS.md). The teammate owns UI; backend work prioritizes runnable increments.

## Airport and flight chatbot

`POST /api/chat` answers questions from saved airport forecasts and public flight
weather assessments, using an OpenAI key on the backend. It supports flight-number
and codeshare lookup, follow-up context, source evidence and freshness warnings.
Set `OPENAI_API_KEY` and `FRA_CHAT_MODEL` before starting the server. The teammate
owns the chat panel; see [setup and the JSON contract](docs/chatbot.md).

## Project context

Built for **AI Week Frankfurt, 30 October 2026**, based on the FraAlliance brief *Frankfurt Airport Operating Direction Forecast*.

The prototype is intended for research and demonstration. Its predictions are not operational air traffic control instructions.

### AI Weather Bot

The dashboard includes a project assistant with data lookups, forecast charts and an interactive airport map. It is intentionally **disconnected from OpenAI** for Antonio's handoff. Use Preview charts & map to review real saved data without a key.

To enable AI answers, add `OPENAI_API_KEY` to the ignored root `.env` file (see `.env.example`). The default backend model is `gpt-5-mini`; set `OPENAI_MODEL` to change it. Keep the key on the Python backend, never in VITE_ variables. The status refreshes automatically; no key is committed. A real OpenAI completion still needs account/model access and has not been tested without a key.

See [AI Weather Bot setup and data contract](docs/ai-weather-bot.md) for source scope, limits and the `/api/weather-bot` endpoints. The existing `/api/chat` flight assistant remains separate. The model reasons internally and returns a short explanation with sources. Weather suitability and official runway closure remain distinct.

## Comparison demo and submission handoff

The [eastbound/westbound forecast](docs/operating-direction.md) now explicitly maps
07/25 predictions to landing direction, approach side, and Centre departure runway.
Runway 18 stays southbound in both directions. Read `direction_forecast` in either
forecast endpoint; each point states whether it is learned or weather-rule based.

The [comparison runbook](docs/model-comparison.md) covers discovery, five scored
candidates, live GFS comparison, the optional AI coordinator, independent OD
training, replay/export, and the local frozen-artifact bundle. The selected
Ridge correction reduced validation vector RMSE from 5.517 to 4.377 kt.
RWY18 probability improvement and actual operating-direction skill are not established.

```bash
source .venv/bin/activate
python -m fra_forecast compare-models
python -m fra_forecast discover-data --probe-gfs
python -m fra_forecast refresh --live-only --no-departures
python -m fra_forecast refresh-comparison
python -m fra_forecast serve
```

The one-page submission card is [available as PDF](output/pdf/model-card.pdf)
with [editable Markdown](docs/model-card.md). Jury dates and issue format are
absent from the brief: populate [the issue template](examples/jury-issues.csv)
only with actual organizer inputs before running `export-submission`.
