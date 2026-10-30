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
assert.deepEqual(w.adaptBackendSnapshot({...payload,schema_version:'1.1',forecast:payload.forecast.map(row=>({...row,ml:{p_rwy18_weather_usable:.9}}))}),live,'Additive ML fields must not replace baseline values');
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
assert.equal(w.runwayPresentation({...statusFrame,tailwindKt:11}).tone,'yellow');
assert.equal(w.runwayPresentation({...statusFrame,gustCrosswindKt:36}).tone,'yellow');
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

const westWind=w.vectorFromWind(12,70);
const opFrame={...statusFrame,...westWind,gustKt:15,...w.components18(westWind.eastKt,westWind.northKt,15),operatingDirection:'25'};
close(w.runwayComponents(opFrame,250).tailwind,12);
assert.ok(w.runwayComponents(opFrame,250).tailwind>=w.LANDING_LIMIT_KT);
assert.equal(w.departureExceedance(opFrame),null); // RWY18 remains independent of landing limits.
assert.equal(w.departureExceedance({...statusFrame,tailwindKt:15}),'Tailwind ≥15 kt');
assert.equal(w.departureExceedance({...statusFrame,crosswindKt:40,gustCrosswindKt:40}),null);
assert.equal(w.departureExceedance({...statusFrame,gustCrosswindKt:40.01}),'Gust crosswind >40 kt');
const before=Date.parse('2026-10-30T10:00:00Z');
const opData={...kpiBase,frames:[{...statusFrame,validTime:'2026-10-30T09:00:00Z',tailwindKt:20},{...statusFrame,validTime:'2026-10-30T11:00:00Z',tailwindKt:8},{...statusFrame,validTime:'2026-10-30T12:00:00Z',tailwindKt:15}]};
assert.equal(w.operationalOutlook(opData,before).first.time,'2026-10-30T12:00:00Z');
assert.equal(w.operationalOutlook(opData,before).peakSix,15);
assert.equal(w.runwayComponents(undefined,70).tailwind,null);
assert.equal(w.operationalOutlook({...opData,frames:[{...statusFrame,validTime:'2026-10-30T11:00:00Z',gustCrosswindKt:null}]},before).checked,0);
console.log('Operations checks passed: landing 10 kt versus departure 15 kt, crosswind >40 kt, missing data and future-only threshold hours.');
const operationalPayload={...payload,observed_operations:{operating_direction:'25',observed_at:'2026-10-30T10:00:00Z',since:'2026-10-30T09:00:00Z',source:'Test source'},forecast:payload.forecast.map(f=>({...f,operating_direction:'07'})),next_operating_direction_change:{status:'change_expected',latest:'2026-10-30T11:00:00Z'}};
const operationalAdapter=w.adaptBackendSnapshot(operationalPayload);
assert.equal(operationalAdapter.operations.direction,'25');
assert.equal(operationalAdapter.frames[0].operatingDirection,'07');
assert.equal(operationalAdapter.nextDirectionChange.latest,'2026-10-30T11:00:00Z');
// East/west arrows follow authoritative OD, never wind-from; 18 remains south.
const airportData={...demo,operations:{direction:'25',observedAt:demo.generatedAt,since:null,source:'Official report'},frames:demo.frames.map(f=>({...f,operatingDirection:'07',directionBasis:'challenge_rules_raw_weather'}))};
assert.equal(w.airportDirection(airportData,0).heading,250);
assert.equal(w.airportDirection(airportData,1).heading,70);
assert.equal(w.airportDirection(airportData,1).basis,'Weather-rule direction forecast');
assert.equal(w.airportDirection(airportData,0,true).direction,null);
assert.equal(w.airportDirection({...airportData,operations:undefined},0).direction,null);
const ne=[[8.6,50.05],[8.5,50.02]],south=[[8.526,49.99],[8.526,50.04]];
assert.deepEqual(w.movementEndpoints(ne,70),[ne[1],ne[0]]);
assert.deepEqual(w.movementEndpoints(ne,250),ne);
assert.deepEqual(w.movementEndpoints(south,180),[south[1],south[0]]);
const enriched={schema_version:'1.1',generated_at:demo.generatedAt,forecast:[{valid_time:demo.frames[1].validTime,operating_direction:'25',direction_forecast:{operating_direction:'07',basis:'challenge_rules_raw_weather',certainty_score:null}}]};
assert.equal(w.adaptBackendSnapshot(enriched).frames[0].operatingDirection,'07');
assert.equal(w.adaptBackendSnapshot(enriched).frames[0].directionCertainty,null);
console.log('Airport movement direction and 1.1 adapter checks passed.');
const trafficCode=(await transformWithOxc(await readFile(new URL('../src/data/traffic.ts',import.meta.url),'utf8'),'traffic.ts')).code;
const traffic=await import('data:text/javascript;base64,'+Buffer.from(trafficCode).toString('base64'));
const trafficNow=Date.parse('2026-10-30T12:00:00Z');
const flight={id:'LH1',number:'LH 1',operation:'landing',scheduled_at:'2026-10-30T12:10:00Z',assigned_runway:'07L',assignment_status:'unknown'};
const trafficSnapshot={schema_version:'1.0',generated_at:'2026-10-30T12:00:00Z',sources:{arrivals:{status:'available'}},flights:[flight]};
assert.equal(traffic.nextMovement(traffic.adaptTraffic(trafficSnapshot),'07L/25R',trafficNow),null);
flight.assignment_status='confirmed';
assert.equal(traffic.nextMovement(traffic.adaptTraffic(trafficSnapshot),'07L/25R',trafficNow)?.operation,'landing');
assert.equal(traffic.nextMovement(traffic.adaptTraffic(trafficSnapshot),'07L/25R',trafficNow+16*60000),null);
assert.equal(traffic.runwayPair('18'),null);
assert.equal(traffic.runwayPair('25L'),'07R/25L');
assert.equal(w.runwayComponents(demo.frames[0],null).tailwind,null);
assert.equal(traffic.demoTraffic(trafficNow,'25').flights.every(f=>f.position===null||f.position.heading===250),true);
console.log('Traffic checks passed: confirmed-only next flight, stale data, runway 18 exclusion, missing direction, and preview movement.');

