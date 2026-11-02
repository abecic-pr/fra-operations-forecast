// Run with node tests/check_presentation.cjs; no browser dependency required.
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");

const html = readFileSync(join(__dirname, "../fra_forecast/presentation/index.html"), "utf8");
const pattern = html.match(/data-days="([^"]+)"/)[1];
const count = kind => [...pattern].filter(day => day === kind).length;

// The day grid must agree with the figures printed beside it.
assert.equal(pattern.trimStart().length, 183, "30 April to 29 October 2026 inclusive");
assert.equal(pattern.length - pattern.trimStart().length, 3, "Thursday start in Monday-first weeks");
assert.equal(count("."), 1, "25 October is shown as not counted");
assert.equal(count("w") + count("e") + count("c"), 182);
assert.equal(count("c"), 65);
assert.match(html, /<b data-count="65">65<\/b><small>\/182<\/small>/);
assert.match(html, new RegExp(`${count("w")} days westbound all day, ${count("e")} days eastbound all day, ${count("c")} days with at least one change`));

// Every animated figure already holds its final value for no-JS and reduced-motion readers.
for (const [, target, decimals = 0, shown] of html.matchAll(/data-count="([\d.]+)"(?: data-decimals="(\d)")?>([^<]+)</g)) {
  assert.equal(shown, Number(target).toLocaleString("en-GB", {minimumFractionDigits: +decimals}));
}

// The real-week replay must agree with its introduction.
const week = attribute => html.match(new RegExp(`data-${attribute}="([^"]+)"`))[1];
const dirs = [...week("dirs")], kt = week("kt").split(" ").map(Number), deg = week("deg").split(" ").map(Number);
assert.equal(dirs.length, 168);
assert.equal(kt.length, 168);
assert.equal(deg.length, 168);
assert.ok(dirs.every(d => d === "e" || d === "w"));
assert.equal(dirs.filter((d, i) => i && d !== dirs[i - 1]).length, 15);
assert.match(html, /changed direction 15 times/);
assert.equal(Math.max(...kt), 13);
assert.equal(Math.round(kt.reduce((a, b) => a + b) / kt.length), 5);
assert.match(html, /about 5 kt on average, never above 13 kt/);
assert.ok(deg.every(d => d >= 0 && d < 360));
// The simulator's Section 3 baseline must reproduce the brief's worked examples.
const page = readFileSync(join(__dirname, "../fra_forecast/presentation/page.js"), "utf8");
const rules = page.slice(page.indexOf("const component ="), page.indexOf("// The 3D stage"));
const {baseline} = vm.runInNewContext(`${rules}; ({baseline})`);
assert.equal(baseline(90, 20, "25").od, "07", "090°/20 kt: ~19 kt tailwind on 25 forces 07");
assert.equal(baseline(330, 20, "25").rwy18, false, "330°/20 kt: 17.3 kt tailwind closes Runway 18");
assert.equal(baseline(330, 20, "25").od, "25", "330°/20 kt is a headwind on 25");
assert.equal(baseline(160, 45, "25").od, null, "45 kt across 07/25 closes the parallel runways");
assert.equal(baseline(160, 45, "25").rwy18, true);
assert.equal(baseline(70, 5, "25").od, "07", "a persisting small tailwind turns the airport into the wind");
assert.equal(baseline(250, 0, "07").od, "07", "calm keeps the current direction");
console.log("presentation checks passed");
