# Data-state audit — 30 October 2026

The existing design was confirmed on main at `0a6830297c488fe1893e3e3ce1cdda04ba692c2c` before these changes. The user subsequently explicitly requested merging this review branch into main on 30 October 2026. The integration preserves the newer parallel-tailwind chart and both sets of regression checks.

| Area | Evidence in the inspected local snapshot | Treatment |
| --- | --- | --- |
| Latest EDDF report | 14:20 UTC, 7 kt from 070°, gust absent | Omission remains absent, never zero; explicit “Gusts not reported” |
| Complete DWD observation | 13:50 UTC, station 01420, mean 5.44 kt, gust 8.75 kt; independent mean/gust QN 2 | May resolve current wind from the complete observation, labeled source, time and provisional |
| Hourly forecast | 48/48 samples usable | Keep the full hourly forecast |
| Native planning timeline | 188 samples, 3 lack gusts at 12:15/12:30/12:45 UTC on 1 November | Expose partial coverage; never interpolate a closure/reopening through missing inputs |
| Airport direction | Reported OD07 from UNH/DFS | Existing reported-versus-predicted distinction retained |
| Flight board | 2,032 records; all assignment_status=unavailable | Awaiting runway assignments; no invented allocation or affected-flight total |
| Official runway status/capacity | Not supplied | Wind suitability cannot establish official opening or clearance |
| Model certainty | Baseline probabilities absent, learned probabilities uncalibrated | Preserve provenance and limitations, never substitute 100% |

Verification now independently checks original DWD mean and gust response hashes, official source URLs, HTTP success, station 01420, valid/received times and QN 2/3. Only matching observation intervals are paired. `GET /api/verification` adds `latest_complete_observation`; old fields stay intact. A complete observation must be at most 90 minutes old and actually received before use. Actual gust direction is retained for runway components. A newer known red/yellow or complete observation is never replaced with an older green observation. No METAR measurement is silently completed using another source's gust.

The UI replaces vague “unknown” headings with specific data states, and labels the complete-observation source and time. Internal null/unknown semantics remain where evidence is absent; removing those would manufacture runway safety, assignments or model confidence. Missing official data still needs Antonio’s source integration.
