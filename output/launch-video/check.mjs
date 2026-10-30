import assert from 'node:assert/strict';
import {existsSync, readFileSync, readdirSync} from 'node:fs';

const film = readFileSync('src/LaunchFilm.tsx', 'utf8');
const root = readFileSync('src/Root.tsx', 'utf8');
const scenes = [...film.matchAll(/Sequence name="[^"]+" durationInFrames=\{(\d+)\}/g)].map(m => Number(m[1]));
const overlaps = [...film.matchAll(/linearTiming\(\{durationInFrames: (\d+)\}/g)].map(m => Number(m[1]));
assert.equal(scenes.length, 9);
assert.equal(overlaps.length, scenes.length - 1);
assert.equal(scenes.reduce((a, b) => a + b, 0) - overlaps.reduce((a, b) => a + b, 0), 65 * 30);
assert.match(root, /id="FRA-Launch"[^>]+durationInFrames=\{1950\}[^>]+fps=\{30\}[^>]+width=\{1920\}[^>]+height=\{1080\}/);
for (let i = 0; i < overlaps.length; i++) assert.ok(overlaps[i] < Math.min(scenes[i], scenes[i + 1]));
for (const file of readdirSync('src').filter(f => f.endsWith('.tsx'))) {
  const src = readFileSync(`src/${file}`, 'utf8');
  for (const match of src.matchAll(/(?:staticFile\('([^']+)'\)|src="([^"{}]+\.(?:png|jpg))")/g)) {
    assert.ok(existsSync(`public/${match[1] || match[2]}`), `Missing asset in ${file}: ${match[1] || match[2]}`);
  }
  assert.doesNotMatch(src, /<(?:Audio|h1|h2|p|span)\b/, 'First cut must have no added text or audio');
}
console.log('65 seconds, nine scenes, valid transitions, all assets present, no added text/audio.');
