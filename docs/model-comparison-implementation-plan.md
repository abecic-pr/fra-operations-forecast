**Implementation plan: data discovery, forecast comparison, selection, and an AI coordinator**

Prepared 30 October 2026; originally audited against the PDF, code, artifacts, and 43 passing offline tests. The [challenge brief](challenge/README.md) and its unchanged PDF are authoritative. This document does not authorize changing the teammate's UI.

**Implementation update, 30 October:** The comparison/discovery/coordinator backend, additive OD training/inference/evaluation path, unknown-state change fix, replay/export, and one-page model card are implemented. The live comparison has 48 hours, GFS's four bounded probes succeeded, and validation selected Ridge. See the [runbook and measured results](model-comparison.md) and [model card](model-card.md). Actual OD training/accuracy remain blocked on independent historical labels; the optional agent's real API execution needs configuration; official jury files need dates/issue times/schema absent from the PDF. The table below is the original audit baseline, not the current completion state. Code-only OD and provisional weather probabilities do not establish full challenge completion or baseline-beating operational skill.

**0. PDF and code audit: what exists and what remains**

**Later ML/history update:** The earlier label blocker is partly resolved: DFLD yielded 182 days of actual-direction displays and 4,259 provisional stable-state point proxies. `operations-v2` now trains and evaluates a recent-observation classifier. Probability scores improve at 1/6/24 hours on the inspected later period; 6/24-hour classification does not. Exact switch labels, a fresh holdout and RWY18 event coverage remain gaps. The [current ML report](ml-improvement.md) supersedes the earlier implementation-status sentence above; this audit table remains historical.

| PDF requirement (page 1) | Verified current implementation | Remaining work |
| --- | --- | --- |
| Hourly forecasts through 48 h, section 4.1 | Implemented by `pipeline.live_snapshot()` and `ml_live.enrich()`; the inspected saved snapshot has 48 hours | Preserve alignment and provenance; reuse this output grid |
| RWY18 usability probability, section 4.1 | Implemented in `wind_ml.probabilities()` and `ml_live.enrich()`; all 48 saved `forecast[].ml.p_rwy18_weather_usable` values are populated | Preserve and report these provisional estimates; calibrate/evaluate any different selected forecast using its own residuals |
| OD 07/25 with certainty, section 4.1 | `DirectionState` supplies a rule-based direction; `p_od07` and `p_od25` are explicitly null, including in ML output | Independent historical OD labels, a learned OD predictor, and an explicitly defined certainty score are missing |
| Next probable change time, section 4.1 | `pipeline.next_change()` already returns rule-based windows/statuses | Add a learned-forecast change estimate and evaluate timing; fix unknown-to-known transitions being reported as changes |
| Section 3 rules as the baseline to beat, section 4.1 | Thresholds and persistence are implemented/tested in `domain.py`; existing wind corrections were rejected on validation | No improvement over the required operational baseline is established. Wind RMSE improvement alone cannot establish it |
| Self-sourced data and citations, section 4.2 | Source readers, raw response metadata, cached data, and source research documents exist | Reuse them; collect usable independent historical OD labels and carry source citations into the model card/export |
| Unseen evaluation at 1/6/24 h using forecast-time data, section 4.3 | `wind_ml.evaluate()` and saved metrics cover 1/6/24/48 h, chronological partitions, overlap purging, wind errors, and RWY18 Brier/reliability | Actual OD and change-timing evaluation is absent; historical availability assumptions still prevent a verified leakage-free claim |
| Code repository, section 4.4 | Already present with CLI, API, and tests | Include reproducible submission instructions and model/data identities |
| One-page model card with sources, quality, and drivers, section 4.4 | ML guide and evaluation notes exist | No dedicated one-page model card found; distill existing evidence rather than redo it |
| Forecasts for jury test days compared to actual flown OD, section 4.4 | Live JSON exists | No jury-day replay/export command found. Jury dates, issue times, schema, and scoring details are not specified in the brief |

Evidence inspected: saved forecast generated `2026-10-30T12:10:18Z`, metrics trained `2026-10-30T11:51:16Z`, and the current Python modules/CLI. These are saved-artifact checks, not a fresh provider test. The RWY18 probability status is `provisional_low_event_coverage`: only one distinct adverse test valid time; the always-usable forecast has a slightly better Brier score. The original plan missed required completion tasks, but it would also have duplicated probability generation and horizon evaluation that already exist.

