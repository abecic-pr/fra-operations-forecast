// The week panel's 3D stage: the recorded week or the wind the reader sets, both written to #week by page.js.
import { startScene } from "/how-it-works/airport-scene.js";

const week = document.getElementById("week");
const stage = week.querySelector(".week-stage");
let visible = false;
new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(stage);

try {
  startScene(stage.querySelector(".airport-map"), stage.querySelector(".wind-field"), stage.querySelector(".airport-labels"), {
    still: matchMedia("(prefers-reduced-motion: reduce)").matches,
    padding: () => ({top: 48, bottom: 24, left: 24, right: 24}),
    paused: () => !visible || document.hidden,
    onReady: () => stage.classList.add("is-ready"),
    control: () => {
      const od = week.dataset.od;
      return {from: Number(week.dataset.windFrom), kt: Number(week.dataset.windKt), od: od === "25" || od === "07" ? od : null, rwy18: week.dataset.rwy18 !== "closed"};
    },
  });
} catch {
  stage.hidden = true; // no WebGL: the readouts and chart still work
}