assert.equal(traffic.adaptTraffic({...trafficSnapshot,flights:[{...flight,assigned_runway:'18',assignment_status:'confirmed'}]}).flights.length,1);

const windUrl='data:text/javascript;base64,'+Buffer.from(code).toString('base64');
const planningCode=(await transformWithOxc(await readFile(new URL('../src/data/planning.ts',import.meta.url),'utf8'),'planning.ts')).code.replace(/from ["']\.\/wind["']/g,'from '+JSON.stringify(windUrl));
const p=await import('data:text/javascript;base64,'+Buffer.from(planningCode).toString('base64'));
assert.equal(w.runwayPresentation({...statusFrame,tailwindKt:10.99}).tone,'green');
assert.equal(w.runwayPresentation({...statusFrame,gustCrosswindKt:35.99}).tone,'green');
const scenario=p.examplePlan(trafficNow), report=p.forecastWindows(scenario.dataset,trafficNow);
const restriction=report.windows.find(x=>x.kind==='restricted');
assert.equal(restriction.start,trafficNow+120*60000);
assert.equal(restriction.end,trafficNow+150*60000);
assert.equal(restriction.resolution,15);
const reviews=p.flightReviews(scenario.dataset,scenario.board,restriction,trafficNow);
assert.equal(reviews.filter(x=>x.assigned18).length,1);
assert.equal(reviews.filter(x=>!x.assigned18).length,1);
assert.equal(reviews.find(x=>x.assigned18).candidate,'07C');
assert.equal(p.flightReviews(scenario.dataset,{...scenario.board,generatedAt:new Date(trafficNow-16*60000).toISOString()},restriction,trafficNow).length,0);
assert.equal(p.flightReviews(scenario.dataset,{...scenario.board,flights:scenario.board.flights.map(f=>({...f,operation:'landing'}))},restriction,trafficNow).length,0);
const gapDataset={...scenario.dataset,planningFrames:scenario.dataset.planningFrames.filter(f=>Date.parse(f.validTime)!==trafficNow+150*60000)};
assert.equal(p.forecastWindows(gapDataset,trafficNow).windows.find(x=>x.kind==='restricted').end,null);
assert.equal(w.frameAt(gapDataset,2.5).weatherState,'unknown');
assert.equal(p.planningState({...statusFrame,weatherState:'unknown'}),'unknown');
assert.equal(p.centreCandidate({...scenario.dataset,planningFrames:scenario.dataset.planningFrames.map(f=>({...f,gustKt:null}))},trafficNow+130*60000),null);
const hourly={...scenario.dataset,planningFrames:undefined,frames:scenario.dataset.frames.map(f=>({...f,resolutionMinutes:60}))};
assert.equal(p.forecastWindows(hourly,trafficNow).windows.find(x=>x.kind==='restricted').end,trafficNow+180*60000);
console.log('Restriction planning checks passed: 4 kt caution, 30-minute sampled window, assignment screening, stale boards, gaps and hourly precision.');

const directionConflict={...scenario.dataset,frames:scenario.dataset.frames.map(f=>({...f,operatingDirection:'25',directionBasis:'independently_trained_od_model'}))};
assert.equal(w.airportDirection(directionConflict,2).direction,'25','Fine raw weather must not replace the learned airport direction');
assert.equal(p.centreCandidate(directionConflict,trafficNow+130*60000),null,'Do not propose conflicting forecast runway directions');
assert.equal(w.adaptBackendSnapshot(payload).frames[0].resolutionMinutes,60,'Hourly published cadence remains hourly');

const screenedComplete={...measuredInput,valid_time:'2026-10-30T12:00:00Z',received_at:'2026-10-30T12:20:00Z',wind_speed_kt:7,wind_from_deg_true:0,wind_gust_kt:10,gust_from_deg_true:90,gust_quality_code:'2',gust_received_at:'2026-10-30T12:25:00Z',source_sha256:'a'.repeat(64),gust_source_sha256:'b'.repeat(64),gust_source_url:'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/now/10minutenwerte_extrema_wind_01420_now.zip'};
const incompleteCurrent={...demo,currentObservation:{...statusFrame,gustKt:null,gustCrosswindKt:null,weatherState:'unknown'}};
w.applyVerifiedCurrent(incompleteCurrent,screenedComplete,trafficNow+30*60000);
assert.equal(incompleteCurrent.currentObservation.weatherState,'usable');
assert.equal(incompleteCurrent.currentObservation.gustCrosswindKt,10);
close(w.runwayComponents(incompleteCurrent.currentObservation,180).gustCrosswind,10);
assert.equal(incompleteCurrent.currentObservationSource,'DWD 01420 · checked provisional');
for(const patch of [{gust_quality_code:'1'},{gust_source_sha256:'bad'},{gust_received_at:'2026-10-30T13:00:00Z'},{valid_time:'2026-10-30T10:00:00Z'}]){
 const d={...demo,currentObservation:{...statusFrame,gustKt:null,gustCrosswindKt:null,weatherState:'unknown'}};
 w.applyVerifiedCurrent(d,{...screenedComplete,...patch},trafficNow+30*60000);
 assert.equal(d.currentObservation.weatherState,'unknown');
}
const newerRed={...demo,currentObservation:{...statusFrame,tailwindKt:16,weatherState:'not_usable'}};
w.applyVerifiedCurrent(newerRed,screenedComplete,trafficNow+30*60000);
assert.equal(newerRed.currentObservation.tailwindKt,16,'Older complete wind must not hide a newer known exceedance');
assert.equal(w.runwayPresentation({...statusFrame,gustKt:null,gustCrosswindKt:null,weatherState:'unknown'}).label,'Gusts not reported');
console.log('Complete observation checks passed: separate source/quality screening, same interval, freshness, actual gust direction and newer hazard precedence.');

const directionCode=(await transformWithOxc(await readFile(new URL('../src/data/direction.ts',import.meta.url),'utf8'),'direction.ts')).code.replace(/from ["']\.\/wind["']/g,'from '+JSON.stringify(windUrl));
const dOutlook=await import('data:text/javascript;base64,'+Buffer.from(directionCode).toString('base64'));
const switchData=dOutlook.directionExample(trafficNow);
const directionRows=dOutlook.directionRows(switchData,12,trafficNow);
assert.equal(directionRows.length,13);
assert.deepEqual(directionRows.filter(r=>r.change).map(r=>r.hour),[3,8]);
const eastConfig=dOutlook.runwayConfiguration('07'),westConfig=dOutlook.runwayConfiguration('25');
assert.deepEqual(eastConfig.map(r=>r.end),['07L','07R','07C','18']);
assert.deepEqual(westConfig.map(r=>r.end),['25R','25L','25C','18']);
assert.deepEqual(westConfig.map(r=>r.heading),[250,250,250,180]);
assert.equal(westConfig.find(r=>r.ref==='18').operation,'Departure');
assert.equal(directionRows[3].flow.direction,'25');
assert.equal(directionRows[3].wind.label,'250° WSW');
assert.equal(w.airportDirection(switchData,directionRows[3].hour).direction,'25');
assert.equal(dOutlook.windBearing({...statusFrame,eastKt:0,northKt:0}).label,'Calm');
assert.equal(dOutlook.windBearing({...statusFrame,eastKt:null}).degrees,null);
const missingFlow={...switchData,frames:switchData.frames.map(f=>({...f,operatingDirection:null}))};
assert.equal(dOutlook.directionRows(missingFlow,12,trafficNow).slice(1).every(r=>r.runways.slice(0,3).every(x=>x.end===null)&&r.runways[3].end==='18'),true);
assert.equal(dOutlook.directionRows(switchData,12,trafficNow,true).every(r=>r.flow.direction===null),true);
assert.equal(dOutlook.directionRows(switchData,48,trafficNow).length,49);
assert.equal(dOutlook.directionRows(switchData,6,trafficNow+2*3600000).filter(r=>!r.current).length,4);
const delayedSwitch={...switchData,frames:switchData.frames.map(f=>({...f,operatingDirection:'07'}))};
assert.equal(dOutlook.directionRows(delayedSwitch,12,trafficNow).find(r=>r.hour===3).flow.direction,'07','Wind change alone must not bypass the backend persistence/airport direction');
console.log('Direction outlook passed: all-runway switches, fixed southbound 18, wind FROM bearings, calm/missing data, horizons and shared airport selection.');
// A complete zero forecast must stay distinct from partial or absent weather/direction.
const headwindForecast={...demo,frames:demo.frames.map(f=>({...f,...w.vectorFromWind(8,70),operatingDirection:'07'}))};
for(const horizon of [12,24,48]){
  const outlook=w.parallelTailwindForecast(headwindForecast,horizon);
  assert.equal(outlook.count,horizon);
  assert.equal(outlook.complete,true);
  assert.equal(outlook.peak,0);
}
close(w.parallelTailwindForecast(headwindForecast,12,'25R').peak,8);
assert.equal(w.parallelTailwindForecast({...headwindForecast,generatedAt:'2026-10-30T10:26:00Z'},12).count,12);
const partial=w.parallelTailwindForecast({...headwindForecast,frames:headwindForecast.frames.map((f,i)=>i===2?{...f,eastKt:null}:f)},12);
assert.equal(partial.count,11);
assert.equal(partial.complete,false);
assert.equal(partial.points[1].tail,null);
assert.equal(w.parallelTailwindForecast({...headwindForecast,frames:headwindForecast.frames.filter((_,i)=>i!==2)},12).complete,false);
const noDirection={...headwindForecast,frames:headwindForecast.frames.map(f=>({...f,operatingDirection:null}))};
assert.equal(w.parallelTailwindForecast(noDirection,12).peak,null);
assert.equal(w.parallelTailwindForecast(noDirection,12,'07L').complete,true);
assert.equal(w.parallelTailwindForecast({...headwindForecast,frames:[]},12).peak,null);
console.log('Parallel forecast checks passed: zero/headwind, assigned direction, horizons and missing coverage.');

assert.equal(dOutlook.directionRows(switchData,12,trafficNow-500).length,13,'A newly activated example must not duplicate its time-zero observation as a forecast');
