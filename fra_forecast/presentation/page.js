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

/* Hero: the shared 3D airport scene is started by hero.js. */

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
/* Section 3 baseline for one steady wind, as in fra_forecast.domain: tailwind/crosswind per runway heading. */
const component = (kt, from, heading) => {
  const a = (from - heading) * Math.PI / 180;
  return {tail: Math.max(0, -kt * Math.cos(a)), cross: Math.abs(kt * Math.sin(a))};
};
function baseline(from, kt, current) {
  const w = component(kt, from, 250), e = component(kt, from, 70), south = component(kt, from, 180);
  const result = {w, e, south, rwy18: south.tail < 15 && south.cross <= 40};
  if (w.cross > 40) return {...result, od: null, why: `A ${Math.round(w.cross)} kt crosswind exceeds the 40 kt limit, so the parallel runways close.`};
  const now = current ?? (w.tail <= e.tail ? "25" : "07"), other = now === "25" ? "07" : "25";
  const tail = now === "25" ? w.tail : e.tail;
  if (tail >= 10) return {...result, od: other, why: `A ${Math.round(tail)} kt tailwind on ${now} reaches the 10 kt landing limit, so the airport switches at once to ${other}.`};
  if (tail > 0.5) return {...result, od: other, why: `A ${Math.round(tail)} kt tailwind on ${now} is tolerated for up to 30 minutes. As it persists, the airport turns to ${other} for a headwind.`};
  return {...result, od: now, why: kt < 1 ? `Calm: the airport keeps operating ${now}.` : `Aircraft on ${now} land and take off into a headwind, so nothing changes.`};
}
// The 3D stage (week-scene.js) reads the wind and runway state from these attributes.
function showWind(from, kt, od, rwy18) {
  Object.assign(week.dataset, {windFrom: from, windKt: kt, od: od ?? "closed", rwy18: rwy18 ? "open" : "closed"});
}

