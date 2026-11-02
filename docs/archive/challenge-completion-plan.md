**FraAlliance required-deliverables implementation plan**

Prepared 30 October 2026. Planning only: this document does not implement the steps below. The user confirmed **three hours remain in the total six-hour hackathon**, and **the PDF is the only organizer material supplied**. Subtract planning and coordination time from that remaining budget; do not start a fresh three-hour clock when coding begins.

The [challenge text and diagram notes](../challenge/README.md) and [original PDF](../challenge/AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf) define the requirements. This document gives the executable order for the required work in the [broader comparison/coordinator plan](model-comparison-implementation-plan.md). Its implementation choices, metrics, timeboxes, and proposed output schema are our choices, not additional wording from the PDF. Comparison, additional providers, and the [chatbot](chatbot-plan.md) remain requested extensions with no new time allocation until the required work is packaged.

**Current position and dependencies**

| Requirement | Evidence at planning time | Completion work |
| --- | --- | --- |
| 48 hourly forecasts | Existing pipeline and saved forecast have 48 hours | Retain the grid in live inference and replay |
| RWY18 usability probability | Existing empirical weather probabilities populate 48 hours | Retain them; compare against the actual Section 3 weather baseline and disclose sparse adverse events |
| Airport-wide 07/25 and certainty | Saved forecast lacks learned OD; a new, uncommitted `operations_ml.py` draft now exists | Validate its data, training, inference, CLI/API integration, and outcomes; do not create a second classifier |
| Next probable change | Rule windows exist; current `next_change()` edit addresses unknown-to-known alerts | Verify the fix, connect the learned hourly sequence, and evaluate change timing |
| Unseen evaluation at 1/6/24 h; beat Section 3 | Weather evaluation exists; wind corrections lost validation; no operational skill is established | Score actual OD, probability quality, and changes on matched cases; state whether improvement is established |
| Self-sourced data and citations | Cached ICON/DWD data, source logs, current operations snapshots | Obtain independent historical OD outcomes and preserve source/time semantics |
| One-page model card | Evaluation/source notes exist | Produce one rendered page with sources, quality, drivers, limitations, and version identifiers |
| Jury-day forecasts and repository | Repository and live JSON exist; no jury dates, issue times, or format supplied | Build replay/export, verify a demonstration export, and generate actual jury files only when their inputs exist |

The prior audit passed 43 tests, but additional source edits are now in progress. That result is not validation of those newer edits. Re-read current files before editing. In particular, `pipeline.py`, `ml_live.py`, `sources.py`, `wind_ml.py`, and `operations_ml.py` already contain related work. `comparison.py` and a `submission.py` replay/export draft also appeared during planning; the latter was inspected and must be reused. Preserve this work and avoid duplicate implementations. The saved evaluation still describes the earlier trained artifact, not these code changes.

**Time allocation and execution order**

These are effort caps for the next implementation session, not promises that external data will arrive. Core work totals 160 minutes; the remaining 20 minutes absorbs planning, coordination, and failures. Recalculate actual time at the start and protect the model-card/integration allocation. Do not extend the deadline to finish optional features.

| Step | Cap | Deliverable | Dependency / stop condition |
| --- | ---: | --- | --- |
| 1. Verify labels and reconcile existing edits | 20 min | Real label source/coverage report or explicit unavailable result; agreed jury-input checklist | Stop discovery at the cap; no speculative full backfill |
| 2. Finish the OD model and live integration | 30 min | One trained/evaluated model with OD/certainty outputs, if supported | Requires sufficient independent labels; code-only checks do not complete the model |
| 3. Complete next-change handling | 15 min | Verified unknown-state fix and model-derived hourly change window | Learned change output requires step 2; baseline fix does not |
| 4. Complete target evaluation | 30 min | 1/6/24 h comparison report with matched coverage and improvement status | Actual OD scoring requires labels; weather scoring can proceed independently |
| 5. Replay and export | 30 min | Deterministic 48-hour export and validation report | Official jury exports require their dates/issue times/schema |
| 6. Model card | 20 min | One-page PDF plus editable source | Uses real results, including explicit missing results |
| 7. Integration and handoff | 15 min | Focused checks, one smoke run, stable JSON handoff, submission instructions | No new feature work during this allocation |

If step 1 fails, complete useful label validation and explicit unavailable behavior, then spend the released model time on steps 3–7. Keep learned OD, actual-OD evaluation, and baseline improvement marked incomplete. A weather-only package is a fallback submission, not full PDF compliance. If a verified label source arrives later, resume at step 2 only if the remaining clock permits it.

