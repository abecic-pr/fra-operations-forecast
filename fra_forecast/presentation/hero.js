// Hero: the same 3D airport as the app's loading screen; the readout follows its wind phases.
import { startScene } from "/how-it-works/airport-scene.js";

const scene = document.getElementById("scene");
const stage = scene.querySelector(".airport-3d");
const needle = scene.querySelector(".needle");
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
let visible = true, angle = 70;
new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(scene);

// Keep the airport clear of the copy and readout panels on wide screens; on phones the stage has its own box.
function padding() {
  if (innerWidth <= 760) return {top: 24, bottom: 24, left: 16, right: 16};
  const copy = scene.querySelector(".scene-copy").getBoundingClientRect(), box = stage.getBoundingClientRect();
  return {top: 110, bottom: 150, left: copy.right - box.left + 32, right: 32};
}

try {
  startScene(stage.querySelector(".airport-map"), stage.querySelector(".wind-field"), stage.querySelector(".airport-labels"), {
    still,
    padding,
    paused: () => !visible || document.hidden,
    onReady: () => stage.classList.add("is-ready"),
    onPhase: westbound => {
      scene.dataset.od = westbound ? "25" : "07";
      // The needle shows where the wind blows to, turning the short way round.
      const target = westbound ? 70 : 250;
      angle += ((((target - angle) % 360) + 540) % 360) - 180;
      needle.style.setProperty("--to", `${angle}deg`);
      document.getElementById("scene-wind").textContent = westbound ? "W · 12 kt" : "E · 9 kt";
    },
  });
} catch {
  stage.hidden = true; // no WebGL: the copy and readout still explain the scene
}
