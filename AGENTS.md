# Shared project knowledge

The shared knowledge base for Philipp and Antonio is the **FRA Operations Forecast** Page in the Pencilrec Space:
https://chatgpt.com/space/page_fe8b5e3a0f788191867be7f4e42de933

- Before every major change, read the current Page through the Pages tools and consult relevant linked project Pages for new information. Do not rely solely on an earlier chat snapshot.
- Major changes include app structure, substantial design work, data sources, the shared data contract, forecasting rules, model behavior, dependencies and repository or deployment changes.
- Reconcile new information with the user's current request and the actual code. Keep proposed decisions distinct from agreed decisions and implemented behavior. Surface unresolved conflicts before making dependent changes.
- If the Page cannot be read, state that the knowledge check could not be completed; do not assume it is unchanged. Continue independent work where possible.
- After major work, update the relevant knowledge-base section with the resulting decisions, implementation status, local verification and open handoff items. Preserve Antonio's unrelated updates.
- Philipp owns design; Antonio gathers data. Test changes on localhost before pushing to GitHub.
- The connected repository is `abecic-pr/fra-operations-forecast` (renamed from `aiw26`; confirmed by GitHub during push). Antonio's backend is on `main`; UI work is on `codex/design`. The UI remains in demo mode until live integration is requested. Preserve backend schema 1.0.

# Hackathon working agreement

This is a six-hour FraAlliance / AI Week hackathon project. The user explicitly
wants that constraint respected throughout the project, including future chats.

- Prioritize a working end-to-end demo and measurable progress over architecture.
- Use the current checkout and simple existing tools. Avoid infrastructure,
  abstractions, dependencies, and polish that do not improve the demo.
- The teammate owns UI. Keep backend outputs stable and document changes to JSON.
- Deliver small runnable increments. Test numerical rules, time alignment, missing
  data, and leakage prevention; avoid exhaustive low-value test scaffolding.
- Follow the challenge's 10 kt landing, 15 kt departure, >40 kt crosswind, and
  >30 minute persistence rules for the versioned baseline. Do not silently replace
  these with real-world rules from other sources.
- Keep weather suitability, observed runway use, and official runway status
  separate. Never manufacture operating-history labels or model accuracy.
- Keep observed data, forecasts, and predictions separate. Store provenance,
  timestamps, units, and uncertainty about historical availability.
- Do not present deterministic baseline outputs as calibrated probabilities.
- Preserve other contributors' work. Do not implement UI unless asked.

Research: `docs/izvori-podataka.md` and `docs/podaci-aplikacije.md`.
