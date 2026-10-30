# ML improvement and recovered 07/25 history

30 October 2026. User-authorized improvement work; model/version choices below are implementation decisions, not additional challenge requirements.

## What was delivered

- 182 days of DFLD history (30 April-29 October), 8,736 half-hour categories, and 4,259 conservative hourly point-label proxies. Raw source responses, hashes, retrieval times, and exclusions are retained locally. [Source and time-resolution audit](operations-label-research.md).
- `operations-v3`: a fixed 50/50 probability blend of the recent-observation balanced logistic classifier and a second balanced logistic classifier. The second adds runway-aligned forecast wind, recent wind/anomaly with a fixed six-hour decay, UTC hour cycles, and trailing three-/six-hour forecast-wind averages. All trailing inputs are forecast values from the same issue, never observed target weather. It retains raw forecast u/v, gust/missing flag, horizon, as-of initial OD when available, and one-hour-old DWD u/v plus preceding-hour maximum gust. The historical point labels cannot supply initial OD because their publication time is unknown.
- Training, live inference and replay share that recent-observation definition. Future/missing observations cannot silently become inputs; missing recent wind produces an explicit weather-rule fallback. JSON additions are documented in [backend-data.md](backend-data.md).
- Calibration now needs a purged forward check within its reserved partition. The actual check period had no eastbound cases, so sigmoid calibration was **not accepted**. Output remains `uncalibrated_model_probability`; certainty is a model score, not established calibration.
- Failed selection remains experimental and is not promoted into the displayed direction. Point labels cannot be scored as exact interval switch times.

## Measured results

Validation: 3,199 matched cases. Accuracy **92.53% -> 95.75%**, balanced accuracy **92.60% -> 93.43%**, Brier **0.07471 -> 0.03872**. An earlier, purged check within training gives **89.39% -> 93.84% accuracy**, balanced accuracy **89.46% -> 93.82%**, Brier **0.10611 -> 0.04897**. Selection requires no worse overall accuracy/class balance and lower Brier on both splits, plus no worse 1/6/24-hour accuracy on selection. Among eligible candidates, rank the worst-split overall accuracy gain. No test score enters selection.

The later September 21-October 26 issue period has been inspected during development. These are **exploratory retrospective results**, not a new untouched holdout. The same stable-source-label cases are used for model and Section 3 rule baseline; transitions excluded by the label rule are not scored as successes.

| Lead | Cases | Rule accuracy | Previous ML | New ML accuracy | Rule Brier | New ML Brier |
| --- | --- | --- | --- | --- | --- | --- |
| 1 h | 135 | 71.9% | 77.8% | 78.5% | 0.2815 | 0.1884 |
| 6 h | 134 | 78.4% | 76.1% | 77.6% | 0.2164 | 0.1853 |
| 24 h | 134 | 76.1% | 74.6% | 76.1% | 0.2388 | 0.1933 |

Across 1-48 hours: **74.72% -> 77.60% accuracy**, **74.79% -> 77.85% balanced accuracy**, **0.25277 -> 0.18763 Brier** on 6,500 forecast cases (854 distinct target timestamps). Brier improves by 25.8%. One-hour classification wins; 24-hour accuracy ties the rules. Six-hour classification is one correct prediction behind: 104/134 versus 105/134. The earlier v2 model had 76.34% overall accuracy; v3 adds 82 correct forecast cases across all horizons. Every required-horizon ML accuracy improves over v2, but all required rule benchmarks are not beaten.

The latest report is `data/operations-evaluation.json` (`/api/operations-metrics`). Initial-OD persistence has zero eligible historical cases: target retrieval time was not backdated into an as-of feature. Exact next-change metrics are unavailable because the source points do not establish exact transition intervals.

RWY18 remains unchanged: empirical probability loses to the always-usable and Section 3 references, with one distinct adverse test timestamp. The 1-48-hour training subset contains only two distinct adverse hours. This work does not establish rare-event calibration or official RWY18 status.