**1. Outcome and scope**

Deliver the challenge's 48-hour forecast of RWY18 usability probability, airport-wide OD with certainty, and next probable OD change, with the required evaluation and submission package. The user's comparison extension shows several candidates, identifies disagreements, selects a forecast or fixed blend using saved validation results, and lets an AI agent explain and run that workflow.

Data discovery covers both source coverage and patterns in forecast errors. Start with the cached dataset and existing models. Add one new correction model and one additional weather-model source. Use local files, the existing Python CLI/API, the standard library, and the existing optional scikit-learn dependency.

The six-hour limit applies to the whole project, including work already completed. Required forecast/evaluation/submission gaps take priority over extra providers and the AI coordinator. A raw-forecast winner is an honest experimental result, but does not satisfy the brief's objective to beat the section 3 baseline. Report an unsuccessful or incomplete challenge outcome accurately rather than invent improvement.

**2. Current capabilities and constraints**

| Existing capability | Reuse and implication |
| --- | --- |
| `sources.py`: cached downloads, DWD/METAR, parameterized weather-model reader | Reuse fetching, parsing, provenance, units, retry limits, and atomic JSON writes. |
| `ml_data.py`: ICON-EU/DWD dataset and exact time joins | Use the existing cached rows first. Do not trigger another 180-day backfill. |
| `wind_ml.py`: feature construction, chronological partitions, corrections, metrics | Reuse these functions; make only the small extraction needed to reuse training. |
| Three gradient boosting regressors for u/v/gust | These constitute one correction approach, not three independent forecasts. |
| Raw ICON-EU and observation persistence evaluation | Include as reference forecasts in the comparison. |
| `ml_live.py`: explicit-run selection and validated artifact loading | Preserve its existing behavior; reuse compatible time/provenance helpers. |
| `/api/forecast`, `/api/model-metrics`, and departure assessments | Existing contracts and artifact directories remain valid. |
| Recorded evaluation rejected wind and gust corrections | Display the experimental corrections separately from the deployed raw fallback. |

Independent historical 07/25 operations labels are still missing. Flight-board schedules do not provide those labels or confirmed runway assignments. Weather suitability, observed runway use, and official status remain separate. The recorded RWY18 probability evaluation has very few adverse events and does not establish reliable extreme-event probabilities.

**3. Candidate forecasts and data sources**

| Candidate ID | Implementation | Selection role |
| --- | --- | --- |
| `raw_icon_eu` | Exact source forecast from the eligible explicit run | Default and fallback |
| `persistence` | Repeat the latest observation available at the decision time | Benchmark only in version 1 |
| `boosting_correction` | Existing u/v/gust residual regressors, with candidate corrections enabled | Eligible after validation |
| `linear_correction` | Fixed Ridge residual regression for u/v/gust | New eligible candidate |
| `equal_blend` | One-third each of raw ICON-EU, linear correction, and boosting correction | New eligible candidate |
| `raw_gfs` | One explicitly identified GFS Global run through Open-Meteo | Additional source; comparison only until matched historical evaluation exists |

For the linear model, use the current feature list, train-only median imputation and scaling, and fixed `Ridge(alpha=1.0)`. Preserve the explicit missing-gust indicator. Exclude missing targets separately for each output, using the existing minimum-training-data checks. Do not tune alpha or add features in this version.

Blend u/v components, then derive speed and circular direction. Blend gusts only when every constituent has a gust. Never average direction angles, fill absent gusts with zero, or silently redistribute weights around a missing constituent. Apply the existing physical bounds to corrected/blended outputs. Keep raw source values intact for inspection.

The mixed ICON-D2/EU baseline can remain visible as context, but it is not a ranked historical candidate until matching archived snapshots exist. TAF remains context; parsing all TAF change/probability groups is outside this increment. Label shared inputs/model families so algorithm diversity is not presented as independent weather evidence.

**4. Runnable increments**

First address the required challenge track below. Reuse existing features rather than rebuilding them. Then run the comparison/agent increments as remaining time permits.

