/** Shared UI boundary. Wind directions are FROM true north; all speeds are knots. */
export type WeatherState = 'usable' | 'not_usable' | 'unknown';
export type WindFrame = {
  validTime: string;
  eastKt: number | null;
  northKt: number | null;
  gustKt: number | null;
  tailwindKt: number | null;
  crosswindKt: number | null;
  gustCrosswindKt: number | null;
  weatherState: WeatherState;
  probability: number | null;
};
export type WindDataset = {
  mode: 'demo' | 'live';
  generatedAt: string;
  frames: WindFrame[];
  spatialMode: 'synthetic' | 'uniform-airport';
  source: string;
};
export interface WindProvider { load(signal?: AbortSignal): Promise<WindDataset> }
export const DEPARTURE_LIMIT_KT = 15;
export const CROSSWIND_LIMIT_KT = 40;
export const vectorFromWind = (speedKt: number, fromDegrees: number) => ({
  eastKt: -speedKt * Math.sin(fromDegrees * Math.PI / 180),
  northKt: -speedKt * Math.cos(fromDegrees * Math.PI / 180),
});
export function windFromVector(eastKt: number, northKt: number) {
  return (Math.atan2(-eastKt, -northKt) * 180 / Math.PI + 360) % 360;
}
export function components18(eastKt: number | null, northKt: number | null, gustKt: number | null) {
  if (eastKt === null || northKt === null) return { tailwindKt: null, crosswindKt: null, gustCrosswindKt: null, weatherState: 'unknown' as WeatherState };
  const speed = Math.hypot(eastKt, northKt);
  const tailwindKt = Math.max(0, -northKt);
  const crosswindKt = Math.abs(eastKt);
  const gustCrosswindKt = gustKt === null ? null : speed === 0 ? 0 : crosswindKt / speed * gustKt;
  const weatherState: WeatherState = tailwindKt >= DEPARTURE_LIMIT_KT || crosswindKt > CROSSWIND_LIMIT_KT || (gustCrosswindKt !== null && gustCrosswindKt > CROSSWIND_LIMIT_KT) ? 'not_usable' : gustCrosswindKt === null ? 'unknown' : 'usable';
  return { tailwindKt, crosswindKt, gustCrosswindKt, weatherState };
}
export function demoDataset(now = new Date()): WindDataset {
  const start = now.getTime();
  const frames = Array.from({ length: 49 }, (_, hour) => {
    const speed = 18 + 7 * Math.sin(hour * .39 - .9) + 3 * Math.sin(hour * .9);
    const from = 335 + 32 * Math.sin(hour * .23);
    const vector = vectorFromWind(speed, from);
    const gustKt = speed + 6 + 2 * Math.sin(hour * .4);
    return { validTime: new Date(start + hour * 3600000).toISOString(), ...vector, gustKt, ...components18(vector.eastKt, vector.northKt, gustKt), probability: null };
  });
  return { mode: 'demo', generatedAt: now.toISOString(), frames, spatialMode: 'synthetic', source: 'Synthetic design data · no live weather' };
}
export const demoWindProvider: WindProvider = { load: async () => demoDataset() };
export function frameAt(dataset: WindDataset, hour: number): WindFrame {
  const target = Date.parse(dataset.generatedAt) + Math.max(0, hour) * 3600000;
  const index = dataset.frames.findIndex(frame => Date.parse(frame.validTime) >= target);
  if (index >= 0 && Date.parse(dataset.frames[index].validTime) === target) return dataset.frames[index];
  if (index <= 0) return { validTime: new Date(target).toISOString(), eastKt: null, northKt: null, gustKt: null, tailwindKt: null, crosswindKt: null, gustCrosswindKt: null, weatherState: 'unknown', probability: null };
  const a = dataset.frames[index - 1], b = dataset.frames[index];
  const t = (target - Date.parse(a.validTime)) / (Date.parse(b.validTime) - Date.parse(a.validTime));
  const mix = (a: number | null, b: number | null) => a === null || b === null ? null : a + (b - a) * t;
  const eastKt = mix(a.eastKt, b.eastKt), northKt = mix(a.northKt, b.northKt), gustKt = mix(a.gustKt, b.gustKt);
  // Preserve backend rule states at hourly points; only interpolate between them for playback.
  if (t === 0) return a;
  return { validTime: new Date(new Date(a.validTime).getTime() + (new Date(b.validTime).getTime() - new Date(a.validTime).getTime()) * t).toISOString(), eastKt, northKt, gustKt, ...components18(eastKt, northKt, gustKt), probability: mix(a.probability, b.probability) };
}
export function sampleField(dataset: WindDataset, frame: WindFrame, lat: number, lon: number) {
  if (frame.eastKt === null || frame.northKt === null) return null;
  let east = frame.eastKt, north = frame.northKt;
  if (dataset.spatialMode === 'synthetic') {
    if (lat < 49.85 || lat > 50.2 || lon < 8.3 || lon > 8.85) return null;
    const hour = (Date.parse(frame.validTime) - Date.parse(dataset.generatedAt)) / 3600000;
    // Synthetic variation is anchored at EDDF so chart and map agree at the airport.
    const x = (lon - 8.526) * 40, y = (lat - 50.026) * 55;
    east += 4 * (Math.sin(y + hour * .2) - Math.sin(hour * .2)) + x * .7;
    north += 4 * (Math.sin(x - hour * .15) - Math.sin(-hour * .15)) - y * .6;
  }
  return { east, north, speed: Math.hypot(east, north) };
}