## Accuracy follow-up experiment

The bounded follow-up compared current/decayed logistic and small boosting candidates, then balanced boosting and forecast-history variants on training/selection only. None of the single new learners passed both overall class-balance gates. A fixed equal blend passed and was frozen at `2026-10-30T14:08:15Z` before its later-period evaluation. Reports are `data/experiments/od-accuracy-selection.json`, `od-trajectory-selection.json`, `od-equal-blend-selection.json`, and `od-accuracy-frozen*.json`; the frozen model hash is recorded. The production implementation reproduces the frozen predictions and test metrics. No further candidate search followed that test result.

## Wind experiment

A validation-only experiment added recent DWD observations to the existing Ridge wind correction. Raw recent features gave vector RMSE 4.3747 versus existing 4.3768 kt, with worse gust error. A fixed six-hour decay variant reached 4.3640 kt overall and 3.6351 versus 3.7806 kt at one hour. These are small development-period gains without demonstrated runway benefit; neither variant replaces the existing wind artifact. Reports are `data/experiments/recent-observation-selection.json` and `operations-recent-selection.json`; no final-test wind search was performed.

## Reproduce and use

```bash
python -m fra_forecast fetch-operations
python -m fra_forecast train-operations --labels data/operations/labels.csv
python -m fra_forecast refresh --live-only --no-departures
python -m fra_forecast refresh-comparison --no-gfs
```

Model experiment `277d8d037ca31002de2e`. Original weather dataset hash `66fe17ae25c62ea2fda4031a678e4bfe379f27a268ea98dc4dfd56098aa2de1b`; label hash `2a8645e6c594156d05efebe1d7861e61f0c1709b9a0c43497bd554cdae5cbc7f`. Fixed weather partitions are retained (train through Aug 15, selection Aug 16-Sep 2, calibration Sep 3-20, test Sep 21-Oct 26), with overlapping targets purged. Labels were retrieved on Oct 30; the artifact evidence cutoff is `2026-10-30T13:39:14Z`. Its first eligible whole-hour reference is **14:00 UTC / 15:00 Berlin**. Historical replay before that cutoff correctly excludes this new artifact rather than pretending it existed then.

## Remaining limits

Verification: all 122 backend tests passed, including local HTTP handlers, history parsing/DST handling, point-label lookup, future-availability rejection, trailing-window causality/gap handling, training/live feature parity and failed-model export fallback. Cached historical and live-input feature construction matched on sampled issue times. The model card was rendered and checked as one page. Source/dataset hashes match the saved model report. UI verification was not part of this backend work.

Live verification at reference `2026-10-30T14:00:00Z`: refreshed public inputs produced 48/48 available v3 OD probabilities, all finite, summing to one, and carrying the provisional-label/uncalibrated-score flags. The comparison snapshot was refreshed to the same issue. A local smoke export at `output/operations-live-check-v3/` contains 48 CSV/JSON rows and reports `complete_with_availability_assumptions`; this issue is not an organizer-supplied jury date. The deployment packaging allowlist now includes the v3 OD artifact and metrics, while continuing to exclude source history. The local API was restarted on port 8000 and its forecast/metrics routes verified. No deployment was performed in this ML task.

The DFLD extract is an observed-direction source but the derived point labels remain provisional: exact sampling time is unverified, stable-bin filtering favors easier cases, DST-change day is excluded, and switches inside a displayed half hour are unresolved. Predictions of next change are hourly class-sequence windows, not calibrated event-time probabilities. Model/observation historical publication delays and DWD retrospective corrections remain assumptions. New untouched dates and verified switch intervals are required for a stronger claim.

No new provider or dependency was added. UI work was left to the teammate; unrelated concurrent work was preserved. Source history stays local; public redistribution permission is not established. The older local delivery ZIP predates this extension. Jury dates/schema are still not supplied in the brief.
