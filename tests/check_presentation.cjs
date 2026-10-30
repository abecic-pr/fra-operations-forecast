// Run with node tests/check_presentation.cjs; no browser dependency required.
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");

class Element {
  constructor() { this.children = []; this.style = {}; this.textContent = ""; }
  append(...children) { this.children.push(...children); }
  replaceChildren() { this.children = []; }
  setAttribute() {}
  addEventListener() {}
}
const elements = new Map();
const document = {
  querySelectorAll: () => [],
  createElement: () => new Element(),
  getElementById: id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  },
};
const context = vm.createContext({document, AbortSignal, fetch: async () => ({ok: false})});
vm.runInContext(readFileSync(join(__dirname, "../fra_forecast/presentation/page.js"), "utf8"), context);

(async () => {
  await context.loadReport();
  assert.equal(elements.get("results").hidden, true);
  assert.match(elements.get("report-status").textContent, /unavailable/);
  assert.equal(elements.get("retry").hidden, false);

  // Synthetic scores deliberately differ from the matched raw reference.
  const report = {
    model_version: "wind-comparison-v1",
    policy: {winner: "linear_correction", cohort: {wind_rows: 100}, candidates: {
      raw_icon_eu: {metrics: {vector_rmse_kt: 4}},
      linear_correction: {metrics: {vector_rmse_kt: 3}},
    }},
    test: {1: {candidates: {
      raw_icon_eu: {vector_rmse_kt: 99},
      linear_correction: {vector_rmse_kt: 2, samples: 4, raw_on_same_rows: {vector_rmse_kt: 3},
        weather: {probability: {matched_baselines: {challenge_rules: {
          baseline_brier_score: 0, model_brier_score: null, samples: 4,
        }}}}},
    }}},
  };
  context.renderReport(report);
  assert.match(elements.get("selection-summary").textContent, /25.0% lower/);
  const cells = id => elements.get(id).children.map(row => row.children.map(cell => cell.textContent));
  assert.deepEqual(cells("wind-scores"), [
    ["1 h", "3.000", "2.000", "4"],
    ["6 h", "Unavailable", "Unavailable", "Unavailable"],
    ["24 h", "Unavailable", "Unavailable", "Unavailable"],
  ]);
  assert.deepEqual(cells("weather-scores")[0], ["1 h", "0.000000", "Unavailable", "4"]);
  assert.throws(() => context.renderReport({}), /Unsupported/);
  context.fetch = async () => ({ok: true, json: async () => report});
  await context.loadReport();
  assert.equal(elements.get("results").hidden, false);
  assert.equal(elements.get("report-status").hidden, true);
  assert.equal(elements.get("candidate-bars").children.length, 4);
  console.log("Presentation checks passed: matched scores, nulls, missing data, invalid reports and recovery.");
})().catch(error => { console.error(error); process.exitCode = 1; });
