# Documentation

## Start here

- [Challenge brief](challenge/README.md): the FraAlliance requirements, with the [original PDF](challenge/AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf).
- [Model card](model-card.md): one page on sources, quality and key drivers ([PDF](../output/pdf/model-card.pdf)). Submitted on 30 October 2026.
- [Online learning](online-learning.md): the hourly correction that learns from forecast error, and its out-of-sample results.
- [Operating direction](operating-direction.md): how 07/25 predictions map to landing direction, approach side and runways.

## Models and evaluation

- [Wind correction ML](wind-ml.md): targets, time alignment, metrics and fallbacks.
- [ML improvement and 07/25 history](ml-improvement.md): the trained direction model and its measured results.
- [Operations label research](operations-label-research.md): where the direction history comes from, and its limits.
- [Model comparison](model-comparison.md): candidates, GFS comparison, the optional AI coordinator and replay/export.

## Data

- [Data sources](data-sources.md): public sources researched and selected, with [machine checks](source-checks.json).
- [App and model data](app-data.md): the recommended data contract and evaluation plan.
- [Backend data contract](backend-data.md): JSON served to the dashboard (schemas 1.0/1.1 and later additions).
- [Runway 18 departures](runway18-departures.md): matching public flight-board departures to Runway 18 weather.
- [Airport traffic](airport-traffic.md): the parallel-runway arrivals and departures view.

## App

- [Runway 18 live wind UI](frontend-wind.md): the dashboard's data adapter and controls.
- [Airport and flight chatbot](chatbot.md) and [AI Weather Bot](ai-weather-bot.md): optional assistants (need an OpenAI key on the backend).
- [Deployment](deployment.md): Vercel setup and data packaging.

## Archive

[Hackathon working notes](archive/README.md): plans and snapshots from 30 October 2026, kept for traceability.
