import {examplePlan} from './data/planning';
import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import AirportMap from './AirportMap';
import Icon from './Icon';
import TrafficOverview, {useTraffic} from './Traffic';
import WeatherBot from './WeatherBot';
import OperationsOverview from './OperationsOverview';
import { backendWindProvider, airportDirection, formatUtc, frameAt, type WindDataset, type WindProvider } from './data/wind';
import './styles.css';

// Live backend stays separate from rendering; failed requests never turn into demo weather.
const provider: WindProvider = backendWindProvider();
const frankfurtClock=(at:number)=>new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(new Date(at));
function App() {
  const [planningPreview,setPlanningPreview]=useState(false),[exampleAt,setExampleAt]=useState(Date.now()),[selectedWindow,setSelectedWindow]=useState<string|null>(null),[proposals,setProposals]=useState<string[]>([]);
  const [mapFocus,setMapFocus]=useState<'runway18'|'airport'>('runway18');
  const [mode,setMode]=useState<'dashboard'|'map'>(()=>window.location.hash==='#map'?'map':'dashboard');
  const [dataset,setDataset]=useState<WindDataset|null>(null),[error,setError]=useState(false);
  const [now,setNow]=useState(Date.now()),[refreshing,setRefreshing]=useState(false);
  const [hour,setHour]=useState(0),[horizon,setHorizon]=useState(12),[playing,setPlaying]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();
    const load=()=>provider.load(controller.signal).then(data=>{if(!controller.signal.aborted){setDataset(data);setError(false);}}).catch(()=>{if(!controller.signal.aborted)setError(true);});
    void load();
    const poll=window.setInterval(()=>{if(!document.hidden)void load();},30000);
    const clock=window.setInterval(()=>setNow(Date.now()),1000);
    const refresh=window.setInterval(()=>{if(!document.hidden)void refreshSources(controller.signal);},600000);
    const visible=()=>{if(!document.hidden)void load();};
    document.addEventListener('visibilitychange',visible);
    return()=>{controller.abort();clearInterval(poll);clearInterval(clock);clearInterval(refresh);document.removeEventListener('visibilitychange',visible);};
  },[]);
  async function refreshSources(signal?:AbortSignal){
    setRefreshing(true);
    try {
      const response=await fetch('/api/refresh',{method:'POST',headers:{'X-FRA-Refresh':'1'},signal});
      if(!response.ok&&response.status!==409)throw new Error('Refresh failed');
      const updated=await provider.load(signal);setDataset(updated);setError(false);
    }catch{if(!signal?.aborted)setError(true);}finally{if(!signal?.aborted)setRefreshing(false);}
  }
  useEffect(()=>{if(!playing)return;const id=window.setInterval(()=>setHour(previous=>previous+.25>horizon?0:previous+.25),400);return()=>clearInterval(id);},[playing,horizon]);
  function changeMode(next:'dashboard'|'map'){setMode(next);window.history.replaceState(null,'',`#${next}`);}
  const traffic=useTraffic(now,dataset?airportDirection(dataset,0).direction:null);
  if(!dataset)return <main className="dashboard" role="status"><h1>{error?'Live forecast unavailable':'Loading airport weather…'}</h1><p>{error?'Start the local data API and try again.':'Connecting to Antonio’s data pipeline.'}</p>{error&&<button onClick={()=>window.location.reload()}>Try again</button>}</main>;
  const example=examplePlan(exampleAt),activeDataset=planningPreview?example.dataset:dataset;
  const planning={board:planningPreview?example.board:traffic.board,preview:planningPreview,onPreview:()=>{setPlanningPreview(v=>!v);setExampleAt(Date.now());setHour(0);setPlaying(false);setSelectedWindow(null);setProposals([]);},selected:selectedWindow,onSelect:setSelectedWindow,proposals,onProposal:(id:string)=>setProposals(ids=>ids.includes(id)?ids.filter(v=>v!==id):[...ids,id])};
  const frame=frameAt(activeDataset,hour);
  const view={dataset:activeDataset,hour,horizon,playing,onHour:setHour,onHorizon:(value:number)=>{setHorizon(value);setHour(previous=>Math.min(previous,value));},onPlaying:setPlaying,now,connectionError:planningPreview?false:error,refreshing,onRefresh:()=>void refreshSources()};
  const openRunwayMap=()=>{setMapFocus('runway18');changeMode('map');};
  const openAirportMap=()=>{setMapFocus('airport');changeMode('map');};
  if(mode==='map')return <AirportMap {...view} planning={planning} traffic={traffic} focus={mapFocus} onFocus={setMapFocus} onBack={()=>changeMode('dashboard')}/>;
  return <main className="dashboard"><header className="dashboard-hero"><h1>Weather<br/>Operations</h1><nav className="segmented mode-switch" aria-label="App mode"><button className="is-active" aria-pressed="true" onClick={()=>changeMode('dashboard')}>Dashboard</button><button aria-pressed="false" onClick={openRunwayMap}>Map view</button></nav><span className="dashboard-location">Frankfurt Airport<span>{frankfurtClock(now)}</span></span></header><div className="dashboard-context"><h2>Departure outlook · Runway 18</h2><span>{planningPreview?'Example scenario':error?'Connection lost':dataset.mode==='demo'?'Demo weather':'Airport weather'} · {formatUtc(activeDataset.currentObservation?.validTime??activeDataset.generatedAt)} UTC</span></div><OperationsOverview view={view} planning={planning} onOpenMap={openRunwayMap}/><details className="secondary-traffic"><summary><span>Other runways & flights<small>07L/25R · 07C/25C · 07R/25L</small></span><Icon name="chevron" size={19}/></summary><TrafficOverview view={{...view,dataset}} traffic={traffic} onMap={openAirportMap}/></details><WeatherBot selectedTime={frame.validTime} onOpenMap={openRunwayMap}/><button className="map-entry" onClick={openRunwayMap}><span className="map-entry-icon"><Icon name="map" size={28}/></span><span><strong>Explore the wind</strong><small>Runway 18 wind, measured history and departure outlook.</small></span><span className="map-entry-action">Open map<Icon name="arrow" size={18}/></span></button><footer className="dashboard-footer"><span>{dataset.mode==='demo'?'Demo mode · actual data will be connected after integration.':'Airport forecast · not official runway status.'}</span><span>Frankfurt · 48-hour outlook</span></footer></main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
