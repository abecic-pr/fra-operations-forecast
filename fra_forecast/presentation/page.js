"use strict";

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const motion = !reduce && "IntersectionObserver" in window;
if (motion) document.documentElement.classList.add("motion");
const $ = id => document.getElementById(id);
const points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const compassPoint = deg => points[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
// Keep the needle turning the short way round instead of spinning back through 0°.
const turn = (previous, target) => previous + ((((target - previous) % 360) + 540) % 360 - 180);

// One square per local date in Monday-first weeks; spaces pad to Thursday 30 April, "." marks the uncounted clock-change day.
const days = $("days");
[...days.dataset.days].forEach((kind, i) => {
  const day = document.createElement("span");
  day.className = kind === "." ? "gap" : kind === " " ? "pad" : kind;
  day.style.setProperty("--i", i);
  days.append(day);
});

/* Hero: an illustrative wind that swings west → east → west; the parallel runways follow it. */
const scene = $("scene");
const canvas = scene.querySelector("canvas");
const context = canvas.getContext("2d");
const sceneNeedle = scene.querySelector(".needle");
const loop = 16000;
// Wind direction (from, degrees) and speed (kt) through one loop; rotations pass through south, then north.
function sceneWind(ms) {
  const t = ms % loop / 1000, ease = p => p < .5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2;
  if (t < 5) return {from: 250, kt: 12};
  if (t < 8) { const p = ease((t - 5) / 3); return {from: 250 - 180 * p, kt: 12 - 7 * Math.sin(Math.PI * p)}; }
  if (t < 13) return {from: 70, kt: 9};
  const p = ease((t - 13) / 3); return {from: 70 - 180 * p, kt: 9 - 4 * Math.sin(Math.PI * p) + 3 * p};
}
let particles = [], width = 0, height = 0, ratio = 1, needleAngle = 70;
function sizeCanvas() {
  ratio = Math.min(2, devicePixelRatio || 1);
  ({width, height} = scene.getBoundingClientRect());
  canvas.width = width * ratio; canvas.height = height * ratio;
  const count = Math.min(480, Math.round(width * height / 3000));
  particles = Array.from({length: count}, () => ({x: Math.random() * width, y: Math.random() * height, life: Math.random() * 160}));
}
function drawWind(wind, steps) {
  const bearing = (wind.from + 180) * Math.PI / 180, speed = wind.kt * .32;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.lineWidth = 1.1;
  context.strokeStyle = "#ffffff47";
  context.beginPath();
  for (const p of particles) {
    // A gentle swirl so the field reads as air, not as parallel rails.
    const angle = bearing + Math.sin(p.y * .006 + p.x * .002) * .22;
    const dx = Math.sin(angle) * speed * steps, dy = -Math.cos(angle) * speed * steps;
    context.moveTo(p.x, p.y);
    p.x += dx; p.y += dy; p.life -= steps;
    context.lineTo(p.x, p.y);
    if (p.life < 0 || p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) {
      p.x = Math.random() * width; p.y = Math.random() * height; p.life = 80 + Math.random() * 120;
    }
  }
  context.stroke();
}
function showWind(wind) {
  // Simplified illustration: switch once the wind has a clear tailwind component on the current direction.
  const along25 = wind.kt * Math.cos((wind.from - 250) * Math.PI / 180);
  const od = scene.dataset.od;
  if (od === "25" && along25 < -2) scene.dataset.od = "07";
  if (od === "07" && along25 > 2) scene.dataset.od = "25";
  needleAngle = turn(needleAngle, wind.from + 180);
  sceneNeedle.style.setProperty("--to", `${needleAngle}deg`);
  $("scene-wind").textContent = `${compassPoint(wind.from)} · ${Math.round(wind.kt)} kt`;
}
sizeCanvas();
addEventListener("resize", sizeCanvas);
if (motion) {
  let visible = true, clock = 0, last = 0, labelClock = 0;
  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(scene);
  const frame = now => {
    const dt = Math.min(50, now - (last || now)); last = now;
    if (visible && !document.hidden) {
      clock += dt;
      const wind = sceneWind(clock);
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.globalCompositeOperation = "destination-out";
      context.fillStyle = "#00000030";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.globalCompositeOperation = "source-over";
      drawWind(wind, dt / 16.7);
      if (clock - labelClock > 120) { labelClock = clock; showWind(wind); }
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
} else {
  // Reduced motion: one still frame of westerly wind and westbound operation.
  for (let i = 0; i < 6; i++) drawWind({from: 250, kt: 12}, 2);
  showWind({from: 250, kt: 12});
}

/* One real week: readout, chart, playhead and scrubber stay in step. */
const week = $("week");
const dirs = [...week.dataset.dirs];
const degrees = week.dataset.deg.split(" ").map(Number), speeds = week.dataset.kt.split(" ").map(Number);
const start = Date.parse(week.dataset.start);
const local = new Intl.DateTimeFormat("en-GB", {timeZone: "Europe/Berlin", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
const longLocal = new Intl.DateTimeFormat("en-GB", {timeZone: "Europe/Berlin", weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
const label = hour => {
  const part = Object.fromEntries(local.formatToParts(start + hour * 3600e3).map(p => [p.type, p.value]));
  return `${part.weekday} ${part.day} ${part.month} · ${part.hour}:${part.minute}`;
};
const name = kind => kind === "e" ? "07 Eastbound" : "25 Westbound";
const changesBy = dirs.map((kind, i) => dirs.slice(0, i + 1).filter((d, j) => j && d !== dirs[j - 1]).length);
const svgNode = (tag, attributes) => Object.entries(attributes).reduce((node, [key, value]) => (node.setAttribute(key, value), node), document.createElementNS("http://www.w3.org/2000/svg", tag));
$("week-area").setAttribute("d", `M0 30${speeds.map((kt, i) => `L${i + .5} ${30 - Math.min(kt, 15) / 15 * 28}`).join("")}L168 30Z`);
for (let i = 0, from = 0; i <= dirs.length; i++) {
  if (i < dirs.length && dirs[i] === dirs[from]) continue;
  $("week-bands").append(svgNode("rect", {x: from, y: 33, width: i - from + .02, height: 13, class: dirs[from]}));
  from = i;
}
for (let d = 1; d < 7; d++) $("week-days").append(svgNode("line", {x1: d * 24, x2: d * 24, y1: 0, y2: 46}));
$("week-axis").replaceChildren(...Array.from({length: 7}, (_, d) => Object.assign(document.createElement("span"), {textContent: label(d * 24).split(" ").slice(0, 2).join(" ")})));
const scrub = $("week-scrub"), play = $("week-play"), weekNeedle = $("week-needle");
let hour = 0, weekAngle = 0, playing = false, lastStep = 0, autoplayed = false;
function setHour(next) {
  hour = Math.max(0, Math.min(167, next));
  scrub.value = hour;
  week.dataset.od = dirs[hour] === "e" ? "07" : "25";
  $("week-time").textContent = label(hour);
  $("week-od").textContent = name(dirs[hour]);
  $("week-kt").textContent = speeds[hour];
  $("week-from").textContent = `${compassPoint(degrees[hour])} ${degrees[hour]}°`;
  $("week-changes").textContent = changesBy[hour];
  weekAngle = turn(weekAngle, degrees[hour] + 180);
  weekNeedle.style.setProperty("--to", `${weekAngle}deg`);
  $("week-future").setAttribute("x", hour + 1);
  $("week-future").setAttribute("width", 167 - hour);
  $("week-playhead").setAttribute("x1", hour + .5);
  $("week-playhead").setAttribute("x2", hour + .5);
  scrub.setAttribute("aria-valuetext", `${longLocal.format(start + hour * 3600e3)}, ${name(dirs[hour])}, wind ${speeds[hour]} knots`);
}
function setPlaying(next) {
  playing = next;
  const icon = playing ? "#i-pause" : hour >= 167 ? "#i-replay" : "#i-play";
  play.querySelector("use").setAttribute("href", icon);
  play.setAttribute("aria-label", playing ? "Pause" : hour >= 167 ? "Replay the week" : "Play the week");
  if (playing) { lastStep = performance.now(); requestAnimationFrame(advance); }
}
function advance(now) {
  if (!playing) return;
  // About twelve seconds for the whole week.
  if (now - lastStep > 70) { lastStep = now; setHour(hour + 1); }
  if (hour >= 167) return setPlaying(false);
  requestAnimationFrame(advance);
}
play.addEventListener("click", () => {
  if (playing) return setPlaying(false);
  if (hour >= 167) setHour(0);
  setPlaying(true);
});
scrub.addEventListener("input", () => { setPlaying(false); setHour(Number(scrub.value)); });
setHour(0);

/* How it works: draw forecast, then correction, then corrected wind, lighting each step. */
const how = $("how");
const playSteps = () => [1, 2, 3].forEach((step, i) => setTimeout(() => { how.dataset.step = step; }, i * 1300));

if (motion) {
  how.dataset.step = 0;
  const format = (value, decimals) => value.toLocaleString("en-GB", {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
  const countUp = node => {
    const target = Number(node.dataset.count), decimals = Number(node.dataset.decimals || 0);
    const duration = 1600, begin = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - begin) / duration);
      node.textContent = format(target * (1 - Math.pow(2, -10 * t)), decimals);
      if (t < 1) requestAnimationFrame(tick); else node.textContent = format(target, decimals);
    };
    requestAnimationFrame(tick);
    // Never leave a placeholder zero on screen if animation frames are paused.
    setTimeout(() => { node.textContent = format(target, decimals); }, duration + 100);
  };
  // Stagger siblings that enter together, such as a row of tiles.
  for (const group of document.querySelectorAll(".hero-stats, .grid, .status-list")) {
    [...group.children].forEach((child, i) => child.style.setProperty("--delay", `${i * 80}ms`));
  }
  document.querySelectorAll("[data-count]").forEach(node => { node.textContent = format(0, Number(node.dataset.decimals || 0)); });
  const enter = node => {
    node.classList.add("in");
    observer.unobserve(node);
    const delay = parseFloat(getComputedStyle(node).getPropertyValue("--delay")) || 0;
    setTimeout(() => node.querySelectorAll("[data-count]").forEach(countUp), delay + 150);
    if (node === how) setTimeout(playSteps, 400);
    if (node === week && !autoplayed) { autoplayed = true; setTimeout(() => setPlaying(true), 700); }
  };
  const observer = new IntersectionObserver(entries => entries.forEach(entry => entry.isIntersecting && enter(entry.target)), {threshold: 0.2, rootMargin: "0px 0px -6% 0px"});
  const reveals = [...document.querySelectorAll(".reveal")];
  reveals.forEach(node => observer.observe(node));
  // Fallback for first-screen content when observer callbacks are throttled (hidden or background tabs).
  setTimeout(() => reveals.filter(node => !node.classList.contains("in") && node.getBoundingClientRect().top < innerHeight).forEach(enter), 900);
}
