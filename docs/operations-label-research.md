**Historical operating-direction labels: bounded source check**

**Implementation follow-up, 30 October 2026:** Direct cached HTTP retrieval now
succeeded for the 20 July and 20 October 2026 daily pages, so the earlier DNS/web
failure below is resolved. Following the public measurement form to
`Messwerte.php` exposed 48 explicit direction-title elements for 20 July,
including `Betriebsrichtung West (25)` and `Betriebsrichtung Ost (07)`; the public
16:00-18:00 zoom contained four such indicators. This establishes actual named
direction history overlapping the weather cache, rather than just noise CSV.
It does **not** establish whether each indicator is an instantaneous sample,
interval state, or aggregation, nor a verified timezone/publication timestamp.
The hourly statistics icons alone do not resolve those questions. No target
intervals or exact switch times were manufactured, and these probes were not
accepted into training. Cached source responses and retrieval metadata are in
`data/od-research/raw/`.

The [DFLD help](https://www.dfld.de/Mess/Language/MessHelpG.html) identifies the
post-March-2004 lower direction bar as actual direction based on Fraport data.
The [site's terms](https://www.dfld.de/DFLDimprint.php?L=G) allow private,
noncommercial downloads/copies; redistribution permission was not established.
The bounded probes remain local research and are not included in the demo bundle.
Next acceptance step is a documented timestamp/interval definition and suitable
reuse terms for a historical extract, not a broader scrape of ambiguous labels.

Checked 30 October 2026 for the challenge-completion plan. Planning/research only; no collector, labels, model, or accuracy claim was produced. The user has three hours remaining, so implementation should give label discovery a hard 20-minute gate.

**Finding:** no ready-to-import, timestamped historical 07/25 dataset was verified in this check. DFLD is a concrete lead for independently observed direction, but it is not yet an accepted training source. Current-state pages and forecast products must remain separate from historical outcome labels.

| Source | What was verified | Consequence for implementation |
| --- | --- | --- |
| [UNH current direction and forecast](https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/) | Current 07/25 and a “since” time are explicitly attributed to DFS. The separate prediction uses GFS and eight-hour periods. A data service for automated window control is offered through contact. | Reuse the existing current-state reader. No historical export, archive coverage, or historical publication timestamps were verified. The contact offer is not evidence that a historical dataset is immediately available. |
| [Fraport current direction](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/aktuelles/aktuelle-betriebsrichtung.html) | Official current-direction page and description of DFS setting direction. | No documented timestamped historical download was found in this bounded check. |
| [DFLD help, sections 4.4 and 13](https://www.dfld.de/Mess/Language/MessHelpG.html) | For Frankfurt from March 2004, the lower graph bar is described as actual direction based on Fraport data; the upper bar is wind. Earlier Frankfurt displays calculated direction from wind. | Promising observed-history lead. Verify that any extracted series is the actual-direction bar; never turn wind arrows into operating labels. |
| [DFLD daily page, 20 April 2026](https://www.dfld.de/Mess/StatTag.php?D=20.04.2026&E=D&L=G&R=001&StatNr=137) | Historical hourly table with direction icons and detected overflight/noise entries is accessible. Icon links differ before/after 13:00. | Does not establish exact transition times or an OD export. The existing repository probe found noise/overflight CSV, not OD labels. This date precedes the current ML cache's 30 April start. |
| [OpenSky historical-data documentation](https://openskynetwork.github.io/opensky-api/trino) | Trino access requires application review; research eligibility and private/commercial licensing differ. | A new access application is not a dependable route within three hours. Consider tracks only if suitable authorized data is already available. |

**DFLD verification still needed.** Requests for the same daily view on 20 July and 20 October 2026 were inaccessible through the web tool. A direct standard-library HTTP request failed DNS resolution in this environment. Those failures do not prove the data is absent. No overlap with cached training dates, machine-readable OD records, or reuse rights was established. The source documentation makes DFLD worth a short probe, not an assumed dependency that can already train a model.

**The 20-minute implementation gate (proposed, not completed):**

1. Spend at most 10 minutes inspecting the documented DFLD actual-direction series for two or three dates within the cached 30 April–26 October 2026 issue period. Include a date with a change. Prefer structured values in the public response; do not build an image/OCR reconstruction pipeline.
2. Require explicit 07/25 semantics, timestamps and timezone, unknown/gap handling, a source URL, and evidence of actual observed operations. Resolve local-time/DST ambiguity. Confirm retrieval/reuse conditions and sufficient date/class coverage before any bounded collection.
3. Use the remaining 10 minutes to test normalization into the existing `examples/operations-labels.csv` interval schema and produce a coverage report. Record the real retrieval time; historical publication time remains unknown unless supported. Do not invent `available_at` to make a target label usable as a forecast input.
4. If the gate passes, collect only the overlap needed for chronological train/validation/test partitions. Keep historical labels as targets; permit initial-OD features only when the state was demonstrably known by the forecast issue time. Report source-derived labels as such, not as an independently audited DFS database.
5. If it fails, mark the learned OD and actual-OD evaluation deliverables blocked on labels. Continue useful export, model-card, baseline-bug, and weather-evaluation work. Current snapshot collection can support future evaluation but cannot create months of history during the hackathon.

**Potential human follow-up, not sent:** ask the organizers which public historical direction source they expect participants to use, or request a pointer to an existing DFS/Fraport/UNH export. Specify timestamped 07/25 intervals, timezone, coverage spanning the weather archive, publication information if available, and reuse conditions. The PDF supplies no dataset; this is a clarification/source request, not an assumption that organizers will provide training data.

**Scope limits:** no outreach, paid service, login, broad scrape, bulk backfill, or track-to-runway labeling was attempted. No source found here establishes official RWY18 availability; lack of departures must not become a closure label.
