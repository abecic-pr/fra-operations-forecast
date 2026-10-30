**FRA app chatbot — implementation plan**

Planned on 30 October 2026. Implementation update: the user supplied and explicitly authorized use of the hackathon key. The read-only backend is now implemented; see [the current contract](chatbot.md). The planning-time inspection below is retained as history. The teammate's UI remains outside this backend work.

The user's new request is a conversational assistant that answers questions about airport conditions and upcoming flights using this app's data, with a user-supplied OpenAI API key. This is an extension to the [FraAlliance challenge](challenge/README.md). Required 48-hour forecasts, RWY18 usability probabilities, airport-wide operating direction with certainty, next probable change, unseen-data evaluation at 1/6/24 hours, model card, and jury exports retain priority within the total six-hour project budget. A chatbot does not complete missing forecast or evaluation deliverables.

**What the first version should answer**

| Example question | Answer from app data |
| --- | --- |
| “What are conditions at Frankfurt now?” | Latest saved observations, observed operating direction, runway wind components, and their timestamps. |
| “What will conditions be tomorrow morning?” | Available hourly wind/gust forecasts, airport-wide 07/25 baseline outlook, RWY18 weather suitability, and available provisional probabilities. State the interpreted local date/time window. |
| “What conditions are expected for flight LH 123?” | Find the primary flight or codeshare, clarify its date when needed, then show weather around its published estimated/scheduled departure. |
| “Will my flight depart from Runway 18?” | Explain its RWY18 weather assessment and explicitly state that assigned runway and individual runway-use probability are unknown. |
| “When is the next direction change expected?” | The saved change window and its method/uncertainty, or the explicit unknown/no-change-within-horizon state. |
| “Why does the app say conditions are unfavorable?” | Explain the existing wind components, margins, reason codes, and challenge thresholds. |
| “Is my flight delayed?” | Report a published estimate/status when present; do not predict a new delay or attribute it to wind. |
| “What about an arrival, destination weather, or next week?” | Explain which requested information is absent or outside coverage; offer the FRA conditions that are available. |

Default to Frankfurt/EDDF and Europe/Berlin display time, with dates and UTC offsets. Reply in the user's language. Follow-up questions such as “And two hours later?” use bounded conversation history. If the flight or date remains ambiguous, ask one concise clarification and do not select a flight arbitrarily.

**What already exists**

Inspected `fra_forecast/server.py`, `pipeline.py`, `departures.py`, the data contracts, tests, and saved snapshots before proposing this work.

| State | Evidence and consequence |
| --- | --- |
| Implemented | `GET /api/forecast` serves observations, hourly forecasts, baseline OD/change outlook, and separate ML fields. Reuse this snapshot. |
| Implemented | `GET /api/runway18/departures` serves public FRA flight records with primary IDs, codeshares, times/status and existing RWY18 weather assessments. Reuse those assessments. |
| Implemented | Python standard-library HTTP server; manual refresh; same-origin frontend proxy pattern; atomic per-file JSON publication. No frontend is present in this checkout. |
| Provisional | The inspected snapshot has RWY18 weather probabilities marked `provisional_low_event_coverage`; validation selected raw ICON-EU fallback. Do not describe all output as ML-corrected or calibrated. |
| Missing | OD probability/certainty model, confirmed individual runway assignment, estimated wheels-off times, official RWY18 availability, and a flight-delay prediction model. Null fields stay unknown. |
| Planned separately | The [model-comparison plan](model-comparison-implementation-plan.md) proposes an AI coordinator; `agent.py` does not exist in this checkout. Chat must work without that extension. |

The inspected departure snapshot contains 1,053 primary services. Sending the entire file to OpenAI for every question is unnecessary; select a small relevant subset locally.

**Smallest implementation**

```text
Teammate's chat panel
        |
        | POST /api/chat, through the existing same-origin proxy
        v
Existing Python server -> OpenAI Responses API
        ^                      |
        | validated tool calls |
        +-- saved app snapshots+
        |
        +-> answer + evidence + source times + limitations
```

