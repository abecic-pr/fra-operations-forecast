# FRA Operations Forecast

Forecasting runway operating direction and Runway 18 weather suitability at Frankfurt Airport.

FRA Operations Forecast is a research prototype for the **FraAlliance challenge at AI Week Frankfurt 2026**. The project aims to turn weather observations and forecasts into a probabilistic outlook for airport operations over the next 48 hours.

**Status:** Initial project setup. The forecasting model, data pipeline, and application are planned and are not yet implemented.

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

Application setup, dependencies, and run commands will be added when implementation begins.

## Project context

Built for **AI Week Frankfurt, 30 October 2026**, based on the FraAlliance brief *Frankfurt Airport Operating Direction Forecast*.

The prototype is intended for research and demonstration. Its predictions are not operational air traffic control instructions.