function setHour(next) {
  hour = Math.max(0, Math.min(167, next));
  scrub.value = hour;
  if (week.dataset.mode !== "sim") showWind(degrees[hour], speeds[hour], dirs[hour] === "e" ? "07" : "25", baseline(degrees[hour], speeds[hour], null).rwy18);
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
  if (playing && week.dataset.mode === "sim") return setPlaying(false);
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

/* Set the wind yourself: the same stage, driven by the Section 3 baseline instead of the recorded week. */
const dial = $("sim-dial"), arrow = $("sim-arrow"), ktInput = $("sim-kt");
const compassNames = {N: "north", NE: "northeast", E: "east", SE: "southeast", S: "south", SW: "southwest", W: "west", NW: "northwest"};
let simFrom = 250, simOd = "25", arrowAngle = 250;
function gauge(id, kt, limit, over) {
  const row = $(id);
  row.querySelector(".g-value").textContent = `${Math.round(kt)} kt`;
  row.querySelector(".g-fill").style.transform = `scaleX(${Math.min(1, kt / (limit * 1.6))})`;
  row.classList.toggle("is-over", over);
}
function simulate() {
  const kt = Number(ktInput.value), result = baseline(simFrom, kt, simOd);
  simOd = result.od;
  showWind(simFrom, kt, result.od, result.rwy18);
  const point = compassPoint(simFrom), degrees = String(simFrom).padStart(3, "0");
  $("sim-from-out").textContent = `${point} ${degrees}°`;
  dial.setAttribute("aria-valuenow", simFrom);
  dial.setAttribute("aria-valuetext", `From ${compassNames[point]}, ${simFrom} degrees`);
  arrowAngle = turn(arrowAngle, simFrom);
  arrow.style.setProperty("--r", `${arrowAngle}deg`);
  $("sim-kt-out").textContent = `${kt} kt`;
  ktInput.style.setProperty("--v", `${kt / 45 * 100}%`);
  const od = $("sim-od"), next = result.od ? name(result.od === "07" ? "e" : "w") : "Parallel runways closed";
  if (od.textContent !== next) { od.textContent = next; od.classList.remove("swap"); void od.offsetWidth; od.classList.add("swap"); }
  $("sim-why").textContent = result.why + (result.rwy18 ? "" : ` Runway 18 closes: ${Math.round(result.south.tail) >= 15 ? `a ${Math.round(result.south.tail)} kt tailwind reaches its 15 kt departure limit` : `a ${Math.round(result.south.cross)} kt crosswind exceeds 40 kt`}.`);
  gauge("g-25", result.w.tail, 10, result.w.tail >= 10);
  gauge("g-07", result.e.tail, 10, result.e.tail >= 10);
  gauge("g-18", result.south.tail, 15, result.south.tail >= 15);
  gauge("g-cross", result.w.cross, 40, result.w.cross > 40);
  week.querySelectorAll(".sim-presets button").forEach(button =>
    button.setAttribute("aria-pressed", String(Number(button.dataset.from) === simFrom && Number(button.dataset.kt) === kt)));
}
function setFrom(degrees) {
  simFrom = ((Math.round(degrees / 10) * 10) % 360 + 360) % 360;
  simulate();
}
// Drag or click anywhere on the dial; keys step 10° (Page keys 30°).
function fromPointer(event) {
  const box = dial.getBoundingClientRect();
  setFrom(Math.atan2(event.clientX - box.left - box.width / 2, box.top + box.height / 2 - event.clientY) * 180 / Math.PI);
}
dial.addEventListener("pointerdown", event => { dial.setPointerCapture(event.pointerId); dial.classList.add("dragging"); fromPointer(event); });
dial.addEventListener("pointermove", event => { if (dial.hasPointerCapture(event.pointerId)) fromPointer(event); });
dial.addEventListener("pointerup", () => dial.classList.remove("dragging"));
dial.addEventListener("pointercancel", () => dial.classList.remove("dragging"));
dial.addEventListener("keydown", event => {
  const step = {ArrowRight: 10, ArrowUp: 10, ArrowLeft: -10, ArrowDown: -10, PageUp: 30, PageDown: -30}[event.key];
  if (step !== undefined) setFrom(simFrom + step);
  else if (event.key === "Home") setFrom(0);
  else if (event.key === "End") setFrom(350);
  else return;
  event.preventDefault();
});
function setMode(mode) {
  week.dataset.mode = mode;
  week.querySelectorAll(".week-mode button").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.mode === mode)));
  week.querySelector(".week-real").hidden = mode === "sim";
  week.querySelector(".week-sim").hidden = mode !== "sim";
  $("sim-controls").hidden = mode !== "sim";
  if (mode === "sim") { setPlaying(false); simulate(); } else setHour(hour);
  week.dispatchEvent(new Event("modechange")); // the 3D stage reframes around the controls
}
week.querySelectorAll(".week-mode button").forEach(button => button.addEventListener("click", () => setMode(button.dataset.mode)));
week.querySelectorAll(".sim-presets button").forEach(button => button.addEventListener("click", () => {
  ktInput.value = button.dataset.kt; setFrom(Number(button.dataset.from));
}));
ktInput.addEventListener("input", simulate);

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

// Latest hourly check from the online learner; the static text stays if the API is absent.
const describe = w => Number.isFinite(w?.wind_speed_kt)
  ? `${w.wind_speed_kt.toFixed(1)} kt${Number.isFinite(w.wind_from_deg_true) ? ` from ${Math.round(w.wind_from_deg_true)}°` : ", calm"}${Number.isFinite(w.temperature_c) ? `, ${w.temperature_c.toFixed(1)} °C` : ""}`
  : "unavailable";
fetch("/api/online-learning", {cache: "no-store"}).then(r => r.ok ? r.json() : null).then(report => {
  const last = report?.recent?.at(-1);
  if (!last) return;
  const time = new Date(last.valid_time).toLocaleTimeString("en-GB", {timeZone: "Europe/Berlin", hour: "2-digit", minute: "2-digit"});
  $("online-live").textContent = `Latest check, ${time}: one hour earlier we forecast ${describe(last.learned)} (raw model: ${describe(last.raw)}). The airport measured ${describe(last.actual)}. ${report.live.verified_forecasts_all_leads.toLocaleString("en-GB")} forecasts checked so far.`;
}).catch(() => {});