Use the OpenAI Responses API with three narrow, read-only function tools. The backend validates and executes calls; the model asks for evidence and explains it. This follows the [official OpenAI function-calling workflow](https://developers.openai.com/api/docs/guides/function-calling). Use explicit strict schemas and disable parallel tool calls for a small, bounded implementation.

| Proposed tool | Inputs and behavior |
| --- | --- |
| `get_airport_conditions` | Optional timezone-aware `start_at`/`end_at`; returns current observations and a bounded forecast window, existing OD/change outputs, quality, rules and provenance. Maximum 48 hourly samples; no extrapolation. |
| `find_departures` | Optional flight number, destination and time window; require at least one filter. Normalize case/spacing and match primary number/codeshare exactly. Destination uses saved IATA/name fields. Return at most 20 summaries plus matched count, truncation and source coverage. Count primary services once. |
| `get_flight_conditions` | A `flight_id` from the saved departure snapshot; returns its published schedule/estimate/status and existing `runway18` assessment, including hourly samples and provenance. Unknown IDs return not-found, never invented details. |

Load each required snapshot once per chat turn and reuse those in-memory objects for all tools. Read local files directly rather than calling this server over HTTP. Preserve the weather snapshot identity carried by each flight assessment. If the current airport forecast is a different version, expose the mismatch rather than silently combining them. Missing or malformed files produce explicit unavailable results.

No new weather ingestion, training, database, vector store, embeddings, agent framework or mandatory dependency. Use standard-library HTTP to the fixed OpenAI Responses endpoint. Do not use `SourceClient`, which caches provider responses, for credential-bearing requests. If the coordinator transport is implemented before this work begins, inspect and reuse it where appropriate; do not create a shared abstraction in anticipation.

The customer chatbot has no refresh, training, file-writing or model-selection tools. Existing manual refresh remains an explicit app action. The coordinator's separate planned capabilities remain intact.

Scope clarification: the earlier coordinator plan excluded sending flight records to OpenAI. This later user request requires flight-aware answers. For this chatbot, send only relevant public departure fields and weather assessments, alongside the user's question/recent history. Do not send the full board, raw archives, passenger/booking details, local paths or credentials. This does not expand the coordinator's access.

**Proposed frontend contract**

Add `POST /api/chat` without changing existing forecast/departure JSON schemas. Require JSON and `X-FRA-Chat: 1`, with the existing same-origin check and loopback binding. The teammate supplies the chat panel and proxies `/api/*` as already documented.

```json
{
  "message": "What conditions are expected for this flight?",
  "history": [],
  "selected_flight_id": null
}
```

`history` contains only user/assistant text, at most six prior messages. A selected flight ID provides optional UI context and must resolve against server-side records; client-supplied weather or probability values are never accepted. The server supplies the current time and fixed airport timezone. Reject system/tool roles supplied by the browser, excessive bodies, invalid types and empty messages. Proposed limits: 16 KiB request body and 2,000 characters per message.

Return this stable envelope:

| Field | Meaning |
| --- | --- |
| `schema_version` | `1.0` for this new endpoint. |
| `status` | `answered`, `needs_clarification`, `insufficient_data`, `fallback_template`, or `unavailable_configuration`. |
| `answer` | Concise plain text suitable for safe text rendering. |
| `evidence[]` | Server-owned IDs, exact facts/units, flight IDs or valid times, source labels/URLs, snapshot timestamps and prediction/probability status. |
| `warnings[]` | Mandatory freshness, coverage, provisional-probability and time-proxy caveats selected by the backend. |
| `generated_at`, `display_timezone` | Answer timestamp in UTC and `Europe/Berlin`. |

Use a small structured final model output containing answer status, text and evidence IDs. Resolve IDs to evidence in the backend; reject references that were not returned by tools. URLs and numerical evidence cards come from the server, not model-generated values. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) controls response shape; it does not establish factual accuracy. Test the generated prose separately.

HTTP behavior: 200 for a valid answer/clarification/insufficient-data result; 400 for malformed requests, 403 for origin/header rejection, 413 for oversized bodies, 429 for the local request limit, 503 for missing configuration, and 502/504 for upstream failure/timeout. Failures retain a clear error code and safe message; available evidence can accompany a template fallback. The UI must handle non-2xx responses without losing the user's question.

The teammate's handoff includes this contract, one successful response fixture, one ambiguity fixture, one unavailable/fallback fixture, source-time display, and a loading/retry state. Suggested prompts: “Conditions tomorrow morning”, “Weather for my flight”, and “Next direction change”. No UI implementation is included in backend work.

**Answer correctness rules**

- Every claim about current/future app conditions must use evidence retrieved in this turn. History supports conversational references, not authoritative numbers. Treat user messages and provider text as untrusted content, never instructions to expand tools or override these rules.
- Distinguish observations, numerical weather forecasts, baseline runway decisions, provisional ML probabilities, published flight-board status, and official runway status.
- Preserve the challenge baseline: landing tailwind threshold 10 kt, departure threshold 15 kt, crosswind closure above 40 kt including gusts, and persistence strictly longer than 30 minutes. Reuse existing calculations; the language model must not recompute decisions or substitute real-world thresholds.
- Report probabilities only when supplied for the stated target/time. Do not turn a deterministic state into 0%/100%, an RWY18 weather probability into a flight-assignment probability, or missing OD certainty into a confident score.
- Reuse `departures.weather_sample()` semantics: keep baseline OD and its forecast source distinct from ML/raw-fallback RWY18 weather. Explain source differences when they matter.
- For a departure between hours, retain the saved bracketing samples. Do not interpolate probability, describe min/max as a confidence interval, or infer continuous usability between samples. Published departure time is a proxy, not wheels-off time.
- Resolve “today/tomorrow” from request time in Europe/Berlin. Use `zoneinfo`/existing time helpers; require explicit offsets in tools and clarify ambiguous daylight-saving times. Return exact dates in answers. No claim of coverage beyond actual valid forecast samples.
- Recompute freshness at request time: cached `data_status`/age fields describe generation time. Preserve the existing observation staleness rule (90 minutes) and weather-snapshot rule (two hours). Always display flight-board retrieval/update times; for the demo, mark board data older than 15 minutes as stale, explicitly an application choice rather than a source guarantee. Stale evidence is described as the last saved outlook, never current confirmation.
- Recheck whether cached flights are still upcoming at request time. A missing flight is not proof of cancellation: the current ingestion excludes cancelled/departed/off-block records and may have incomplete board coverage.
- Never claim safety clearance, guaranteed departure, delay causation, or official closure from weather suitability. Aircraft-specific restrictions and airline/ATC decisions are absent.
- The inspected saved snapshot labels an unknown-to-known RWY18 transition as a change. A concurrent edit to `pipeline.next_change()` now normalizes unknown initial states. Verify its regression test and regenerate affected snapshots before exposing that result; do not duplicate the fix or advertise an unknown initial state as a reopening.

