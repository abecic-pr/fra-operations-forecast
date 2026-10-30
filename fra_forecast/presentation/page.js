"use strict";

const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectStep(tab) {
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute("aria-controls")).hidden = !selected;
  }
}
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectStep(tab));
  tab.addEventListener("keydown", event => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    selectStep(tabs[next]);
    tabs[next].focus();
  });
});

const labels = {raw_icon_eu: "Raw ICON-EU", linear_correction: "Ridge correction", boosting_correction: "Gradient boosting", equal_blend: "Equal blend"};
const byId = id => document.getElementById(id);
const number = (value, digits = 3) => Number.isFinite(value) ? value.toFixed(digits) : "Unavailable";
const count = value => Number.isInteger(value) && value >= 0 ? value.toLocaleString("en-GB") : "Unavailable";

function appendRow(target, values) {
  const row = document.createElement("tr");
  for (const [index, value] of values.entries()) {
    const cell = document.createElement(index === 0 ? "th" : "td");
    if (index === 0) cell.scope = "row";
    cell.textContent = value;
    row.append(cell);
  }
  target.append(row);
}

function renderReport(report) {
  const winner = report?.policy?.winner;
  const candidates = report?.policy?.candidates;
  if (report?.model_version !== "wind-comparison-v1" || !labels[winner] || !candidates?.[winner]?.metrics || !report.test) {
    throw new Error("Unsupported or incomplete comparison report");
  }
  byId("winner-title").textContent = `${labels[winner]} selected`;
  const raw = candidates.raw_icon_eu?.metrics?.vector_rmse_kt;
  const selected = candidates[winner].metrics.vector_rmse_kt;
  const change = Number.isFinite(raw) && raw > 0 && Number.isFinite(selected) ? (raw - selected) / raw * 100 : null;
  byId("selection-summary").textContent = change !== null
    ? `${number(raw)} → ${number(selected)} kt. ${number(Math.abs(change), 1)}% ${change >= 0 ? "lower" : "higher"} validation wind-vector error across ${count(report.policy.cohort?.wind_rows)} matched cases.`
    : "Validation wind-vector error is unavailable in this report.";

  byId("candidate-bars").replaceChildren();
  const maximum = Math.max(1, ...Object.values(candidates).map(c => Number.isFinite(c?.metrics?.vector_rmse_kt) ? c.metrics.vector_rmse_kt : 0));
  for (const [name, label] of Object.entries(labels)) {
    const error = candidates[name]?.metrics?.vector_rmse_kt;
    const item = document.createElement("div");
    item.className = `candidate${name === winner ? " selected" : ""}`;
    const heading = document.createElement("div");
    heading.className = "bar-label";
    const title = document.createElement("span");
    title.textContent = label + (name === winner ? " · selected" : "");
    const value = document.createElement("strong");
    value.textContent = Number.isFinite(error) ? `${number(error)} kt` : "Unavailable";
    heading.append(title, value);
    const track = document.createElement("div");
    track.className = "bar-track";
    track.setAttribute("aria-hidden", "true");
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.width = `${Number.isFinite(error) ? Math.max(0, error) / maximum * 100 : 0}%`;
    track.append(bar);
    item.append(heading, track);
    byId("candidate-bars").append(item);
  }
  byId("wind-scores").replaceChildren();
  byId("weather-scores").replaceChildren();
  for (const horizon of [1, 6, 24]) {
    const scores = report.test[horizon]?.candidates;
    const chosen = scores?.[winner];
    // Compare against the raw score on this candidate's exact matched rows.
    appendRow(byId("wind-scores"), [`${horizon} h`, number(chosen?.raw_on_same_rows?.vector_rmse_kt), number(chosen?.vector_rmse_kt), count(chosen?.samples)]);
    const matched = chosen?.weather?.probability?.matched_baselines?.challenge_rules;
    appendRow(byId("weather-scores"), [`${horizon} h`, number(matched?.baseline_brier_score, 6), number(matched?.model_brier_score, 6), count(matched?.samples)]);
  }
  const probability = report.test.all_1_to_48h?.candidates?.[winner]?.weather?.probability;
  byId("probability-summary").textContent = probability
    ? `Across 1–48 hours, the selected probability Brier score is ${number(probability.brier_score, 6)} versus ${number(probability.always_usable_brier_score, 6)} for always predicting usable weather. ${count(probability.adverse_weather_samples)} adverse forecast cases represent ${count(probability.unique_adverse_valid_times)} distinct adverse target time(s).`
    : "Probability metrics are unavailable in this saved report.";
  byId("report-provenance").textContent = `Saved experiment: ${report.experiment_id || "Unavailable"}. Trained: ${report.trained_at || "Unavailable"}. Test status: ${report.test_status || "Unavailable"}. Source: /api/model-comparison.`;
}

async function loadReport() {
  byId("results").hidden = true;
  byId("retry").hidden = true;
  byId("report-status").hidden = false;
  byId("report-status").textContent = "Loading the saved evaluation…";
  try {
    const response = await fetch("/api/model-comparison", {cache: "no-store", signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error("Comparison unavailable");
    renderReport(await response.json());
    byId("report-status").hidden = true;
    byId("results").hidden = false;
  } catch {
    byId("report-status").textContent = "Saved evaluation unavailable. The pipeline explanation still works. Restore the comparison artifacts or run compare-models, then retry; no example scores are substituted.";
    byId("retry").hidden = false;
  }
}
byId("retry").addEventListener("click", loadReport);
loadReport();
