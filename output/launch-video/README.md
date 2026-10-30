# Frankfurt launch film

65-second silent animated first cut, 1920 × 1080 at 30 fps. Created with the video, promo-video, Remotion and built-in image-generation skills. The user chose generated cinematic stills after the available video-generation connectors were reported disabled by the workspace administrator.

The film follows a passenger-window departure, a controller consulting the actual app, a product reveal, Runway 18 takeoff, a second aircraft approaching, the previously shown direction forecast, and touchdown. All nine scenes have editable Remotion timelines. There are no added titles, captions, voiceover or music. The real interface's text and source credits remain visible.

## Preview

```sh
cd output/launch-video
npm ci
npm run dev
```

Open http://localhost:5190/FRA-Launch. Press Space to play and F for the fullscreen preview. The preview is local to this computer. Select a scene in the Scenes folder to edit its timing or framing independently.

## Assets and provenance

- `public/cabin.png`, `tower.png`, `departure.png`, `approach.png`, `arrival.png`: generated photographic illustrations. Camera movement is animated over still images; these are not moving aircraft footage or records of real flights. Frankfurt scenery is illustrative, not verified airport geography. Generation prompts are in `image-prompts.json`.
- `public/app-dashboard.jpg`: actual localhost dashboard capture, 30 October 2026, approximately 14:32 UTC. Current observations and the selected future forecast remain separate; missing current gust data stays visible.
- `public/app-airport-map.jpg`: full desktop map capture at approximately 14:36 UTC, forecast issued 14:30 UTC, selected +1 hour / 15:30 UTC and a 48-hour chart. The tower scene uses the same capture projected into the photographed monitor.
- `public/app-forecast-chart.jpg`: complete chart panel cropped directly from the same app view. Green is checked provisional measured history; blue is forecast. No invented accuracy or confidence is added.
- `public/app-direction.jpg`: actual learned-direction card, selected 15:30 UTC. The same image appears before departure and again before touchdown. It describes operating direction, not an assigned runway for a real flight.
- The full map retains its OpenStreetMap and Esri/Vantor/Earthstar source credits. Source URLs are recorded in the parent repository's `public/data/README.md`.

The illustrated flights are a narrative demonstration. App screenshots do not establish operational clearance, individual runway assignment, calibrated certainty, or model performance.

## Checks

```sh
npm run check
npm run lint
npm run build
```

The self-check verifies the nine-scene timeline, transition overlaps, 1,950 total frames, all referenced assets, and absence of added text/audio elements. ESLint, TypeScript and the Remotion bundle are checked separately. Browser review covers the composition and playback.

Remotion Studio's dependency tree reports a transitive Zod resource-exhaustion advisory. No dependency downgrade or production-app dependency changes were made; the editor is intended for this local trusted project.

## Handoff

This is an editable preview; no final MP4 export, publication, sound mix or real footage replacement has been performed. Future moving footage can replace the five still assets while retaining the app sequence. Source files and dependencies are isolated here; the airport application and backend contracts were not edited for this film.
