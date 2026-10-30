import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { transformWithOxc } from 'vite';
const source = await readFile(new URL('../src/data/wind.ts', import.meta.url), 'utf8');
const { code } = await transformWithOxc(source, 'wind.ts');
const w = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const close = (a,b) => assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
const north = w.vectorFromWind(20,0);
close(north.eastKt,0); close(north.northKt,-20);
assert.equal(w.components18(north.eastKt,north.northKt,25).weatherState,'not_usable');
close(w.components18(0,-15,20).tailwindKt,15);
assert.equal(w.components18(0,-15,20).weatherState,'not_usable');
assert.equal(w.components18(40,0,40).weatherState,'usable');
assert.equal(w.components18(40.01,0,40.01).weatherState,'not_usable');
assert.equal(w.components18(10,0,null).weatherState,'unknown');
assert.equal(w.components18(null,null,20).tailwindKt,null);
close(w.windFromVector(north.eastKt,north.northKt),0);
const demo = w.demoDataset(new Date('2026-10-30T10:00:00Z'));
assert.equal(demo.frames.length,49);
assert.ok(demo.frames.every(frame=>frame.probability===null));
assert.ok(demo.frames.some(frame=>frame.weatherState==='usable'));
assert.ok(demo.frames.some(frame=>frame.weatherState==='not_usable'));
const current = w.frameAt(demo,0), later = w.frameAt(demo,4);
assert.notEqual(current.northKt,later.northKt);
const field = w.sampleField(demo,current,50.026,8.526);
close(field.east,current.eastKt); close(field.north,current.northKt);
assert.equal(w.sampleField(demo,current,0,0),null);
const half = w.frameAt(demo,.5);
close(half.eastKt,(demo.frames[0].eastKt+demo.frames[1].eastKt)/2);
assert.equal(half.validTime,'2026-10-30T10:30:00.000Z');
const payload = {schema_version:'1.0',generated_at:'2026-10-30T10:00:00Z',forecast:[
 {valid_time:'2026-10-30T11:00:00Z',wind_speed_kt:20,wind_from_deg_true:0,wind_gust_kt:25,rwy18_weather_state:'not_usable',runway_wind:{'18':{tailwind_kt:20,crosswind_kt:0,gust_crosswind_kt:0}},p_rwy18_weather_usable:null},
 {valid_time:'2026-10-30T12:00:00Z',wind_speed_kt:null,wind_from_deg_true:null,rwy18_weather_state:'unknown'}
]};
const live = w.adaptBackendSnapshot(payload);
assert.equal(live.mode,'live'); assert.equal(live.spatialMode,'uniform-airport');
assert.equal(live.frames[0].tailwindKt,20); assert.equal(live.frames[0].probability,null);
assert.equal(live.frames[1].eastKt,null); assert.equal(live.frames[1].tailwindKt,null);
assert.equal(w.frameAt(live,0).weatherState,'unknown','Future weather must not be shown as current');
assert.equal(w.frameAt(live,1).tailwindKt,20);
assert.equal(w.frameAt(live,3).weatherState,'unknown','Do not extrapolate missing forecast coverage');
assert.equal(w.frameAt(live,1.5).eastKt,null,'Do not interpolate across missing weather');
assert.throws(()=>w.adaptBackendSnapshot({...payload,schema_version:'2.0'}));
assert.throws(()=>w.adaptBackendSnapshot({...payload,forecast:[...payload.forecast].reverse()}));
assert.throws(()=>w.adaptBackendSnapshot({...payload,forecast:[]}));
console.log('Wind checks passed: direction, thresholds, synchronized demo field, time alignment and backend missing data.');

