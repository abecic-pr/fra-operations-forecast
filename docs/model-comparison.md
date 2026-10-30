# Model comparison and coordinator handoff

Implemented 30 October 2026 against the [challenge brief](challenge/README.md). This is a working backend demo, with learned operating direction and official jury forecasts still incomplete. The [model card](model-card.md) summarizes the measured results. UI remains with the teammate.

## Run the demo

Use the existing `.venv` or install `python -m pip install -e '.[ml]'`. No new dependency was added. From a clean checkout, run `prepare-ml --days 180` and `train-ml` as described in [wind-ml.md](wind-ml.md); the current workspace already has that cache and artifact.

```bash
source .venv/bin/activate
python -m fra_forecast compare-models
python -m fra_forecast discover-data --probe-gfs
python -m fra_forecast refresh --live-only --no-departures
python -m fra_forecast refresh-comparison
python -m fra_forecast serve
```

`compare-models` trains a fixed Ridge residual correction, reuses compatible boosting estimators, evaluates five candidates, and freezes the validation choice. It reuses cached weather; it does not backfill again. `discover-data` reports source inventory, missing fields, validation-period lead/sector/threshold patterns, residual correlations, and disagreement examples. `--probe-gfs` checks only four explicit recent/archive runs. All four returned 96 hours including gusts in the implementation smoke check. GFS stays unranked: matched historical skill and gust-interval compatibility are unverified.

`refresh-comparison` uses the saved snapshot's exact 48 hourly targets and eligible ICON-EU run, plus one optional GFS run. It does not train or change `forecast.json`. Repeat it after refreshing the main forecast. Use `--no-gfs` for the cached-weather path. A snapshot older than two hours is marked `stale_snapshot`. Observation persistence is absent when no observation was available by the reference time; a later scrape is not backdated.

## Fixed selection and uncertainty

The candidates are raw ICON-EU, observation persistence, boosting correction, Ridge correction, and an equal blend of raw/boosting/Ridge. GFS is a sixth live comparison only. The blend averages u/v vectors, not angles; an absent member gust makes the blend gust unavailable. Persistence is a reference, not a selectable winner.

Selection uses only the purged validation partition, at least 100 wind and gust cases over 10 issue dates, and complete raw-reference coverage. A candidate must lower vector RMSE, keep speed MAE within 2% of raw, and not worsen gust MAE. Lowest vector RMSE wins, then gust MAE and stable candidate order. Otherwise raw wins. The saved weights are either one candidate at 1.0 or the predefined equal blend; the LLM cannot set weights. Missing selected wind falls back to raw with a reason; missing gust stays missing.

Raw and the selected candidate each receive their own residual pools from a separate calibration partition. These produce provisional RWY18 **weather** probabilities. Other candidates have null probabilities; descriptive spread is not a confidence interval. Rule-based OD is still a baseline, not learned actual operating direction. Weather-score reports include the Section 3 rules and observation persistence on matched probability cohorts, plus always-usable, reliability bins, missed adverse cases, and false warnings.

The measured winner is `linear_correction`: validation vector RMSE **5.517 -> 4.377 kt**, speed MAE **3.794 -> 2.195 kt**, gust MAE **3.751 -> 3.019 kt** on 3,248 matched cases. The equal blend also passed, but had worse vector RMSE; boosting failed. The inspected test period is explicitly `exploratory_reused_test`. Better wind errors do not establish actual-OD skill. Selected RWY18 probability Brier **0.001195** loses to always-usable **0.001157**; eight adverse forecast cases represent just **one unique adverse timestamp**.

## Optional AI coordinator

Export `OPENAI_API_KEY` and `FRA_AGENT_MODEL` in the server/CLI environment; `.env.example` documents names only. No environment-file loader is installed. Then:

```bash
python -m fra_forecast forecast-agent --question 'Where do the forecasts disagree, and why was this model selected?'
```

The Responses API tool loop can read discovery, inspect comparisons, run the frozen comparison once, and inspect specified hours. It is limited to six model calls, 90 seconds, 1,400 output tokens per call, and no parallel tools. Tool references must be inspected before being cited. Numeric selection is read from the saved policy. It cannot train, change thresholds/weights, or fetch arbitrary URLs. Model output remains an explanation requiring review; evidence-reference validation cannot prove every sentence correct. Public forecast/report context and the question are sent to the configured model. No key is returned or written to reports.

