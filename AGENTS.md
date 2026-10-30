# Shared project knowledge

The shared knowledge base for Philipp and Antonio is the **FRA Operations Forecast** Page in the Pencilrec Space:
https://chatgpt.com/space/page_fe8b5e3a0f788191867be7f4e42de933

- Before every major change, read the current Page through the Pages tools and consult relevant linked project Pages for new information. Do not rely solely on an earlier chat snapshot.
- Major changes include app structure, substantial design work, data sources, the shared data contract, forecasting rules, model behavior, dependencies and repository or deployment changes.
- Reconcile new information with the user's current request and the actual code. Keep proposed decisions distinct from agreed decisions and implemented behavior. Surface unresolved conflicts before making dependent changes.
- If the Page cannot be read, state that the knowledge check could not be completed; do not assume it is unchanged. Continue independent work where possible.
- After major work, update the relevant knowledge-base section with the resulting decisions, implementation status, local verification and open handoff items. Preserve Antonio's unrelated updates.
- Philipp owns design; Antonio gathers data. Test changes on localhost before pushing to GitHub.
- The connected repository is `abecic-pr/fra-operations-forecast` (renamed from `aiw26`; confirmed by GitHub during push). Antonio's backend is on `main`; UI work is on `codex/design`. The user has requested live integration: the local UI now uses the live API. Green measurements require source/hash, station, time and QN 2/3 checks, and remain labeled provisional. Support backend schemas 1.0 and 1.1 and never invent historical forecast matches.

# Hackathon working agreement

## Required project knowledge for every chat

The user has designated the FraAlliance challenge PDF as the project's source of
truth for requirements. This applies to every current, resumed, and future chat
working in this repository.

- Before planning, implementing, reviewing, or reporting completion, read
  `docs/challenge/README.md`, the complete text requirements and diagram notes.
- The authoritative original is
  `docs/challenge/AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf` (one page).
  Consult it for wording, examples, or ambiguity; it takes precedence over project
  plans and summaries about challenge requirements. Preserve the original.
- Do not silently narrow the challenge to wind prediction or an agent demo.
  Required: hourly forecasts through 48 h, RWY18 usability probability, airport-wide
  07/25 operating direction with certainty, and the next probable change time.
- Section 3's weather rules are the baseline to beat. Evaluate on unseen data
  using only forecast-time inputs and report 1/6/24 h results. Wind error alone
  does not establish skill against actual operating directions.
- Required submission: code repository, one-page model card covering sources,
  quality and key drivers, and forecasts for the jury test days. Participants
  source their own data and cite every source; the brief provides no dataset.
- Keep the implemented/provisional/missing distinction explicit. Inspect existing
  code and artifacts before proposing duplicate work. Null probabilities and
  rule-only change windows may be honest fallbacks, but are not evidence that all
  required ML deliverables are complete.
- Model comparisons, additional providers, and an AI coordinator are user-requested
  extensions. Prioritize the required forecast/evaluation/submission work within
  the total time budget; keep the extensions in the plan without substituting them
  for the challenge outputs.
- Record explicit later user changes to scope or requirements; never present an
  implementation choice or an inferred interpretation as wording from the PDF.

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