const measuredInput = {valid_time:'2026-10-30T10:00:00Z',received_at:'2026-10-30T10:05:00Z',tailwind_kt:7,eligible:true,provisional:true,source:'DWD CDC',station_id:'01420',quality_code:'2',source_url:'https://opendata.dwd.de/measurements.zip'};
const measured = w.screenedMeasurements([measuredInput],Date.parse('2026-10-30T11:00:00Z'));
assert.equal(measured.length,1); assert.equal(measured[0].tailwindKt,7);
assert.equal(w.screenedMeasurements([{...measuredInput,quality_code:'1'}],Date.parse('2026-10-30T11:00:00Z')).length,0);
assert.equal(w.screenedMeasurements([{...measuredInput,eligible:false}],Date.parse('2026-10-30T11:00:00Z')).length,0);
assert.equal(w.screenedMeasurements([measuredInput],Date.parse('2026-10-30T09:00:00Z')).length,0);
const issued=w.screenedIssuedForecasts([{valid_time:'2026-10-30T10:00:00Z',issued_at:'2026-10-30T09:00:00Z',tailwind_kt:9}, {valid_time:'2026-10-30T10:00:00Z',issued_at:'2026-10-30T10:01:00Z',tailwind_kt:7}]);
const matches=w.comparisonPairs(measured,issued,Date.parse('2026-10-30T11:00:00Z'));
assert.equal(matches.length,1); assert.equal(matches[0].predicted,9); assert.equal(matches[0].measured,7); assert.equal(matches[0].error,2);
assert.equal(w.comparisonPairs(measured,[],Date.parse('2026-10-30T11:00:00Z')).length,0);
console.log('Measured comparison checks passed: 9 kt forecast versus 7 kt measured, future/unscreened data excluded.');

// Display caution must not alter backend rules or turn unknown data green.
const statusFrame = { ...demo.frames[0], weatherState:'usable', tailwindKt:5, crosswindKt:5, gustCrosswindKt:8 };
assert.equal(w.runwayPresentation(statusFrame).tone,'green');
assert.equal(w.runwayPresentation({...statusFrame,tailwindKt:12}).tone,'yellow');
assert.equal(w.runwayPresentation({...statusFrame,gustCrosswindKt:32}).tone,'yellow');
assert.equal(w.runwayPresentation({...statusFrame,tailwindKt:15}).tone,'red');
assert.equal(w.runwayPresentation({...statusFrame,gustCrosswindKt:40}).tone,'yellow');
assert.equal(w.runwayPresentation({...statusFrame,gustCrosswindKt:40.01}).tone,'red');
assert.equal(w.runwayPresentation({...statusFrame,weatherState:'unknown',gustCrosswindKt:null}).tone,'unknown');
assert.equal(w.runwayPresentation({...statusFrame,weatherState:'unknown',tailwindKt:15,gustCrosswindKt:null}).tone,'red');
assert.equal(w.runwayPresentation(statusFrame,true).tone,'unknown');
console.log('Runway colors passed: caution boundaries, exact limits, missing data and disconnected state.');

const departuresSource = await readFile(new URL('../src/data/departures.ts', import.meta.url), 'utf8');
const departuresCompiled = await transformWithOxc(departuresSource, 'departures.ts');
const departuresAdapter = await import('data:text/javascript;base64,' + Buffer.from(departuresCompiled.code).toString('base64'));
const board = departuresAdapter.adaptDepartures({schema_version:'1.0',generated_at:'2026-10-30T12:00:00Z',source:{status:'partial'},departures:[{flight_id:'sample',flight_number:'EX 123',destination:'Example',scheduled_departure_at:'2026-10-30T13:00:00Z',estimated_departure_at:'2026-10-30T13:20:00Z',assigned_runway:null}]});
assert.equal(board.flights[0].assignedRunway,null);
assert.equal(board.flights[0].at,'2026-10-30T13:20:00Z');
assert.equal(board.flights[0].timeBasis,'Estimated');
assert.equal(board.status,'partial');
assert.equal(departuresAdapter.frankfurtTime('2026-10-30T13:20:00Z'),'14:20');
console.log('Departure checks passed: no invented runway, estimated departure precedence, partial source and Frankfurt time.');

const kpiBase={...demo,mode:'live',generatedAt:'2026-10-30T10:00:00Z',currentObservation:undefined,frames:[
  {...statusFrame,validTime:'2026-10-30T11:00:00Z',eastKt:3,northKt:4},
  {...statusFrame,validTime:'2026-10-30T12:00:00Z',eastKt:-3,northKt:-4},
  {...statusFrame,validTime:'2026-10-30T13:00:00Z',eastKt:null,northKt:null},
  {...statusFrame,validTime:'2026-11-01T11:00:00Z',eastKt:100,northKt:0}]};
const kpis=w.windSummary(kpiBase);
assert.equal(kpis.current,null); assert.equal(kpis.maximum,5); assert.equal(kpis.average,5); assert.equal(kpis.count,2);
assert.equal(w.windSummary({...kpiBase,currentObservation:{...statusFrame,eastKt:0,northKt:8}}).current,8);
assert.equal(w.windSummary({...kpiBase,frames:[]}).average,null);
console.log('Wind KPI checks passed: scalar speeds, missing observation, missing samples and 48-hour bounds.');