| Required step | Concrete work | Completion evidence |
| --- | --- | --- |
| R0. Establish labels and jury inputs | Audit accessible public OD history; reuse `load_labels()`/`label_at()` and the CSV contract. Obtain jury dates, issue times, target meaning, and required file format from organizers | Real label coverage/source report and explicit unresolved jury fields; no expectation of a provided training dataset |
| R1. Complete target outputs | Preserve existing RWY18 probabilities; implement a minimal learned OD model only with independent labels; define certainty and derive its next-change window | Required fields populated with genuine model outputs where supported; unavailable outputs explicitly marked incomplete |
| R2. Target-level evaluation | Reuse chronological split/metrics infrastructure; compare actual OD, RWY18 weather outcomes, and change timing against section 3 and persistence | 1/6/24 h results on matched cases, class/event counts, calibration status, availability assumptions, and an explicit improvement/not-improved result |
| R3. Submission | Add a one-page model card and deterministic jury-day replay/export | Repository instructions, sourced model card, and validated 48-hour exports for each supplied issue time |

Timebox label discovery before committing to a classifier. If labels cannot be obtained, record R1/R2's OD dependency as unresolved and continue useful weather and submission work; the challenge remains incomplete. Do not postpone the search for labels to after the demo. No reliable estimate for R0-R3 is possible until label access and jury inputs are known.

The following A-G estimates apply only to the original comparison/agent extension, not the full challenge completion effort:

| Step | Target time | Runnable result | Acceptance check |
| --- | --- | --- | --- |
| A. Existing-candidate comparison | 25 min | `compare-models` produces raw, persistence, and experimental boosting scores | Matched-row scores reproduce existing helper calculations; rejected corrections remain visible |
| B. Discovery report | 20 min | `discover-data` summarizes existing sources, coverage, and development-period error patterns | Missing data, unique dates/events, and source identity are explicit |
| C. Linear model, blend, and selection | 40 min | Five candidates, a frozen selection policy, and separately stored artifacts | A deliberately worse candidate loses; changing test outcomes cannot change the policy |
| D. Live comparison and JSON API | 35 min | `refresh-comparison` writes 48 hourly comparisons; GET routes expose reports | Exact common target times, explicit missing values, legacy outputs unaffected |
| E. One additional source | 25 min | GFS live comparison and a small archived-run coverage probe | Source-specific availability assumptions and unranked status are explicit |
| F. AI coordinator | 40 min | `forecast-agent` runs bounded tools and returns an evidence-linked explanation | Tool decisions match the deterministic policy; failure preserves the numerical result |
| G. Integration and demo | 20 min | Documented command sequence, focused checks, teammate handoff | End-to-end run and missing-source/agent fallback demonstration |

These extension estimates total about 3 hours 25 minutes and exclude R0-R3. They must not be presented as a total project estimate. Reserve submission/integration time first; then choose the next runnable extension within the remaining six-hour budget. Extra providers and the agent may be deferred, but remain part of the user's requested roadmap. No long backfill should block the demonstration.

**5. Offline comparison and discovery details**

Use `data/ml/dataset.json`, the existing preparation/source reports, and the existing observation targets. Give every experiment a stable ID derived from the dataset hash, candidate settings, and split definition. Record package versions, training dates, artifact hashes, candidate IDs, and the exact cohort definitions.

Reuse the existing train / selection / calibration / test partitions, including removal of targets that overlap the next partition. Load existing boosting estimators only when dataset, feature schema, split, parameters, and dependency metadata match. Otherwise fit the same fixed configuration into the new comparison directory; do not overwrite the existing deployed artifact.

Compare candidates on common `(decision_time, valid_time)` pairs. Maintain separate matched wind and gust cohorts, since missing gusts need not invalidate wind. Report candidate coverage alongside scores so a model cannot win by omitting difficult hours. Include a raw-versus-persistence comparison on their own matched subset; keep subset scores clearly separate from the full candidate cohort.

Report speed MAE, vector RMSE, gust MAE, circular direction error, and counts at 1, 6, 24, and 48 hours plus the full horizon. Keep the existing calm-direction exclusions. Include unique valid times and issue dates, not just repeated forecast-row counts. Derive RWY18 threshold misses and false alarms from observed weather, with adverse-event counts; do not call these actual runway-status errors.

