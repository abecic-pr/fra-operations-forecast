# Frankfurt wind correction ML

This is a small local correction model for ICON-EU at DWD station 01420. It
predicts wind speed, true direction and gusts for 48 future hourly targets.
The teammate's UI consumes the optional `forecast[].ml` block; no UI is included.

## Runnable increments

1. Install optional dependencies with `python -m pip install -e '.[ml]'` inside
   the project virtual environment.
2. Run `python -m fra_forecast prepare-ml --days 180`. It fetches DWD recent
   observations and four archived ICON-EU cycles per day, retaining raw responses,
   source checks and parsed run caches. Subsequent runs reuse successful caches
   and retry missing runs. Requests are limited to roughly one per second, with
   explicit 429 backoff. Archives use four calendar days to include model hour 72.
3. Run `python -m fra_forecast train-ml`. It creates the versioned local artifact,
   manifest and `metrics.json` under `data/models/icon-eu-wind-v1/`.
4. Run `python -m fra_forecast refresh --live-only`, then `serve`. Refresh loads
   compatible artifacts automatically. `--no-ml` explicitly disables enrichment.

All data and model artifacts are local and ignored by Git. The preparation
command also writes `data/ml/dataset.json`, `preparation-report.json`, source
checks and the observation CSV. `--max-minutes 50` limits the backfill. If it
expires, the effective dataset is restricted to the most recent 90 requested
issue dates and any remaining missing runs are disclosed. `--days 90` is the
explicit smaller-data option. No records are synthesized.

## Targets and inputs

Each row identifies one original forecast run, valid time and estimated decision
time (run initialization plus four hours). Training includes model lead hours
5–72. Public output is always 48 hours from the hourly forecast reference, rather
than 48 hours from the source model initialization.

Wind outcomes require an exact DWD observation at the valid time, representing
the preceding ten-minute mean. Wind direction is converted to meteorological
components `u = -speed*sin(direction)`, `v = -speed*cos(direction)`.
Gust outcomes require all six ten-minute maxima in the preceding hour; retain
the direction of the largest gust where available. Records with quality level
below 2 are excluded. Missing gust targets do not remove otherwise usable wind
targets. A model can retain raw gusts if too few gust targets are available.

Input features are only the original ICON-EU u/v/gust forecast, its model lead
time, sine/cosine of valid UTC hour and day of year, and a missing-gust indicator.
Future observations, runway labels and persistence-reference measurements never
enter model features. Three histogram gradient boosting regressors learn u/v/gust
residuals. Fixed settings are saved in the report; early stopping and its random
validation split are disabled. No target-dependent preprocessing is fitted.

## Selection, calibration and final test

Issue dates are split into 60% train, 20% validation/calibration, and 20% test.
The middle 20% is split equally into correction selection and independent error
calibration. At every boundary, remove earlier-partition rows whose target reaches
the next partition. This purges overlapping future targets across all partitions.

Wind correction is selected only if validation vector RMSE improves and speed
MAE is no more than 2% worse. Gust correction requires improved validation MAE.
Selected predictions enforce nonnegative speeds and gusts at least as large as
the selected instantaneous speed. Models are not refitted on calibration or test
outcomes. The frozen configuration is evaluated once on the final test dates.

Metrics include speed/gust MAE, vector RMSE and circular direction MAE for the
whole 1–48-hour horizon and at 1/6/24/48 hours. Direction scoring excludes observed
winds below 3 kt and reports coverage for predictions with a direction. Raw
ICON-EU and one-hour-delayed observation persistence use matched rows. Current
mixed ICON-D2/EU fields remain available, but a historical mixed comparison is
explicitly unavailable until matched archived mixed snapshots exist.

RWY18 probabilities sample 256 **joint** u/v/gust residuals from calibration data
in model-lead bands 5–12, 13–24, 25–48 and 49–72 hours. A band requires at least
100 complete residuals spanning ten distinct issue dates. Resampling preserves
within-sample component/gust dependence; repeated draws do not create independent
weather events. Apply the challenge's 15 kt departure tailwind and >40 kt mean/gust
crosswind limits to each draw. The 10 kt landing and >30-minute persistence rules
remain in the separate versioned runway baseline.

The final test report includes Brier score, ten reliability bins, adverse sample
counts, unique adverse valid times/dates and unique tailwind/crosswind exceedances.
It also compares Brier score with an always-weather-usable baseline so class
imbalance cannot make an uninformative probability forecast appear skillful.
Probabilities are provisional, with a low-event-coverage status when either wind
limit has fewer than 20 distinct test valid times. Missing calibration/gusts
produce `null`; values of 0 or 1 describe the finite empirical sample and are
not guarantees. Forecast gust direction is approximated by mean direction;
evaluation uses observed maximum-gust direction when present. This approximation
is a limitation, especially near wind-limit thresholds.

## Live use, failures and operational labels

Live inference requests an explicit ICON-EU run. When provider metadata confirms
availability before the hourly reference, apply a ten-minute replication buffer
and record verified availability. Otherwise select a run under the same estimated
four-hour-delay policy and clearly flag it as unverified. Actual retrieval time
is always kept separately. Wind and uncertainty outputs remain distinct from raw
provider fields and the runway-rule baseline.

Manifests verify feature schema, artifact version, exact scikit-learn version and
artifact hash before loading trusted local models. Missing dependencies, artifacts,
unsupported versions, missing source hours or inference errors leave the baseline
available. Metrics reports are readable JSON even without ML dependencies.

Actual 07/25 direction probabilities remain `null` because independent historical
operations labels are absent. Existing label import remains supported. Neither
weather-rule labels nor public current-state snapshots are manufactured into
operating history. RWY18 weather probability never establishes official runway
availability. Hourly forecasts cannot resolve precise 30-minute changes.

Historical publication delays and retrospective DWD quality revisions prevent a
claim of verified leakage-free operational performance. The final score is
conditional on those documented assumptions and on the observed date coverage;
other seasons and rare extremes require more validation.
