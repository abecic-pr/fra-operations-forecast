// Loaded lazily by StartupScreen so MapLibre stays out of the dashboard bundle.
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';

setWorkerUrl(workerUrl); // MapLibre 6 otherwise looks for its worker beside the bundled module
export { startScene } from '../fra_forecast/presentation/airport-scene.js';