**1. Establish usable operations labels**

Reuse `dataset.load_labels()`, `label_at()`, and [the existing CSV schema](../../examples/operations-labels.csv). The [bounded source research](../operations-label-research.md) found no verified ready-to-import historical dataset. Its best lead is DFLD's documented Fraport-based actual-direction series, distinct from the wind display. Inspect the actual-direction data on two or three dates overlapping the cached ICON period before committing to collection. Do not build an image/OCR reconstruction or a new ADS-B ingestion system.

Acceptance requires observed 07/25 semantics, timezone-aware timestamps, explicit gaps, provenance, sufficient overlap with the cached weather dates, and usable source conditions. Record label intervals, distinct issue/target dates, both-class counts, and distinct switch events. Reuse the existing chronological splitter's minimum date/partition checks; repeated forecasts of the same outcome do not create independent events. Collection and normalization must fit the timebox; a plausible web page alone does not pass the gate.

Historical outcomes can be used as targets without pretending they were known at issue time. Only verified as-of state can be an initial-OD feature. If historical publication time is unknown, retain that uncertainty and actual retrieval time; never set `available_at = valid_from` merely to make a feature available. Do not extend an hourly category across unobserved intervals or assume an exact transition minute. If the existing interval CSV cannot honestly express a source's resolution, reject that conversion for this increment rather than fabricate precision. Current UNH snapshots and departure schedules cannot manufacture months of historical outcomes.

Required organizer clarifications, still unresolved: jury dates, forecast issue times/timezone, file format, scoring metric, hourly target convention during a switch, and whether RWY18 means wind suitability or official operational availability. Prepare that short checklist for the user; do not assume the organizers will supply training data or send messages without authorization. Use the internal schema in step 5 while the official schema is unknown.

**2. Finish one small learned OD model**

Inspect and reuse the current `operations_ml.py` draft. The first candidate is the existing fixed logistic-regression approach using the installed scikit-learn dependency, `domain.prediction_features()`, and a separate `operations-logistic-v1` artifact. Inputs are archived forecast wind u/v, gust plus missing indicator, initial OD if known by issue time, and lead time. Do not add another model family or a tuning sweep within this budget. Standardization and any preprocessing fit only on training dates.

Join labels to the cached `data/ml/dataset.json`; do not repeat the 180-day weather download. Keep chronological train, selection, calibration, and test dates with purged target overlap. Fit only when training has both classes and the existing date/partition guards pass. For calibration, reuse the draft's separate sigmoid fit only where its independent partition has sufficient class/date coverage. Otherwise expose the raw model probability as uncalibrated. These guards are safeguards, not proof of calibration. Source/date counts must accompany row counts.

