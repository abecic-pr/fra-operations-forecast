export type SceneOptions = {
  still: boolean;
  onPhase?: (westbound: boolean) => void;
  onReady: () => void;
  padding: () => { top: number; bottom: number; left: number; right: number };
  paused?: () => boolean;
  /** Drive the scene with a given wind instead of its built-in westbound/eastbound loop. */
  control?: () => { from: number; kt: number; od: '25' | '07' | null; rwy18: boolean };
};
/** Returns a stop function; `refit()` reframes the airport after the caller's overlays change. */
export function startScene(container: HTMLElement, wind: HTMLCanvasElement, labels: HTMLElement, options: SceneOptions): (() => void) & { refit(): void };
