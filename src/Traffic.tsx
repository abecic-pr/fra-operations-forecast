import {useEffect,useMemo,useState} from 'react';
import L from 'leaflet';
import {airportDirection,formatUtc,runwayComponents,type WindView,type WindFrame} from './data/wind';
import {adaptTraffic,demoTraffic,nextMovement,parallelRunways,type ParallelRunway,type TrafficBoard} from './data/traffic';
import {frankfurtTime} from './data/departures';
export type TrafficControl={board:TrafficBoard|null;failed:boolean;preview:boolean;setPreview:(v:boolean)=>void;runway:ParallelRunway;setRunway:(v:ParallelRunway)=>void;now:number};
export function useTraffic(now:number,od:'07'|'25'|null):TrafficControl{
  const [live,setLive]=useState<TrafficBoard|null>(null),[failed,setFailed]=useState(false),[preview,setPreview]=useState(false),[runway,setRunway]=useState<ParallelRunway>('07C/25C');
  useEffect(()=>{const abort=new AbortController();const load=async()=>{try{const r=await fetch('/api/traffic',{signal:abort.signal});if(!r.ok)throw Error();const data=adaptTraffic(await r.json());if(!abort.signal.aborted){setLive(data);setFailed(false);}}catch{if(!abort.signal.aborted)setFailed(true);}};void load();const timer=setInterval(()=>{if(!document.hidden)void load();},60000);return()=>{abort.abort();clearInterval(timer);};},[]);
  const board=useMemo(()=>preview?demoTraffic(now,od):live,[preview,now,od,live]);
  return {board,failed,preview,setPreview,runway,setRunway,now};
}
function sampleContext(view:WindView,traffic:TrafficControl){
  const next=nextMovement(traffic.board,traffic.runway,traffic.now),target=next?Date.parse(next.at):traffic.now;
  const future=view.dataset.frames.filter(f=>Date.parse(f.validTime)>=target),before=view.dataset.frames.filter(f=>Date.parse(f.validTime)<=target).at(-1);
  let samples:WindFrame[]=[];
  if(next){const after=future[0];if(after&&Date.parse(after.validTime)===target)samples=[after];else if(after&&before&&Date.parse(after.validTime)-Date.parse(before.validTime)<=3600000)samples=[before,after];else if(after&&Date.parse(after.validTime)-target<=3600000)samples=[after];}
  else if(view.dataset.currentObservation)samples=[view.dataset.currentObservation];
  return {next,samples,target};
}
function conditions(view:WindView,samples:WindFrame[],operation:'landing'|'departure',end?:string|null){
  const limit=operation==='landing'?10:15;
  const readings=samples.map(frame=>{const reported=frame===view.dataset.currentObservation;const od=end?.startsWith('07')?'07':end?.startsWith('25')?'25':reported?view.dataset.operations?.direction:frame.operatingDirection;return runwayComponents(frame,od==='07'?70:od==='25'?250:null);});
  const exceeded=readings.some(r=>r.tailwind!==null&&r.tailwind>=limit||r.crosswind!==null&&r.crosswind>40||r.gustCrosswind!==null&&r.gustCrosswind>40);
  const complete=readings.length>0&&readings.every(r=>r.tailwind!==null&&r.gustCrosswind!==null);
  const caution=readings.some(r=>r.tailwind!==null&&r.tailwind>=limit*.8||r.gustCrosswind!==null&&r.gustCrosswind>=32);
  const gust=readings.length&&readings.every(r=>r.gustCrosswind!==null)?Math.max(...readings.map(r=>r.gustCrosswind!)):null;
  return {limit,gust,tone:view.connectionError?'unknown':exceeded?'red':!complete?'unknown':caution?'yellow':'green',label:view.connectionError?'Connection lost':exceeded?'Wind limit reached':!complete?'Data incomplete':caution?'Near wind limit':'Within sample limits',tail:readings.length&&readings.every(r=>r.tailwind!==null)?Math.max(...readings.map(r=>r.tailwind!)):null};
}
export function RunwayTrafficSummary({view,traffic,compact=false}:{view:WindView;traffic:TrafficControl;compact?:boolean}){
  const {next,samples}=sampleContext(view,traffic);
  const stale=traffic.board&&traffic.now-Date.parse(traffic.board.generatedAt)>15*60000;
  return <section className={`traffic-summary ${compact?'glass is-compact':''}`} aria-label="Parallel runway movement status">
    <div className="traffic-title"><h2>{compact?'Runway movements':'Landing & departure outlook'}</h2><span>{traffic.preview?'Design preview · simulated aircraft':'Published airport schedule'}</span></div>
    <div className="segmented runway-selector" aria-label="Select parallel runway">{parallelRunways.map(r=><button key={r} aria-pressed={traffic.runway===r} className={traffic.runway===r?'is-active':''} onClick={()=>traffic.setRunway(r)}>{r}</button>)}</div>
    <div className="next-movement"><span>{next?'Next known assigned flight':'Next assigned flight unavailable'}</span><strong>{next?`${next.number} · ${next.operation==='landing'?'Landing':'Departure'}`:stale?'Schedule needs refreshing':'Awaiting runway assignments'}</strong><small>{next?`${next.estimated?'Estimated':'Scheduled'} ${frankfurtTime(next.at)} Frankfurt · tailwind limit ${next.operation==='landing'?10:15} kt`:'Both wind limits remain visible until a next movement is confirmed.'}</small></div>
    <div className="movement-status-grid">{(['landing','departure'] as const).map(operation=>{const state=conditions(view,samples,operation,next?.runwayEnd);return <article key={operation} className={`movement-status tone-${state.tone}`} data-active={next?.operation===operation}><h3>{operation==='landing'?'Landing':'Departure'}{next?.operation===operation&&<span>Next flight</span>}</h3><strong>{state.label}</strong><p>{state.tail===null?'—':state.tail.toFixed(1)} kt tailwind <span>/ &lt;{state.limit} kt</span></p><small>Gust crosswind {state.gust===null?'—':state.gust.toFixed(1)} kt / ≤40 kt</small></article>;})}</div>
    <p className="traffic-sample-note">{next?`Forecast samples: ${samples.length?samples.map(s=>formatUtc(s.validTime)).join(' / ')+' UTC':'unavailable'}. Published board time is a proxy, not touchdown or wheels-off.`:'Showing current wind on the reported airport direction.'} Wind suitability only.{samples.length>1?' Matching endpoints do not prove conditions between samples.':''}</p>
    <div className="segmented traffic-mode" aria-label="Aircraft data mode"><button className={!traffic.preview?'is-active':''} aria-pressed={!traffic.preview} onClick={()=>traffic.setPreview(false)}>Live schedule</button><button className={traffic.preview?'is-active':''} aria-pressed={traffic.preview} onClick={()=>traffic.setPreview(true)}>Design preview</button></div>
  </section>;
}
export default function TrafficOverview({view,traffic,onMap}:{view:WindView;traffic:TrafficControl;onMap:()=>void}){
  const [filter,setFilter]=useState<'all'|'landing'|'departure'>('all'),[search,setSearch]=useState(''),[page,setPage]=useState(0);
  useEffect(()=>setPage(0),[filter,search,traffic.runway,traffic.preview]);
  const all=traffic.board?.flights.filter(f=>Date.parse(f.at)>=traffic.now)??[];
  const rows=all.filter(f=>(filter==='all'||f.operation===filter)&&`${f.number} ${f.airport}`.toLowerCase().includes(search.toLowerCase())&&(f.runway===traffic.runway||f.runway===null));
  return <section className="traffic-overview" aria-label="Parallel runway flights"><RunwayTrafficSummary view={view} traffic={traffic}/><div className="traffic-list"><div className="traffic-list-heading"><div><h2>Upcoming flights</h2><p>{traffic.preview?'Simulated assignments and positions':traffic.failed?'Feed unavailable · last received schedule shown if available':traffic.board?.partial?'Partial airport board · coverage may be incomplete':'Airport passenger board · runway assignments unavailable'}</p></div><button onClick={onMap}>Show on map ↗</button></div><div className="traffic-filters"><div className="segmented">{(['all','landing','departure'] as const).map(f=><button key={f} className={filter===f?'is-active':''} aria-pressed={filter===f} onClick={()=>setFilter(f)}>{f==='all'?'All':f==='landing'?'Landings':'Departures'}</button>)}</div><input type="search" aria-label="Search flights" placeholder="Flight or airport" value={search} onChange={e=>setSearch(e.target.value)}/></div><div className="traffic-table-wrap"><table><thead><tr><th>Flight</th><th>Movement</th><th>Airport</th><th>Board time</th><th>Runway</th></tr></thead><tbody>{rows.slice(page*25,(page+1)*25).map(f=><tr key={f.id}><td><strong>{f.number}</strong></td><td>{f.operation==='landing'?'↘ Landing':'↗ Departure'}</td><td>{f.airport}</td><td>{frankfurtTime(f.at)} <small>{f.estimated?'est.':'sched.'}</small></td><td>{f.runway??'Unassigned'}</td></tr>)}</tbody></table>{!rows.length&&<p className="traffic-empty">{traffic.board?'No matching flights in this snapshot.':'Flight schedule unavailable. The design preview demonstrates the interaction.'}</p>}</div><div className="traffic-pagination"><button disabled={page===0} onClick={()=>setPage(page-1)}>Previous</button><span>{rows.length?`${page*25+1}–${Math.min(rows.length,(page+1)*25)}`:0} of {rows.length}</span><button disabled={(page+1)*25>=rows.length} onClick={()=>setPage(page+1)}>Next</button></div><p className="traffic-sample-note">{rows.length} matching flights · unassigned flights are airport-wide, not confirmed for this runway. {traffic.board?`Snapshot ${frankfurtTime(traffic.board.generatedAt)} Frankfurt.`:''} No live positions are supplied by the public board.</p></div></section>;
}
export function AircraftLayer({map,traffic}:{map:L.Map|null;traffic:TrafficControl}){
  useEffect(()=>{if(!map)return;const group=L.layerGroup().addTo(map);for(const flight of traffic.board?.flights??[]){const p=flight.position;if(!flight.runway||!p||traffic.now-Date.parse(p.at)>120000||Date.parse(p.at)>traffic.now+5000)continue;
    const icon=L.divIcon({className:'traffic-plane',iconSize:[28,28],iconAnchor:[14,14],html:`<svg viewBox="0 0 24 24" style="transform:rotate(${p.heading}deg)"><path d="M12 2l2 7 7 5v2l-7-2v5l2 2v1l-4-1-4 1v-1l2-2v-5l-7 2v-2l7-5z"/></svg>`});
    const label=document.createElement('span');label.textContent=`${flight.number} · ${flight.operation}`;
    L.marker([p.lat,p.lon],{icon,keyboard:false}).bindTooltip(label,{permanent:true,direction:'right'}).addTo(group);
  }return()=>{group.remove();};},[map,traffic.board,traffic.runway,traffic.now,traffic.preview]);return null;
}
export function ParallelForecast({view,traffic}:{view:WindView;traffic:TrafficControl}){
  const next=nextMovement(traffic.board,traffic.runway,traffic.now),limit=next?(next.operation==='landing'?10:15):null,start=Date.parse(view.dataset.generatedAt),end=start+view.horizon*3600000;
  const points=view.dataset.frames.filter(f=>Date.parse(f.validTime)<=end).map(f=>({time:Date.parse(f.validTime),tail:runwayComponents(f,next?.runwayEnd?.startsWith('07')?70:next?.runwayEnd?.startsWith('25')?250:f.operatingDirection==='07'?70:f.operatingDirection==='25'?250:null).tailwind}));
  const max=Math.max(20,...points.map(p=>p.tail??0)),x=(t:number)=>30+(t-start)/(end-start)*290,y=(v:number)=>180-v/max*145;
  return <section className="glass parallel-forecast"><h2>Tailwind forecast · {traffic.runway}</h2><p>{next?`${next.operation==='landing'?'Landing':'Departure'} limit selected for ${next.number}`:'Next movement unknown · both limits shown'}</p><div className="segmented">{[12,24,48].map(h=><button key={h} className={view.horizon===h?'is-active':''} aria-pressed={view.horizon===h} onClick={()=>view.onHorizon(h)}>{h}h</button>)}</div><svg viewBox="0 0 350 215" role="img" aria-label="Parallel runway tailwind forecast and operation limits">{(limit?[limit]:[10,15]).map(l=><g key={l}><line x1="30" x2="320" y1={y(l)} y2={y(l)} stroke={l===10?'#63d6ff':'#ffb688'} strokeDasharray="4 4"/><text x="320" y={y(l)-6} textAnchor="end">{l===10?'Landing':'Departure'} {l} kt</text></g>)}{points.map((p,i)=>{const a=points[i-1];return a&&a.tail!==null&&p.tail!==null&&p.time-a.time<=3600000?<path key={p.time} d={`M${x(a.time)} ${y(a.tail)}L${x(p.time)} ${y(p.tail)}`} stroke="#45a9ff" fill="none" strokeWidth="2.5"/>:null;})}<line x1="30" x2="320" y1="180" y2="180" stroke="#ffffff60"/><text x="30" y="204">{formatUtc(view.dataset.generatedAt)} UTC</text><text x="320" y="204" textAnchor="end">+{view.horizon}h</text></svg><small>Hourly samples · direction from backend forecast · kt</small></section>;
}
