# Shared project knowledge

The shared knowledge base for Philipp and Antonio is the **FRA Operations Forecast** Page in the Pencilrec Space:
https://chatgpt.com/space/page_fe8b5e3a0f788191867be7f4e42de933

- Before every major change, read the current Page through the Pages tools and consult relevant linked project Pages for new information. Do not rely solely on an earlier chat snapshot.
- Major changes include app structure, substantial design work, data sources, the shared data contract, forecasting rules, model behavior, dependencies and repository or deployment changes.
- Reconcile new information with the user's current request and the actual code. Keep proposed decisions distinct from agreed decisions and implemented behavior. Surface unresolved conflicts before making dependent changes.
- If the Page cannot be read, state that the knowledge check could not be completed; do not assume it is unchanged. Continue independent work where possible.
- After major work, update the relevant knowledge-base section with the resulting decisions, implementation status, local verification and open handoff items. Preserve Antonio's unrelated updates.
- Philipp owns design; Antonio gathers data. Test changes on localhost before pushing to GitHub.
- The local design remote is currently `abecic-pr/aiw26`; the shared Page also references `abecic-pr/fra-operations-forecast`. Resolve this discrepancy before combining the repositories; do not silently change the remote.
