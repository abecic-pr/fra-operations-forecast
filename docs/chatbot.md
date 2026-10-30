**Airport and flight chatbot — backend contract 1.0**

`POST /api/chat` answers questions using saved FRA observations, forecasts and public departure assessments. The implementation is in `fra_forecast/chat.py`, with the existing HTTP transport reused from `agent.py`. There are no new dependencies. The teammate owns the chat panel.

**Run locally**

Set `OPENAI_API_KEY` and `FRA_CHAT_MODEL` in the backend environment. The local `.env` file is ignored by Git; `.env.example` contains placeholders. The server does not load environment files automatically.

```bash
# From the repository root; load your trusted local configuration without printing it.
set -a
source .env
set +a
python3 -m fra_forecast serve
```

The hackathon configuration uses `gpt-5.4-mini`. The [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini) lists support for Responses, function calling and structured outputs. A different model must support those features and be available to the account.

Refresh data through the existing app refresh action or CLI. Chat reads saved data and never refreshes, trains, selects models, modifies files or requests arbitrary URLs. The existing forecast and departure JSON schemas are unchanged.

**Frontend request**

Proxy `/api/*` to `http://127.0.0.1:8000` from the frontend server, preserving its browser-facing Host as with `/api/refresh`. No CORS is enabled. The backend requires a same-origin browser request and the explicit chat header.

```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-FRA-Chat': '1' },
  body: JSON.stringify({
    message: 'What are conditions for this flight?',
    history: [],
    selected_flight_id: null,
  }),
});
const reply = await response.json();
// Check response.ok; errors also contain an answer for display.
// Render reply.answer as text, plus reply.evidence and reply.warnings.
```

`message` is required, nonempty and at most 2,000 characters. Optional `history` contains at most six `{role, content}` objects, with role `user` or `assistant` and 1–2,000 characters each. The UI keeps history in memory. Optional `selected_flight_id` refers to a saved primary service; it does not carry client-provided weather. Maximum body size is 16 KiB. Other fields/roles are rejected.

**Response**

| Field | Meaning |
| --- | --- |
| `schema_version` | `1.0`. |
| `status` | `answered`, `needs_clarification`, `insufficient_data`, `fallback_template`, or `unavailable_configuration`. |
| `answer` | Plain text. References such as `[e1]` point to evidence entries; do not render model text as HTML. |
| `evidence[]` | `{id, tool, data, warnings}` objects copied from backend tool results. |
| `warnings[]` | Backend-selected data-quality and interpretation limitations; keep visible beside the answer. |
| `generated_at`, `display_timezone` | UTC answer timestamp and `Europe/Berlin`. |
| `model`, `usage[]`, `elapsed_seconds` | Model, actual per-call token counts, elapsed time when a call was attempted. These can stay outside normal UI. |
| `error` | Stable failure code when relevant; no raw API errors, credentials or internal paths. |

Evidence tools:

- `get_airport_conditions`: current observations/operating direction, up to 48 hourly forecasts, separate baseline and selected RWY18 weather, optional independently trained OD fields, change outlook and rules. No extrapolation beyond available samples.
- `find_departures`: exact primary/codeshare-number matching, destination and timezone-aware time filters. At most 20 primary services plus matched count, truncation and coverage. One match also includes its saved weather assessment. Repeated flight numbers on multiple dates produce a deterministic clarification before the model can choose one.
- `get_flight_conditions`: saved schedule/estimate, published status and RWY18 assessment, including exact/bracketing/proxy samples and snapshot identity. Expired assessment times are excluded from the upcoming list.

UTC source timestamps remain intact. `display_times` and `valid_time_local` are computed in Python using Europe/Berlin, including daylight-saving offsets. Use these for display instead of relabeling UTC. A flight assessment may use a different snapshot from the airport forecast; the response reports the mismatch.

The backend recalculates ages at request time. Observations/observed OD older than 90 minutes, weather snapshots older than two hours, and departure-board snapshots older than 15 minutes receive stale warnings. The board threshold is an application choice, not a provider update guarantee. Unknown/future timestamps are not described as fresh.

| HTTP code | Meaning |
| --- | --- |
| 200 | Answer, clarification or insufficient data; inspect status and warnings. |
| 400 / 403 / 413 | Invalid body / origin or header rejected / body too large. Compact `{error, answer}` response. |
| 429 | Local limit: two concurrent requests and 12 accepted requests/minute. Compact `{error, answer}` response. |
| 503 | `unavailable_configuration`: key or model missing. Other routes still work. |
| 502 | `fallback_template`: upstream authentication/rate-limit/network failure or invalid model/tool output. |
| 504 | `fallback_template`: request deadline/timeout. |

No automatic retries. A turn has at most four model requests, three tool calls, 1,400 output tokens per model request, 15 seconds per request and a 45-second overall deadline. Tool output is limited to 128 KB. History and raw responses are not persisted by the endpoint. Responses requests use `store: false`; this disables response-state storage and is not a promise of zero provider retention. See [official Responses guidance](https://developers.openai.com/api/docs/guides/migrate-to-responses).

**Interpretation and handoff**

RWY18 probabilities describe weather suitability only. Baseline OD probabilities can be null; ML probabilities retain their status. A schedule/estimate is a departure-time proxy, not a wheels-off estimate. Half-hour departures retain separate hourly samples and null exact-time probability. Matching usable endpoints does not prove continuous usability. Assigned runway, official RWY18 status and new delay predictions are not inferred.

The UI should show loading, retain questions on errors, support a deliberate retry, and display evidence/source times and warnings. Suggested prompts: “Conditions tomorrow morning”, “Weather for my flight”, “Next direction change”. Synthetic success/clarification/unavailable envelopes are in `examples/chat-responses.json`; these are not real forecasts. Local live verification output is saved separately in ignored `data/chat-smoke.json`.

Run `.venv/bin/python -m unittest discover -s tests -v` (or `python3` without optional ML dependencies). HTTP tests require a temporary loopback port. Focused checks cover times/DST, codeshares, ambiguity, hourly bracketing, stale data, null probabilities, invalid tool access/evidence, API failures and existing routes.

This is a local hackathon backend. Public deployment needs authentication at the frontend/proxy boundary before exposing paid calls. Generated prose can still misstate evidence; evidence cards and focused/live checks do not prove hallucination prevention. Chat does not satisfy missing forecast-model evaluation or challenge submission deliverables.
