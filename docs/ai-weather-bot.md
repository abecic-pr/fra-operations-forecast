# AI Weather Bot

The dashboard contains a read-only project assistant. The Python API calls the OpenAI Responses API, using a reasoning model, function calling for project data and strict Structured Outputs for the answer. Default model: `gpt-5-mini`; override with `OPENAI_MODEL` on the backend. Model access still depends on the OpenAI project/account.

## Connect locally

1. Add your key to the ignored root `.env` file as `OPENAI_API_KEY=your-key`. The placeholder file has been prepared locally. Alternatively set `OPENAI_API_KEY` in the server environment. Never place it in a VITE_ variable or browser storage.
2. Run `python3 -m fra_forecast serve --port 8000` and `npm run dev` in separate terminals.
3. Open the dashboard. It checks connection configuration every 15 seconds; `.env` edits are read without restarting. Configured means a key exists, not that OpenAI has authenticated it. The first real question verifies provider access.

With no key, questions are not sent to OpenAI. Preview charts & map returns actual saved data with an explicit preview label, not a generated answer. No live OpenAI completion has been verified until a key is supplied.

## API

- `GET /api/weather-bot/status`: key presence boolean, model, provider and read-only flag. No secret is returned.
- `GET /api/weather-bot/preview`: deterministic labeled real-data preview with a chart and map.
- `POST /api/weather-bot`: `{message, history:[{role,content}], selected_time}`. Requires same-origin `X-FRA-Chat: 1`; one answer at a time, 40 KB body, 4,000-character question, at most 12 prior messages. The response includes `answer`, concise `explanation`, source dataset IDs, `visuals`, `mode`, model and timestamp. Authentication, provider limits and failures return distinct errors without upstream body leakage.

The model reasons internally. The UI shows a truthful working state while the request runs and returns a concise evidence explanation; it does not expose hidden chain-of-thought or pretend staged progress is model reasoning. Previous messages are kept only in browser component memory, not saved on the backend; New chat clears them. `store:false` is sent to OpenAI. This is a local tool on loopback; public deployment requires authentication and per-user rate limits.

## Data scope

The model receives a fresh catalog per question. Read-only `read_project_data` retrieves JSON, CSV, JSONL and Markdown under the configured data directory and docs, plus README. Sources include weather, baseline forecasts, checked provisional measurements, truly issued forecasts, operations snapshots, departures, diagnostics, future local model metrics, challenge-rule notes and a dated shared-knowledge snapshot. The shared Page is not fetched live by the app; update docs/shared-knowledge.md after collaboration changes. Raw binary/ZIP caches, model weights, environment files and arbitrary system paths are not exposed. Source provenance is available through the normalized source records. Missing artifacts stay unavailable; main's ML additions are not silently enabled here.

Retrieval uses exact catalog IDs, bounded pages and character windows; callers can follow next_offset. A request caches every dataset it opens so a chart and the model use the same loaded forecast snapshot. At most seven model rounds and twelve tool calls are permitted. Document/data contents are reference material, not assistant instructions. A server-only key and project question/retrieved excerpts are sent to OpenAI; no secret file is included in the catalog.

Structured replies select only approved visual types: tailwind_chart, crosswind_chart, airport_map. Numeric chart values and null gaps are built on the server from saved baseline forecast points, never model-generated. Maps use interactive OpenStreetMap tiles and bundled Runway 18 geometry. Model output is rendered as plain text, never HTML or executable code. Charts show issue time and UTC, so an old saved forecast is visible as old. Sources are filtered to data actually retrieved (or used for a visual).

Runway closure, aircraft clearance, model calibration, rain and flight/runway assignments cannot be inferred where data is missing. The bot preserves the case limits and separates measured values, forecasts, weather suitability and official runway status.

## Verification

`python3 -m unittest discover -s tests -v` includes mocked provider tool-loop tests, absent key, incomplete/refused output, history validation, path boundaries, source filtering, frozen snapshots, null chart gaps and tool limits. Mocked calls do not validate real account/model access. `npm run build` verifies TypeScript and frontend output. Browser testing covers the no-key UI, actual-data preview chart/map and question handling; a real completion requires the user's key.

Official implementation references:

- [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)
- [GPT-5 Mini capabilities](https://developers.openai.com/api/docs/models/gpt-5-mini)

Antonio’s tool-calling airport/flight assistant is preserved independently at `/api/chat`; see [its contract](chatbot.md). The dashboard retains the visual assistant contract at `/api/weather-bot`. Both remain disconnected without backend credentials.
