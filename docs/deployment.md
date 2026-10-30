# Vercel deployment

Production: https://fra-operations-forecast.vercel.app (Pencilrec team,
`fra-operations-forecast` project). Deploy from the tested source snapshot;
unfinished local changes are not automatically published.

The Vite frontend and existing Python API run in one Vercel project, in Frankfurt.
The API uses HTTPS origin checks and refreshes a saved forecast older than ten
minutes when `/api/forecast` is requested. Manual refresh remains available.
No forecast JSON fields or weather rules change.

Prepare a fresh local snapshot and an allowlisted deployment bundle:

```sh
python3 -m fra_forecast refresh --live-only --history-days 1 --archive-days 0
python3 scripts/prepare_deployment.py
npm run check:wind
npm run build
vercel deploy --prod --scope pencilrec
```

`deployment-data/` must be a new directory when packaging. It includes saved
public forecasts/departures, wind-model artifacts and the trained provisional
`operations-v3` artifact/report, without raw training data, source-history extracts
or secrets. It is
ignored by Git and included in the explicit CLI deployment. A deployment from
Git alone needs this packaging step and its data before building.

Vercel uses temporary per-instance storage. Forecasts refresh on demand, but
issued-forecast history and verification caches can reset on cold starts or
redeployment. Keep the durable local evaluation archive. Concurrent instances
can serve different refresh timestamps; inspect each snapshot's timestamps.

The deployment does not upload `.env`. On 30 October 2026, the user explicitly
approved storing the hackathon `OPENAI_API_KEY` as a Production-only Vercel
Secret in Pencilrec / `fra-operations-forecast`. Production `OPENAI_MODEL` and
`FRA_CHAT_MODEL` are configured as `gpt-5.4-mini`. Preview and Development
environments were not given this key. Keep it server-side; never use `VITE_`.

Environment changes require a new deployment. The original production failure
was missing configuration: `/api/weather-bot/status` returned `configured: false`.
The corrected production deployment is `dpl_N7aeDeJUmfm9DcLAYXEmocVApvTC`
(`https://fra-operations-forecast-clpo94xft-pencilrec.vercel.app`), serving the
stable production alias above. It uses a source export of `ad9fdda` plus the
small `weather_bot.py` lookup-guidance correction, excluding unrelated local
changes. The correction is also saved to GitHub `main` in commit `9c64a5a`;
retain it when the team's later source changes are deployed.

Verified: six chatbot tests, two hosting checks, production build, a real local
OpenAI completion, and browser tests on the production alias for a six-hour wind
answer with charts plus a follow-up Runway 18 map. The follow-up explicitly
reports official opening status as unconfirmed. Map geometry is rendered by the
app; the model no longer needs to search datasets for it. A configured status
badge alone is not evidence of a successful OpenAI answer.

Vercel excludes the local packaging-only `pyproject.toml` and installs
`requirements.txt` under Python 3.14. Python dependencies pin scikit-learn to the saved model's version. If retraining
changes that version, update `requirements.txt` together with the artifacts.