These wind metrics are diagnostics, not the complete challenge evaluation. For independently observed OD, report accuracy, balanced accuracy, Brier score and reliability for class probabilities, and next-change timing error plus missed/false changes. For RWY18 report Brier score, reliability, adverse-condition recall/false alarms, and distinct adverse times/dates. Compare with the section 3 baseline on the same source forecasts and target cases, OD persistence, and the existing always-usable RWY18 reference. Deterministic labels may be represented as 0/1 solely to calculate a scoring baseline; do not publish them as calibrated probabilities. Report 1/6/24 h separately, with 48 h optional. The brief does not specify the jury metric, so these are our explicit evaluation choices pending organizer clarification.

Discovery produces a compact report covering:

- Source/product identity, model family, station/coordinates, units, retrieval and availability times, temporal resolution, date coverage, and missing-field rates.
- Errors by forecast lead band, forecast wind sector, and proximity to challenge thresholds. Use only development dates for choosing experiments. Mark outcome-based diagnostic groups as retrospective, not deployable routing inputs.
- Paired residual correlation and examples of disagreements, showing whether models make similar mistakes. Suppress numerical group summaries with fewer than 30 matched rows or five issue dates, while retaining coverage counts. These are demo reporting cutoffs, not statistical significance tests.
- A source status of `usable`, `partial`, `unavailable`, or `not_evaluated`, with reasons. Count models and observations by underlying origin rather than API count.

The existing test period has already been inspected. Freeze each new experiment before running it there, label that result `exploratory_reused_test`, and never tune against it. Reserve genuinely unseen dates or future collected observations before claiming confirmed improvement. Historical publication delays and retrospective observation corrections remain disclosed assumptions.

**5a. Minimal missing OD model, conditional on real labels**

Add one simple logistic-regression classifier before considering a larger OD model. Reuse `domain.prediction_features()` and existing label interval validation. Join future OD labels only as targets; initial OD must satisfy `label_at(..., known_by=decision_time)`. Inputs are the forecast wind/components, gust/missing indicator, as-of initial OD, and horizon. Never use rule-generated OD as actual-use training truth. Fit preprocessing only on the training partition, keep selection/calibration/test dates separate, and require both OD classes for model fitting. Insufficient class/date coverage produces an explicit unavailable status.

Store this classifier separately from the wind-correction artifact. Its output is `operating_direction`, `p_od07`, `p_od25`, and `certainty_score = max(p_od07, p_od25)`, with `certainty_basis` and calibration status. Validate probabilities and their sum. Evaluate probability reliability on held-out dates; apply a calibration fit only on the dedicated calibration partition where coverage supports it. An uncalibrated model score must be labeled accordingly, not described as verified confidence. Do not require a second OD learner, tuning sweep, or a learned router for the first increment.

Derive the next predicted OD switch from the frozen model's hourly class sequence and the known initial OD. Reuse the window/status shape from `next_change()`, mark `method: predicted_hourly_class_change`, and report an hourly bracket, not a minute-exact time. This is a heuristic next-change estimate, not a calibrated event-time distribution; do not multiply independent per-hour probabilities to invent one. Report no-change and unknown distinctly and test its timing against independent recorded changes. Fix `next_change()` so an `unknown` initial state becoming known is not falsely counted as a real change; the inspected saved snapshot currently exhibits that problem for RWY18.

**6. Selection, combination, and uncertainty**

The wind-comparison extension chooses one complete wind/gust candidate for all 48 hours. It does not learn a new router for every weather condition or select u, v, and gust independently. The separate OD classifier is evaluated on OD outcomes; a wind-score winner is not automatically the best operating-direction model.

Use selection-partition data only. To replace raw ICON-EU, a candidate must improve vector RMSE, keep speed MAE within the existing 2% tolerance, and have gust MAE no worse than raw on the matched gust cohort. Require at least 100 matched rows across ten issue dates for both selection cohorts; these are minimum demo guards, not proof of significance. Reject candidates that lose reference coverage. Keep raw when the evidence is missing or the gate fails.

Among passing candidates choose lowest vector RMSE, with gust MAE as the next tie-breaker and a fixed ID order for exact ties. The fixed equal blend competes under the same rules. Save the winner, member weights, scores, coverage, gate outcomes, and fallback order in `policy.json`. Do not fit weights on the final test or change them in the live agent.

