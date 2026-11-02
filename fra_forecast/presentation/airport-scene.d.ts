export type SceneOptions = {
  still: boolean;
  onPhase: (westbound: boolean) => void;
  onReady: () => void;
  padding: () => { top: number; bottom: number; left: number; right: number };
  paused?: () => boolean;
};
export function startScene(container: HTMLElement, wind: HTMLCanvasElement, labels: HTMLElement, options: SceneOptions): () => void;
