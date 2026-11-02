# First wind ML evaluation

The three correction models were trained. Neither wind nor gust correction passed the validation gate, so deployed point forecasts retain raw ICON-EU winds. Empirical RWY18 weather probabilities are provisional and have low adverse-event coverage.

Generated from local metrics trained at `2026-10-30T11:51:16Z`; dataset SHA-256 `66fe17ae25c62ea2fda4031a678e4bfe379f27a268ea98dc4dfd56098aa2de1b`.

## Data and split

- Requested 180 days and 720 original forecast runs.
- 715 responses retrieved; 714 runs contributed 48,552 training rows. Five runs were unavailable and one response contained no wind data.
- DWD station 01420, 26,358 ten-minute records; gust targets require all six preceding-hour samples.
- Four chronological partitions; overlapping future targets are purged before each boundary.

| Partition | Rows | First issue UTC | Last issue UTC |
| --- | ---: | --- | --- |
| train | 28,560 | 2026-04-30T04:00:00Z | 2026-08-15T22:00:00Z |
| selection | 4,488 | 2026-08-16T04:00:00Z | 2026-09-02T22:00:00Z |
| calibration | 4,488 | 2026-09-03T04:00:00Z | 2026-09-20T22:00:00Z |
| test | 9,792 | 2026-09-21T04:00:00Z | 2026-10-26T22:00:00Z |

## Validation decision

- Wind-vector RMSE: raw **5.52 kt**, candidate **5.71 kt**. The candidate was rejected despite its lower scalar speed MAE.
- Gust MAE with the selected wind configuration: raw **3.75 kt**, candidate **5.28 kt**. The candidate was rejected.
- Fixed model settings; no hyperparameter search or tuning on final-test results.

## Final chronological test

The selected point forecast equals raw ICON-EU. These are measured forecast errors, not operational-direction accuracy.

| Horizon | Samples | Speed MAE, kt | Gust MAE, kt | Vector RMSE, kt | Direction MAE, degrees |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 h | 144 | 2.91 | 3.12 | 4.23 | 17.67 |
| 6 h | 144 | 3.25 | 3.22 | 4.49 | 16.46 |
| 24 h | 144 | 3.22 | 3.14 | 4.52 | 18.79 |
| 48 h | 144 | 3.19 | 3.24 | 4.55 | 21.40 |

At 48 hours, observation persistence had speed MAE **3.91 kt**, gust MAE **5.61 kt**, and vector RMSE **8.84 kt**.

## Limits and handoff

- RWY18 probability Brier score over 1–48 hours: **0.001178**. There was only **1 distinct adverse valid time** (8 overlapping forecast cases). This is insufficient to establish extreme-event probability calibration.
- An always-weather-usable forecast scored Brier **0.001157**, slightly better than the empirical probabilities. No probability-skill improvement is established.
- Historical model publication is estimated as initialization plus four hours. Reference observations may include subsequent quality corrections.
- Actual 07/25 operating probabilities remain null pending independent labels. No operating history or operational accuracy was manufactured.
- API: `GET /api/forecast` exposes `forecast[].ml`; `GET /api/model-metrics` exposes the complete evaluation and reliability bins.
- Read [the ML guide](../wind-ml.md) and [JSON contract](../backend-data.md) before connecting the UI.