// Antonio's schema 1.0. This adapter is ready for integration; demo remains the active provider.
// Missing data stays null. A single airport wind is never presented as a real spatial grid.
export function adaptBackendSnapshot(input: unknown): WindDataset {
  if (!input || typeof input !== 'object') throw new Error('Expected a forecast snapshot');
  const data = input as Record<string, unknown>;
  if (data.schema_version !== '1.0' || !Array.isArray(data.forecast) || !Number.isFinite(Date.parse(String(data.generated_at)))) throw new Error('Unsupported or invalid forecast schema');
  const numeric = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const frames = data.forecast.map((value: unknown): WindFrame => {
    if (!value || typeof value !== 'object') throw new Error('Invalid forecast point');
    const row = value as Record<string, unknown>;
    if (!Number.isFinite(Date.parse(String(row.valid_time)))) throw new Error('Invalid valid_time');
    const speed = numeric(row.wind_speed_kt), direction = numeric(row.wind_from_deg_true);
    const vector = speed !== null && speed >= 0 && (speed === 0 || (direction !== null && direction >= 0 && direction <= 360)) ? vectorFromWind(speed, direction ?? 0) : { eastKt: null, northKt: null };
    const winds = row.runway_wind as Record<string, Record<string, unknown>> | undefined;
    const runway = winds?.['18'];
    return { validTime: String(row.valid_time), ...vector, gustKt: numeric(row.wind_gust_kt), tailwindKt: numeric(runway?.tailwind_kt), crosswindKt: numeric(runway?.crosswind_kt), gustCrosswindKt: numeric(runway?.gust_crosswind_kt), weatherState: row.rwy18_weather_state === 'usable' || row.rwy18_weather_state === 'not_usable' ? row.rwy18_weather_state : 'unknown', probability: numeric(row.p_rwy18_weather_usable) };
  });
  if (!frames.length || frames.some((frame, index) => index > 0 && Date.parse(frame.validTime) <= Date.parse(frames[index - 1].validTime))) throw new Error('Forecast points must be nonempty and strictly increasing');
  return { mode: 'live', generatedAt: String(data.generated_at), frames, spatialMode: 'uniform-airport', source: 'Airport wind · spatial grid not supplied' };
}
export function backendWindProvider(url = '/api/forecast'): WindProvider {
  return { load: async signal => {
    const response = await fetch(url, { signal });
    if (!response.ok) throw new Error(`Forecast request failed (${response.status})`);
    return adaptBackendSnapshot(await response.json());
  } };
}

export type WindView = {
  dataset: WindDataset;
  hour: number;
  horizon: number;
  playing: boolean;
  onHour: (hour: number) => void;
  onHorizon: (hours: number) => void;
  onPlaying: (playing: boolean) => void;
};
export const formatUtc = (time: string) => new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(time));
