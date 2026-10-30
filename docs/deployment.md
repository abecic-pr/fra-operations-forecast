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
public forecasts/departures and the existing wind-model artifacts, without raw
training data, secrets, or unfinished operating-direction artifacts. It is
ignored by Git and included in the explicit CLI deployment. A deployment from
Git alone needs this packaging step and its data before building.

Vercel uses temporary per-instance storage. Forecasts refresh on demand, but
issued-forecast history and verification caches can reset on cold starts or
redeployment. Keep the durable local evaluation archive. Concurrent instances
can serve different refresh timestamps; inspect each snapshot's timestamps.

The deployment does not upload `.env` or configure an OpenAI key. The dashboard
bot's real-data preview works without credentials. AI answers require separate
server-side configuration and access controls before public use.

Vercel excludes the local packaging-only `pyproject.toml` and installs
`requirements.txt` under Python 3.14. Python dependencies pin scikit-learn to the saved model's version. If retraining
changes that version, update `requirements.txt` together with the artifacts.

The parallel-runway traffic feature adds `traffic.json` to the public snapshot allowlist. Run normal refresh (including arrivals/departures) before packaging, or run `python -m fra_forecast.traffic`. Confirmed assignments and aircraft coordinates are not available from the public passenger boards; production keeps these unknown.