At runtime, if the selected candidate cannot produce a valid wind vector for an hour, fall back to that hour's eligible raw ICON-EU; if raw is absent, return unknown. Preserve missing gusts and let the existing runway-rule functions determine which conclusions remain possible. Record the selected and effective candidate and fallback reason for each hour. Never substitute an unranked GFS source into the selected forecast silently.

Individual experimental candidates can initially have null probability fields; that is an intermediate comparison state, not challenge completion. Preserve the existing, separately labeled RWY18 ML probabilities. Before promoting a different wind winner/blend into the required forecast, compute its own joint residual calibration on the reserved calibration partition using the existing probability machinery, then evaluate Brier/reliability and adverse-event coverage. Do not inherit another model's calibration pool. Report raw-wind fallback probabilities under their true model identity when the current artifact is reused. The learned OD probabilities come from the independent-label classifier above. Missing support still means null plus an explicit incomplete status, never invented confidence. Model spread and agreement fractions are descriptive, not calibrated confidence.

Reuse the challenge rules unchanged: landing tailwind greater than or equal to 10 kt forces an immediate OD change; departure tailwind greater than or equal to 15 kt prevents departure; crosswind strictly greater than 40 kt includes gusts. The strictly longer-than-30-minute persistence rule applies only to small positive tailwind below 10 kt; headwind is preferred. Use one airport-wide OD for all 07/25 runways, with headings 070/250 degrees true; RWY18 remains southbound at 180 degrees true and may be used in either OD. Apply each baseline candidate's time series through its own `DirectionState`, initialized from the same available state. Label rule estimates separately from learned actual-OD predictions. Hourly candidates cannot resolve minute-level changes or prove continuous conditions between samples.

**7. Live sources and time alignment**

Use the saved forecast snapshot's `forecast_reference_time` and its exact 48 target timestamps. Require a recent snapshot and report its age; older-than-two-hour snapshots are stale and must not be presented as a fresh recommendation. `generated_at` records actual comparison generation separately.

Select explicit model runs as of that reference. Reuse the ICON-EU availability policy. For GFS, verify the exact model identifier and returned wind/gust definitions during the probe; use model-specific availability metadata when available. If metadata is absent, record a six-hour publication-delay estimate as unverified and make that conditional status visible. Do not reuse ICON's four-hour assumption as if it were verified for GFS. Open-Meteo distinguishes initialization from public availability in its [Single Runs documentation](https://open-meteo.com/en/docs/single-runs-api).

`sources.parse_forecast()` currently assigns four hours to every archived model. Add only the small explicit availability-policy parameter needed for the additional source, retaining current defaults for existing callers. Verify callers in `pipeline.py`, `ml_data.py`, and `ml_live.py` and the parser tests. Cache new source runs by model/run and retain their raw metadata separately.

For live persistence use an observation whose availability is no later than the comparison reference; never backdate a just-retrieved observation without evidence. Record its averaging interval and age; exclude observations older than 90 minutes from this benchmark. Unknown historical availability remains an explicit assumption.

Probe one recent GFS run and a few archived runs spanning the existing partition dates, within the source-step timebox. Verify coordinates, units, horizon, missing gusts, and interval definitions. Missing archive coverage or incompatible gust intervals restrict the report to the comparable variables. Do not launch a broad source crawler or add several providers when this probe fails.

After the demo, GFS can become eligible only after a cached backfill, as-of joining by shared decision/valid times, comparable target intervals, and the same validation gate on disclosed common cohorts. Its live inclusion alone is not evidence of predictive skill.

**8. Files, callers, configuration, and contracts**