Return one airport-wide class and `p_od07`, `p_od25`, `certainty_score = max(p_od07, p_od25)`, model identity, and probability status. The certainty score is an explicit implementation definition; the PDF does not define it. Validate finite bounded probabilities summing to one. Poorly validated scores remain visibly provisional. The official [logistic-regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression) and [calibration](https://scikit-learn.org/stable/modules/calibration.html) documentation describe the chosen methods; probability output alone does not establish reliability.

Finish `train-operations --labels ...`, inference, and the read-only metrics route if they are not already connected. Freeze the model/calibration policy before scoring test outcomes. Record the selection comparison against the rules and persistence, then report the frozen candidate's final test honestly. A losing model may be shown as an experimental result; do not claim a win or replace a validated fallback simply because training succeeded.

For live inputs, use the exact eligible ICON-EU run and the same feature construction as training. The shared reference remains the existing `forecast_reference_time`. Select a stored operations snapshot with `available_at <= reference`, or mark initial state unknown. A current scrape retrieved after the reference cannot be backdated using its `since` text. Missing/corrupt models or missing wind produce explicit unavailable outputs while preserving the baseline and existing RWY18 probabilities.

**3. Finish change-time prediction**

The unknown-to-known normalization is already edited in `pipeline.next_change()`; validate it rather than reapply it. Trace both callers: baseline OD and RWY18 weather change. Add small checks for unknown initial state, no change, a real change, and a missing-data gap. Refresh the sample artifact during integration so an old false alert is not left in the demo.

For learned OD, reuse the draft's first class change in the ordered 48-hour sequence. For a first-hour change from a known initial OD, bracket it between reference time and the first target. Otherwise use adjacent known hourly timestamps, explicitly widening/flagging gaps. With unknown initial OD, the first available class is not itself a switch. Distinguish `change_expected`, `no_change_within_horizon`, and `unknown`.

Use `method: predicted_hourly_class_change`; leave event probability null because marginal hourly class probabilities do not define the probability of any switch in an interval. This is a model-derived point/window estimate, not a calibrated event-time distribution. Hourly data cannot establish exact minute timing. Do not change the PDF's >30-minute persistence rule to conceal that limitation.

**4. Evaluate the required targets, not just wind**

Use the same issue/valid timestamps, forecast availability assumptions, and eligible inputs for all candidates. Run the rule baseline through the complete available forecast timeline before filtering to labeled/scored hours; missing target labels must not remove weather steps and change persistence behavior. Apply the Section 3 thresholds unchanged. Missing actual OD is not permission to use rule-generated OD as truth.

| Target | Minimum comparison/report |
| --- | --- |
| Actual OD at 1/6/24 h | Accuracy, balanced accuracy when both classes occur, per-class counts, Brier score, and reliability bins for the learned probabilities; same cases for Section 3 and the available-state persistence benchmark |
| RWY18 weather at 1/6/24 h | Existing empirical probability Brier/reliability versus Section 3 applied to the exact raw forecast, always-usable, and observation persistence where available; missed adverse events and false warnings at a fixed 0.5 usability threshold |
| Next OD change | First-change detection, false/missed changes, signed and absolute timing error for both model and rule baseline; score each issue's full covered 48-hour interval, with 1/6/24 h window summaries where supported |

For change truth, use independent label interval boundaries rather than the first sampled future hour with another class. Do not count incomplete coverage as no-change truth, score a later event as a successful match to an earlier missed event, or silently overlook within-hour reversals when interval labels resolve them. State a fixed matching rule before scoring: compare the first predicted and actual switch in each covered issue horizon; report unmatched events and bracket hit rate separately from endpoint timing error. Unknown starting state/partial truth produces an exclusion with a count, not a success.

Report common-case and missing-coverage counts for each comparison. Persistence needs its own matched cohort if initial state is unavailable. Deduplicate valid times/events for coverage reporting; overlapping forecast runs are not independent adverse events. The existing RWY18 result has only one distinct adverse timestamp and cannot support a reliable rare-event claim. Preserve that finding; do not tune against it or relabel official availability from weather/flight absence.

Separate validation model choice from final scoring. Use selection-partition Brier score as the proposed OD primary selection metric, with balanced accuracy no worse than the rules as a classification guard. Record the uncalibrated candidate's selection decision, then fit the predefined sigmoid calibration on its separate partition when coverage permits, without retuning. Score the resulting frozen pipeline once on test; preserve both the selection and final probability status. Report every required horizon rather than hiding losses inside an overall average. Any reused previously inspected test period remains `exploratory_reused_test`. Do not promise statistically established improvement or fabricate an untouched test period. Availability remains conditional until publication history is verified; retrospective data corrections and assumed delays stay in the report.

**5. Export forecasts reproducibly**

Complete the existing `submission.py` draft and connect `export-submission --issues path/to/issues.csv --output-dir ...`, sharing prediction logic with the live path. Reuse current forecast parsing, explicit runs, artifact loaders, and `write_json()`. The required export must work with the existing wind artifact without depending on completion of the optional comparison extension; keep the selected model identity and probability status consistent with live inference, including low-event-coverage warnings. Do not make historical replay call live refresh or read today's operations state. Retain the draft's input column `forecast_reference_time` for explicit timezone-aware issue times; initially require whole-hour UTC times to match the existing model/evaluation grid. Reject other times with an explanation until an organizer convention is supplied.

For every issue produce exactly 48 unique hourly targets, issue+1 through issue+48. The internal CSV contains `forecast_reference_time`, `valid_time`, `lead_time_hours`, `operating_direction`, `p_od07`, `p_od25`, `certainty_score`, `od_status`, `p_rwy18_weather_usable`, `rwy18_probability_status`, `next_change_earliest`, `next_change_latest`, and `next_change_status`. JSON sidecars retain change method, model/ruleset identity, source URLs, run/availability metadata, assumptions, and artifact/data hashes. Repeat the issue-level next-change summary consistently in CSV rows. This internal format is not represented as an organizer requirement.

Select only weather/state inputs available as of each issue. Training, selection, and calibration information used by the artifact must precede that issue, with availability assumptions explicit. Today's model must not be silently used for a date inside its training/calibration window. If needed, fit an eligible pre-issue artifact from cached data with frozen settings, within the budget; otherwise mark the export incomplete. Record actual training/export time separately from the simulated historical issue time, and label retrospective reconstruction as such. Strict verified-as-of exports cannot be claimed when historical publication times are only assumed.

Write into a separate output directory and preserve existing data/models. Validate row count, uniqueness, timezone/grid, probability bounds, required statuses, source availability, and artifact cutoffs before declaring readiness. Missing evidence produces nulls and an `incomplete` report, not omitted hours or a fabricated value. A demonstration export for an explicitly labeled internal issue time proves plumbing only. Official jury forecasts remain pending until actual jury inputs are supplied; no guessed dates.

**6. Prepare the one-page model card and submission instructions**

Create `docs/model-card.md` and a rendered `output/pdf/model-card.pdf`, reusing the existing source and evaluation notes. Include targets and their distinction from official status; source links and dates; input drivers; training/selection/calibration/test periods; 1/6/24 h target metrics alongside baselines; unique event counts; model/ruleset identity; availability/calibration limitations; and what remains missing. Use meaningful input coefficients/contributions only if calculated correctly; otherwise list actual inputs and physical drivers without invented importance rankings.

Render-check that the PDF is exactly one readable page. The README handoff gives installation, training/inference/export commands, artifact location, and known incomplete items. `data/` is ignored by Git: explicitly package the frozen compatible artifact and permitted forecast/metrics files, or provide exact reproducible retrieval/training instructions plus hashes. Do not assume a clean clone contains local models, data, or jury exports. Preserve source attribution and reuse conditions; do not put credentials in the package.

**Files, callers, and compatibility**

| Area | Existing files / intended changes | Checks and affected consumers |
| --- | --- | --- |
| Labels and OD | `dataset.py`, draft `operations_ml.py`; reuse `domain.py` features | CLI training, live enrichment, replay; missing/future labels, classes, temporal splits |
| Baseline/change | Existing edit in `pipeline.py` | Both next-change summaries and any replay caller; unknown/gap/first-hour cases |
| Artifacts/probabilities | In-flight helpers in `wind_ml.py`, `ml_live.py` | Existing wind models/departure probability consumers must continue to load and behave as documented |
| CLI/API | `cli.py`, `server.py`, `pipeline.refresh()` | `train-operations`, `export-submission`, `GET /api/operations-metrics`; existing routes preserved |
| Replay | Existing draft `submission.py` | As-of selection, 48-hour shape, missing rows, cutoff enforcement, strict JSON/CSV |
| Tests | Existing baseline/wind/departure tests; small operations/submission tests if absent | Numerical limits, leakage boundaries, matched scoring, required fields; synthetic fixtures never become accuracy evidence |
| Documentation/package | `backend-data.md`, `README.md`, model card and output files | Teammate receives real sample JSON and exact field semantics; no UI implementation |

Use the additive contract already drafted: per-hour `forecast[].operations_ml` contains learned OD/certainty; `operations_model.next_change` contains its change summary. Existing `forecast[].operating_direction` and top-level change remain the rule baseline, and `forecast[].ml.p_rwy18_weather_usable` retains the existing weather probability. Baseline `p_*` values stay null. Do not duplicate learned probabilities into several blocks with conflicting model identity. Document the additive schema revision and fix stale version references in the current API documentation. RWY18 departure assessments keep their existing meaning.

**7. Completion checks and final handoff**

Run the existing focused test suite plus the small new cases warranted above after implementation. Test corruption/unavailable-artifact fallback, future inputs rejected, preprocessing isolated from later targets, inference/replay using the same features, full-timeline baseline scoring, unknown-versus-no-change, exactly 48 export rows, and unchanged departure semantics. One bounded end-to-end run and GET requests to forecast/metrics routes are sufficient after those checks pass; do not spend the remaining budget repeatedly backfilling or broadening tests.

Final status must distinguish: software implemented/tested; trained with real labels; empirically improved/not improved/inconclusive; provisional probabilities; and jury submission generated/pending inputs. The PDF's baseline-beating objective cannot be guaranteed by a plan. Null OD probabilities, a code-only classifier, and a successful synthetic replay do not complete the actual forecasting/evaluation deliverables.

The teammate owns UI. Supply the stable JSON and one real example; reserve optional historical replay visualization, wind-margin explanations, departure-window counts, provider comparisons, and AI explanations for time demonstrably left after required packaging. No new infrastructure, dependencies, UI, broad provider backfill, or autonomous retraining is included in this three-hour plan.