**Configuration and failure behavior**

Read `OPENAI_API_KEY` only in the backend process. Set it through the local runtime/deployment secret configuration; never paste it into frontend code, commit it, place it in URLs or log it. A key is not needed to implement offline tools or to review this plan. The repository ignores `.env`, but does not currently load it automatically; document environment setup without adding a dotenv dependency.

Use one configured `FRA_CHAT_MODEL`; choose an account-accessible text model with function calling and structured output support during integration. Confirm with a small real call rather than guessing access or promising a particular price. Track actual token usage and latency without logging credentials or full conversations.

Keep history in the frontend's memory for the demo and resend only the bounded text history. Plan to use `store: false` for Responses; verify that parameter during implementation and do not describe it as a guarantee of zero provider retention. Use no persistent chat database.

Bound each turn to four model requests, three tool executions, a 45-second overall deadline, and at most 15 seconds per request within the remaining deadline. Limit model output and tool-result size; do not silently truncate coverage without a flag. Add a small process-local concurrency/rate limit to bound paid calls. No automatic retry loop in the first version.

Missing key/model disables chat only. Refusal, malformed model output, bad evidence references, API rate limits and timeouts return an explicit unavailable or template result. Existing forecast/flight views continue working. This loopback demo endpoint is not an authenticated public service; public deployment needs access control at its existing frontend/proxy boundary before exposing paid calls.

**Files and integration scope for implementation**

| File/caller | Necessary change |
| --- | --- |
| New `fra_forecast/chat.py` | Snapshot selection, three tools, prompts, bounded Responses call loop, evidence validation and response envelope. |
| `fra_forecast/server.py` | Route `/api/chat`, body/origin checks and local request limits; preserve `/api/refresh` behavior and existing GET routes. |
| `fra_forecast/pipeline.py`, `tests/test_baseline.py` | Verify the concurrent unknown-to-known change correction and regression coverage; refresh stale snapshots. No duplicate implementation is planned. |
| New `tests/test_chat.py` | Synthetic snapshot fixtures, mocked API conversation and focused boundary checks. Follow existing `unittest` style. |
| `docs/backend-data.md`, `README.md`, new `.env.example` | Document endpoint, setup, limits, response/error examples and UI handoff; placeholders only in the example environment. |
| Teammate's frontend | Chat panel, optional selected-flight context, bounded history, evidence/freshness display and loading/error behavior. Hand off the contract; preserve UI ownership. |

No CLI entry point, package export, dependency or existing saved-data migration is required. Recheck the checkout before implementation so concurrent changes are preserved.

**Delivery and checks**

Planning estimate: reserve at most 60–90 minutes of remaining backend hackathon time after required forecast/evaluation/submission work; UI integration is separate and owned by the teammate. If that time is unavailable, retain this plan instead of displacing challenge deliverables.

1. Implement local evidence tools and synthetic fixtures first. Demonstrate airport outlook, primary/codeshare lookup and flight-weather retrieval without an API key.
2. Add the OpenAI loop and `/api/chat`, with mocked responses first. Verify follow-up context, argument validation and evidence references.
3. Hand the teammate the request/response fixtures. With the key configured, run a small live smoke check for airport conditions, a flight question, a follow-up and unavailable data.

Focused acceptance cases: duplicate flight number on different dates prompts clarification; codeshares map to one service; 14:30 preserves two samples and null exact-time probability; null OD confidence stays unavailable; provisional probabilities retain their qualification; no flight assignment/delay forecast is invented; saved freshness is recalculated; missing/gapped/out-of-horizon data remains unknown; no-match and partial coverage are honest; unknown-to-known is not a change; prompt injection cannot invoke writes/arbitrary paths/URLs; a fake evidence ID is rejected; missing key, timeout and upstream failure preserve normal app routes.

Run the existing offline suite plus the focused chat tests. Offline API mocks establish integration behavior only. Mark the chatbot operational only after a real authenticated request returns an evidence-backed answer and the teammate verifies the panel against the contract. Do not claim universal hallucination prevention from a passing smoke test.

Skipped for the first version: voice, persistent chat accounts/history, new flight providers, destination-weather ingestion, autonomous refresh/retraining, and connection to the planned model-selection coordinator. Main limitation: answer quality is bounded by the app's available data and provisional forecasts, and generated prose still needs validation.