| File | Planned change |
| --- | --- |
| New `fra_forecast/comparison.py` | Candidate execution, linear model/blend, matched evaluation, discovery summaries, saved policy, and live comparison. Use plain functions and a fixed candidate list. |
| New `fra_forecast/operations_ml.py` | Minimal independent-label OD classifier, certainty output, and target-level evaluation; use existing label and feature helpers. |
| New `fra_forecast/submission.py` | Replay requested issue times from eligible archives and write jury forecasts plus a validation/coverage report. |
| `fra_forecast/pipeline.py` | Correct unknown-state transition handling in `next_change()`; preserve the legacy response shape and fallback behavior. |
| `fra_forecast/ml_live.py` | Add optional learned OD output and its change summary without replacing baseline semantics or existing RWY18 fields. |
| `fra_forecast/wind_ml.py` | Reuse existing helpers; extract the boosting-fit block only if required to avoid duplicate training code. Preserve `train-ml`, its reports, validation gates, and artifact version. |
| `fra_forecast/sources.py` | Small source-specific availability change described above; preserve parser validation and retries. |
| New `fra_forecast/agent.py` | One bounded tool loop, application-side tool dispatch/validation, and evidence-based output. |
| `fra_forecast/cli.py` | Add required `train-operations`/`export-submission` commands and the four extension commands below, using existing error/exit-code conventions. |
| `fra_forecast/server.py` | Add four read-only report routes; use the existing 404 behavior when reports do not exist. |
| New `tests/test_operations_ml.py`, `tests/test_submission.py`, `tests/test_comparison.py`, `tests/test_agent.py` | Focused target/label, export, numerical, cohort, policy, and tool-boundary checks; no exhaustive scaffolding. |
| Existing tests | Extend parser/caller coverage only where behavior changes; run baseline, wind-ML, and departure regression tests. |
| `docs/backend-data.md`, `docs/wind-ml.md`, `README.md` | Add new routes, workflow, field semantics, caveats, and teammate examples. Correct the existing 1.0/1.1 API wording when documenting the final contract. |
| New `docs/model-card.md` and one-page export | Sources, target definitions, test dates/scores, key drivers and limitations, distilled from existing reports. |
| New `.env.example` | Names for optional `OPENAI_API_KEY` and `FRA_AGENT_MODEL`, without credentials. Read environment variables directly. |

No package exports, entry point, mandatory dependency, database, service, or UI changes are required. The existing `.gitignore` already covers `data/` and secret `.env` files. Preserve other contributors' work. `departures.weather_sample()` consumes legacy `forecast[].ml` statuses; new OD fields must be additive and must not change that consumer's wind/probability choice. Test the intentional next-change correction separately from unchanged forecast semantics.

Store new trained models and manifests under `data/models/wind-comparison-v1/`. Store four independently versioned JSON reports under `data/comparison/`:

| Report and route | Required content |
| --- | --- |
| `discovery.json` → `/api/discovery` | Source inventory, coverage, date partitions, diagnostic groups, matched counts, and limitations |
| `evaluation.json` → `/api/model-comparison` | Experiment ID, dataset hash, candidate definitions, cohort IDs, partition-specific scores, selection decision, and exploratory-test status |
| `forecast.json` → `/api/forecast-comparison` | Snapshot/reference timestamps, policy ID, 48 hourly candidate outputs, selected outputs, disagreements, and fallbacks |
| `agent.json` → `/api/forecast-agent` | Status, question, model ID, report/policy references, decision returned by tools, explanation, evidence references, and tool trace |

Each comparison forecast hour contains `valid_time`, integer `lead_time_hours`, a `candidates` map keyed by the IDs above, `selected`, and `disagreement`. Each candidate carries wind/gust values, source/run/availability metadata, `prediction_status`, `selection_eligible`, runway components and rule estimates, probability fields with their model/calibration status or null, and reason codes. A candidate failure is an explicit entry, not an omitted forecast hour. Carry the learned OD output and next-change summary separately from the weather-rule comparison, with their own model identity.

`selected` contains the policy winner, effective candidate, weights if blended, numerical forecast, and fallback reason. `disagreement` contains candidate count, wind-speed/gust ranges, maximum pairwise vector difference, and the candidate IDs that disagree on runway-weather states. With fewer than two valid candidates, disagreement is unknown rather than zero. A range is not an uncertainty interval.

Use the existing JSON writer, normalize nonfinite numerical values to null, and validate required fields before publishing. Tie manifests, policies, and reports together with their IDs/hashes; a missing or mismatched artifact disables selection rather than mixing experiment versions. Write the complete artifact and publish its manifest last, retaining the existing dependency/hash checks. Keep writes sequential; no background worker or scheduler is needed.

**9. AI coordinator implementation**