Missing configuration or API/tool failure produces an explicitly labeled template fallback and retains the numeric policy. The current workspace has no configured key/model, so real provider execution remains unverified; mocked tool-loop, malformed-output, bounded-loop, stale-report, and mismatch checks pass. `GET /api/forecast-agent` reads the saved result and does not call the API. The separate chatbot being built in another chat is not this coordinator.

## Independent OD training and replay

```bash
python -m fra_forecast train-operations --labels path/to/verified-operations.csv
python -m fra_forecast refresh --live-only
python -m fra_forecast export-submission --issues path/to/issues.csv --output-dir data/submission --labels path/to/verified-operations.csv
```

Use [operations-labels.csv](../examples/operations-labels.csv) for interval columns. The empty template deliberately trains nothing and writes `missing_independent_labels`. [Source research](operations-label-research.md) has not verified a usable historical OD dataset. Never train on rule-generated labels.

The classifier uses scaled raw ICON-EU wind components, gust with a missing indicator, forecast horizon, and initial OD only when independently available at issue time. Fixed logistic regression is trained chronologically; sigmoid calibration uses a separate partition when both classes have coverage. Certainty is the larger class probability, labeled uncalibrated or provisional. The uncalibrated validation gate reports Brier improvement with a balanced-accuracy guard; a losing model stays experimental and the separate baseline remains available. Actual-OD accuracy, Brier, reliability, and first-change evaluation run only on independent labels. Missing target labels do not remove weather steps from the baseline. Change scoring compares first predicted change windows with actual interval boundaries on complete horizons and excludes missing truth/unknown starting state. Hourly predictions can miss within-hour reversals.

Issue CSV requires `forecast_reference_time`, explicit timezone, unique whole hours, and past/present issues. The [jury template](../examples/jury-issues.csv) is empty because the PDF specifies no dates or file schema. Replay uses archived runs and eligible model cutoffs, never today's weather or operations state. It exports exactly 48 rows per issue to `forecasts.csv`, `forecasts.json`, and `report.json`. Cutoffs include fitting, selection, and calibration evidence; provenance records real retrieval/training times separately from simulated issue times. It is a retrospective reconstruction with unverified publication delays, not a verified historical issuance.

The internal smoke issue **2026-10-20 12:00 UTC** is not a jury date. `data/submission-smoke/` contains 48 wind and RWY18 probability rows, zero learned OD rows, and `status: incomplete`. The CLI exits 1 for incomplete exports, unavailable training/agent configuration, and stale/unavailable comparisons while still saving useful reports.

## Saved outputs and reproducibility

| Output | API |
| --- | --- |
| `data/comparison/discovery.json` | `/api/discovery` |
| `data/comparison/evaluation.json` | `/api/model-comparison` |
| `data/comparison/forecast.json` | `/api/forecast-comparison` |
| `data/comparison/agent.json` | `/api/forecast-agent` |
| `data/operations-evaluation.json` | `/api/operations-metrics` |

Contracts are in [backend-data.md](backend-data.md). Models live separately in `data/models/wind-comparison-v1/`, `icon-eu-wind-v1/`, and, when actually trained, `operations-logistic-v1/`. Each new artifact has a model/report hash manifest; unsupported versions, dependencies, or mismatched hashes are rejected. Load only trusted local model files: joblib artifacts are executable serialization.

`data/` is ignored. A clean clone does not contain these trained models, reports, or data. The local `data/delivery/fra-demo-artifacts.zip` packages the two frozen wind models, dataset, comparison reports, current forecast/source metadata, and explicitly incomplete smoke export. Extract into the repository root to restore its `data/` paths. Use scikit-learn **1.9.1** for these artifacts; otherwise retrain. The archive contains no credentials and is a local handoff artifact, not an uploaded submission. Provider responses are not bundled; source URLs/hashes and research retain provenance. Later fresh backfills may differ because source data and rolling dates change.

Experiment: `ed131c7b15d7291b15a5`; dataset SHA-256: `66fe17ae25c62ea2fda4031a678e4bfe379f27a268ea98dc4dfd56098aa2de1b`. Full artifact hashes are in the bundle's model manifests. Training/selection/calibration end before **2026-09-21 00:00 UTC** under the documented one-hour observation delay. Historical availability remains assumed, and the inspected test period is not a fresh holdout.
