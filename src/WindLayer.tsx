import { useEffect, useRef } from 'react';
import type L from 'leaflet';
import { sampleField, type WindDataset, type WindFrame } from './data/wind';

type Vector = { east: number; north: number; speed: number };
const stops = [[0, 48, 155, 191], [10, 77, 179, 154], [20, 224, 191, 93], [30, 219, 115, 125], [40, 153, 104, 190]];
export function windColor(speed: number) {
  const index = Math.min(stops.length - 2, Math.floor(Math.max(0, speed) / 10));
  const a = stops[index], b = stops[index + 1], t = Math.min(1, Math.max(0, (speed - a[0]) / (b[0] - a[0])));
  return a.slice(1).map((value, i) => Math.round(value + (b[i + 1] - value) * t));
}

/** Canvas reads only normalized vectors. The renderer never fetches or invents weather. */
export default function WindLayer({ map, dataset, frame, enabled, animated }: { map: L.Map | null; dataset: WindDataset; frame: WindFrame; enabled: boolean; animated: boolean }) {
  const current = useRef({ dataset, frame });
  const dirty = useRef(true);
  useEffect(() => { current.current = { dataset, frame }; dirty.current = true; }, [dataset, frame]);
  useEffect(() => {
    if (!map || !enabled) return;
    const host = document.createElement('div');
    host.className = 'wind-overlay'; host.setAttribute('aria-hidden', 'true');
    const heat = document.createElement('canvas'), trails = document.createElement('canvas');
    heat.className = 'wind-heat'; trails.className = 'wind-particles';
    host.append(heat, trails); map.getContainer().append(host);
    const ctx = trails.getContext('2d'), heatCtx = heat.getContext('2d');
    if (!ctx || !heatCtx) { host.remove(); return; }
    let width = 0, height = 0, columns = 0, rows = 0;
    let field: (Vector | null)[] = [], animationId = 0, last = 0, moving = false;
    let particles: { x: number; y: number; age: number }[] = [];
    let seed = 18;
    const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const cell = 32;
    const at = (x: number, y: number) => {
      const gx = x / cell, gy = y / cell, ix = Math.floor(gx), iy = Math.floor(gy);
      if (ix < 0 || iy < 0 || ix >= columns - 1 || iy >= rows - 1) return null;
      const a = field[iy * columns + ix], b = field[iy * columns + ix + 1], c = field[(iy + 1) * columns + ix], d = field[(iy + 1) * columns + ix + 1];
      if (!a || !b || !c || !d) return null;
      const tx = gx - ix, ty = gy - iy;
      const blend = (key: 'east' | 'north') => (a[key] * (1-tx) + b[key] * tx) * (1-ty) + (c[key] * (1-tx) + d[key] * tx) * ty;
      const east = blend('east'), north = blend('north');
      return { east, north, speed: Math.hypot(east, north) };
    };
    const resetParticle = (particle: { x: number; y: number; age: number }) => { particle.x = random() * width; particle.y = random() * height; particle.age = Math.floor(random() * 80); };
    function rebuild() {
      if (!ctx || !heatCtx) return;
      const size = map!.getSize(); width = size.x; height = size.y;
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      trails.width = Math.round(width * ratio); trails.height = Math.round(height * ratio);
      trails.style.width = `${width}px`; trails.style.height = `${height}px`; ctx.setTransform(ratio,0,0,ratio,0,0);
      columns = Math.ceil(width / cell) + 1; rows = Math.ceil(height / cell) + 1;
      heat.width = columns; heat.height = rows;
      field = [];
      const pixels = heatCtx.createImageData(columns, rows);
      for (let row = 0; row < rows; row++) for (let col = 0; col < columns; col++) {
        const location = map!.containerPointToLatLng([col * cell, row * cell]);
        const wind = sampleField(current.current.dataset, current.current.frame, location.lat, location.lng);
        field.push(wind);
        if (wind) { const color = windColor(wind.speed), index = (row * columns + col) * 4; pixels.data.set([...color, 112], index); }
      }
      heatCtx.putImageData(pixels, 0, 0);
      heat.style.width = `${(columns - 1) * cell}px`; heat.style.height = `${(rows - 1) * cell}px`;
      particles = Array.from({ length: Math.min(1800, Math.max(200, Math.floor(width * height / 550))) }, () => ({ x: random() * width, y: random() * height, age: random() * 90 }));
      dirty.current = false;
    }
    function draw(delta: number, staticFrame = false) {
      if (!ctx) return;
      ctx.globalCompositeOperation = 'destination-in'; ctx.fillStyle = 'rgba(0,0,0,.91)'; ctx.fillRect(0,0,width,height);
      ctx.globalCompositeOperation = 'source-over'; ctx.strokeStyle = staticFrame ? 'rgba(255,255,244,.65)' : 'rgba(255,255,244,.78)'; ctx.lineWidth = 1; ctx.lineCap = 'round';
      ctx.beginPath();
      for (const particle of particles) {
        const wind = at(particle.x, particle.y);
        if (!wind || wind.speed < .1 || particle.age > 100 || particle.x < 0 || particle.y < 0 || particle.x > width || particle.y > height) { resetParticle(particle); continue; }
        const length = staticFrame ? 6 + wind.speed * .2 : (.55 + Math.min(45, wind.speed) * .055) * delta * 30;
        const nextX = particle.x + wind.east / wind.speed * length, nextY = particle.y - wind.north / wind.speed * length;
        ctx.moveTo(particle.x, particle.y); ctx.lineTo(nextX, nextY);
        particle.x = nextX; particle.y = nextY; particle.age += delta * 30;
      }
      ctx.stroke();
    }
    function tick(now: number) {
      if (document.hidden || moving) { last = now; animationId = requestAnimationFrame(tick); return; }
      if (dirty.current) rebuild();
      if (now - last >= 30) { draw(Math.min(.06, (now-last)/1000)); last = now; }
      animationId = requestAnimationFrame(tick);
    }
    function onStart() { moving = true; ctx!.clearRect(0,0,width,height); heat.style.visibility = 'hidden'; }
    function onEnd() { moving = false; heat.style.visibility = ''; dirty.current = true; if (!animated) { rebuild(); draw(0, true); } }
    const observer = new ResizeObserver(onEnd); observer.observe(map.getContainer());
    map.on('movestart zoomstart', onStart); map.on('moveend zoomend resize', onEnd);
    rebuild();
    if (animated) animationId = requestAnimationFrame(tick); else draw(0, true);
    // In reduced-motion mode, update the still field when the selected forecast changes.
    const stillRefresh = !animated ? window.setInterval(() => { if (dirty.current && !moving) { rebuild(); draw(0, true); } }, 250) : undefined;
    return () => { cancelAnimationFrame(animationId); if (stillRefresh !== undefined) clearInterval(stillRefresh); observer.disconnect(); map.off('movestart zoomstart', onStart); map.off('moveend zoomend resize', onEnd); host.remove(); };
  }, [map, enabled, animated]);
  return null;
}