Use a small OpenAI Responses API function-calling loop, without an agent framework. Read `OPENAI_API_KEY` and an explicitly configured `FRA_AGENT_MODEL`; verify model/tool support when implementing rather than hard-coding a guessed model. Use the standard library HTTP client and a fixed API destination. The [official function-calling guide](https://developers.openai.com/api/docs/guides/function-calling) documents tool schemas and the application-executed tool/result cycle.

Expose four narrow tools:

| Tool | Behavior |
| --- | --- |
| `read_discovery` | Return the saved source/coverage summary |
| `read_comparison` | Return validation scores, candidate definitions, and saved policy; expose exploratory test results separately when requested |
| `run_forecast_comparison` | Run the already-trained candidates for the current snapshot, at most once per agent invocation |
| `inspect_forecast` | Return selected hours, disagreement, and the deterministic policy decision, bounded to the 48-hour horizon |

The agent can choose which evidence to inspect, run the frozen comparison, explain the chosen model/blend, and suggest an experiment in prose. The application executes the saved selection policy. The agent cannot invent weights, modify thresholds, train new candidates, replace artifacts, choose arbitrary URLs/paths, run shell commands, or convert flight schedules into labels.

Use strict tool schemas, disable parallel tool calls, validate arguments in Python, and preserve the response items required by the API while returning tool results by call ID. Bound an invocation to six model calls, one comparison refresh, a 90-second overall deadline, and 30 seconds per HTTP request. Record actual usage; the model choice determines cost. Do not add an automatic retry loop that repeats a completed write.

Attach the numeric selection directly from the tool output, never from model-generated text. Have the explanation identify the report, metric, and hour it discusses. Validate referenced candidate IDs/timestamps and retain required availability/calibration caveats beside the prose. Treat provider text and the user's question as data, not permission to broaden tool access. Send compact public-weather/metric summaries only; do not send flight records, raw datasets, secrets, or local paths to the model. Do not use the source-response cache for authorization-bearing LLM requests.

If configuration is absent, return `unavailable_configuration` with the deterministic selection and a template explanation. For a timeout, invalid tool call, or API failure, return `fallback_template` with the reason. Neither state is described as a successful AI-agent run. Keep a mock two-tool conversation for offline verification; demonstrate the real configured call separately when credentials are available.

**10. Intended commands and demo sequence**

These are implementation targets, not commands to run against the current checkout yet:

```bash
# Required OD work, once independently sourced labels are available.
python -m fra_forecast train-operations --data-dir data --labels path/to/verified-operations.csv

# Required jury replay; supplied issue times determine the exact forecast grid.
python -m fra_forecast export-submission --data-dir data \
  --issues path/to/jury-issues.csv --output-dir data/submission

# Reuse existing historical data and train the fixed candidate set.
python -m fra_forecast compare-models --data-dir data

# Summarize cached data and the comparison's development-period diagnostics.
python -m fra_forecast discover-data --data-dir data

# Existing weather refresh remains the source of the shared reference snapshot.
python -m fra_forecast refresh --live-only --no-departures

# Run frozen candidates and include the one additional source when configured.
python -m fra_forecast refresh-comparison --data-dir data

# Optional bounded network probe; no full new historical backfill.
python -m fra_forecast discover-data --data-dir data --probe-gfs

# Configured AI coordinator; failure still returns the deterministic result.
python -m fra_forecast forecast-agent --data-dir data \
  --question "Where do the forecasts disagree, and why was this forecast selected?"

python -m fra_forecast serve --data-dir data
```

`compare-models` trains/evaluates only when explicitly invoked. `refresh-comparison` never retrains. All new commands default to `data/`; no additional CLI tuning knobs are needed. GET routes only read files. The agent uses the same functions as the CLI, not HTTP calls back into the local server.

`export-submission` is independent of the optional agent. Accept explicit timezone-aware forecast issue/reference times from a small input file; confirm the organizer's time convention and map the final output schema when supplied. Produce 48 hourly records per issue, including issue/valid time, RWY18 probability and status, OD with certainty and status, next-change window/status, model IDs, and provenance. Preserve nulls with an incomplete-coverage report when evidence is missing; do not silently omit hours or use today's weather for historical dates. The model's training, selection, and calibration data must precede each replay issue; create an eligible artifact if the current one violates that boundary. Keep actual export-generation time separate from the historical issue time. Validate counts, duplicates, timestamps, availability, and artifact identity before packaging.

Write a one-page model card using existing source/metrics documents: target definitions, complete source citations, training/test periods, 1/6/24 h target metrics and baselines, principal input drivers, model/threshold versions, publication-delay assumptions, event coverage, and limitations. Distinguish implemented features, unvalidated hypotheses, and missing labels. Do not invent feature-importance numbers. Render-check the final one-page PDF before submission; a long README is not the required model card. Jury dates/schema are unresolved external inputs, not supplied by the attached brief.

The teammate's handoff includes the required forecast fields, additive OD/change contract, four extension JSON contracts, and representative real outputs. The UI can show source health, a model-score table, hourly candidate values, disagreements, the selected forecast, and the explanation. This plan includes no UI implementation or automatic migration of flight assessments to the experimental selection.

**11. Focused verification and definition of done**

Use `python -m unittest discover -s tests -v` in the existing ML environment. New checks should cover observable outcomes with small synthetic fixtures; they must not be reported as real forecast-accuracy evidence.

- Time and leakage: exact joins; future/unavailable runs rejected; source-specific delay preserved; partition-overlap purge; training preprocessing ignores later targets; changing test targets cannot alter the selected policy.
- Required targets: label availability gates initial OD; synthetic weather labels cannot masquerade as flown OD; one-class/insufficient-label training is unavailable; probability sums/bounds and certainty definitions are checked; unknown-to-known transitions are not real changes.
- Fair comparisons: common-row wind/gust scores and missing-coverage counts; repeated runs do not masquerade as independent events; small diagnostic groups remain unscored.
- Numerical behavior: directions near 359°/1° blend correctly, calm/missing inputs stay distinct, gust handling preserves unknowns, and challenge threshold/persistence boundary tests still pass.
- Selection: an inferior candidate loses, a qualifying candidate wins, deterministic ties, correct fixed weights, and a missing constituent leads to explicit fallback rather than a new blend.
- Live/API: exactly 48 aligned hours; strict JSON without NaN; unavailable source/artifact and mismatched manifest cases; legacy wind/departure semantics remain stable while OD fields are additive and the next-change bug is explicitly corrected; missing report routes return 404.
- Agent: valid two-tool flow, rejected unknown tool/argument, model attempts to invent weights, bounded timeout/configuration failures, and tool-derived numeric output surviving explanation failure.
- Submission: 48 unique future hours per supplied issue, replay artifacts/data available as of that issue, no substitution of current forecasts, explicit missing-output report, and a rendered one-page card with sources/quality/drivers.

Run one real end-to-end comparison after those checks, inspect the saved outputs, and make one request to each new route. Demonstrate one missing-source case. If agent credentials are available, make one bounded real call; otherwise explicitly record that the agent integration was only tested with mocks.

Challenge completion and extension completion are separate. The challenge needs the required 48-hour outputs, actual-OD/certainty/change evaluation, 1/6/24 h results against the section 3 baseline, source citations, the one-page card, and jury-day forecasts. Missing labels, missing certainty, or missing jury inputs remain explicit gaps. The brief asks to beat the baseline; report whether the evidence does or does not establish that objective. Never claim improvement without the corresponding labels and evaluation.

The comparison extension is complete when the five candidates are inspectable, the additional source has a disclosed probe/result status, the policy is reproducible, disagreements and limitations are visible, and the teammate has stable JSON. AI-agent completion additionally requires a real successful tool-calling run. These extension milestones cannot substitute for challenge completion.

**12. Follow-ups after the demo**

After required work: backfill and rank the additional source, collect more independent/rare-event evaluation data, and evaluate fixed lead-band selection if enough dates support it. Operations-label discovery, required probability outputs, and submission packaging are not post-demo extras. Learned stacking, dynamic routing by weather regime, additional providers, broader feature searches, and autonomous retraining wait for evidence that they improve the core task.

Review checks completed: read and visually inspected the complete one-page PDF; inspected current source/training/live/CLI/API/label/departure code and saved forecast/metrics; verified all 43 existing offline tests pass. Only project instructions, source-brief copies/transcription, and documentation changed during this review. No application code was changed, models retrained, source probes executed, or paid API requests made.
