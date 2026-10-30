**FraAlliance challenge: required project knowledge**

The user designated the [original one-page PDF](AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf) as the source of truth for this project's challenge requirements on 30 October 2026. Every chat working in this repository must read this file before work, as required by `AGENTS.md`. If this transcription or an implementation plan differs from the PDF, consult the PDF and correct the derivative document.

The repository PDF is an unchanged copy of the user-supplied document. SHA-256: `8413a1f3b1930d6bd620690ba5e344266065f58fc921c76495872967af5fa184`.

**Brief text: typography and line wrapping normalized**

AI Week Hackathon 2026. Public. FraAlliance, October 2026.

Frankfurt Airport Operating Direction Forecast.

Venue: AI Week 2026, Frankfurt. Date: 30 Oct 2026. Format: one day, approximately six hours build time.

**1. The challenge**

At Frankfurt Airport, the wind mainly determines in which direction aircraft take off and land: shifting winds force an airport-wide change of operating direction, while strong northerly winds (e.g. from the Taunus) close Runway 18 (only used for departures). Your mission: build a machine-learning model that forecasts (1) whether departures are possible on RWY 18 and (2) which operating direction is in use.

**2. Runway system**

- Frankfurt Airport has four runways: two (mainly) for landings (07L/25R Northwest, 07R/25L South) and two for departures (07C/25C Centre, 18 West).
- The 07/25 runways can be used in both directions, but the operating direction (OD) is set airport-wide: when it changes, all runways switch at the same time. Mixed directions are not possible.
- OD 25: departures and landings towards the west (250 degrees true). OD 07: towards the east (070 degrees true). Runway 18 West: departures to the south (180 degrees true), used in both OD.

Schematic notes: T1 means Terminal 1; the drawing is not to scale. It marks north, Taunus to the northwest and wind from N/NW; the three 07/25 runways share the OD, while RWY18 remains southbound in either OD. The diagram distinguishes departure and landing runways and take-off directions.

**3. Decision rules**

A. Wind direction and tailwind component:

- Only the part blowing exactly from behind counts as tailwind. This tailwind component must stay below 15 kt for departures and below 10 kt for landings.
- Crosswinds greater than 40 kt, including gusts, force a runway closure.
- Example, 20 kt wind: 30 degrees off straight behind gives 17.3 kt, not permitted; 45 degrees off gives 14.1 kt, permitted.

B. Operating direction (07/25):

- Headwind is always preferred.
- Landings decide the OD: a tailwind component greater than or equal to 10 kt on the landing runways forces an immediate change of OD.
- Persistence: a small tailwind, always below 10 kt, is accepted for short periods up to 30 minutes to avoid frequent changes; if it persists longer, the OD switches to the headwind direction.
- Example: 090 degrees / 20 kt gives approximately 19 kt tailwind on 25, so use OD 07.

C. Runway 18:

- Departure runway only, take-offs only towards the south (180 degrees true).
- Tailwind greater than or equal to 15 kt (wind from the north) means no take-off on 18, so departures only via the Centre runway (07C/25C).
- Example: 330 degrees / 20 kt gives 17.3 kt tailwind, so Runway 18 is closed.

**4. Deliverables**

1. Machine-learning forecast model: for every hour up to t+[48] h, predict the probability of RWY18 usability as well as the operating direction (25/07) with a certainty score and the next probable change time. Section 3 applied to a weather forecast is only the baseline; beat it.
2. Self-sourced data: no dataset is provided; each participant finds and combines suitable public data (e.g. METAR EDDF, weather-model forecasts, historical operating directions) and cites every source.
3. Model quality: show how good the model is; test it on data it was not trained on, using only data available at forecast time, and report results for forecasts 1 h, 6 h, and 24 h ahead.
4. Submission at the end of the day: code repository, one-page model card (data sources, model quality, key drivers of the forecast), forecasts for the jury test days. The forecasts are compared with the operating directions actually flown.

**Project interpretations and unresolved details, separate from the brief**

- The 14.1 kt example is permitted under the 15 kt departure limit, not the 10 kt landing limit. Apply the explicit threshold for each operation.
- Exactly 10 kt landing tailwind forces an immediate OD change; exactly 15 kt prevents departure; exactly 40 kt crosswind does not exceed the stated crosswind limit. Exactly 30 minutes of sub-10 kt tailwind does not yet meet the strictly longer-than-30-minute switch condition.
- Model RWY18 wind suitability separately from actual runway use and official availability. No departures is not proof of closure. Confirm the jury's precise RWY18 target interpretation instead of silently relabeling weather suitability as official status.
- The brief does not give jury test dates, forecast issue times, file schema, exact scoring metric, certainty-score definition, or how to score intervals with direction changes. Obtain those details from the organizers; do not invent them or a supplied training dataset.
- Do not manufacture historical operations labels, calibrated confidence, model improvement, or minute-level precision from hourly data. Missing evidence means a disclosed incomplete deliverable, not an exemption from the requirement.
- Six hours is the whole-project build budget. UI remains owned by the teammate under the working agreement. Additional data sources, model comparisons, and the AI agent are user-requested extensions, not PDF deliverables.

Implementation status belongs in the [implementation plan](../model-comparison-implementation-plan.md) and evaluation documents, not in this source transcription. Recheck the code and artifacts before relying on a status report.
