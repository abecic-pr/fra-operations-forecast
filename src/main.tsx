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
  const frame=frameAt(dataset,hour);
  const view={dataset,hour,horizon,playing,onHour:setHour,onHorizon:(value:number)=>{setHorizon(value);setHour(previous=>Math.min(previous,value));},onPlaying:setPlaying,now,connectionError:error,refreshing,onRefresh:()=>void refreshSources()};
  if(mode==='map')return <AirportMap {...view} traffic={traffic} onBack={()=>changeMode('dashboard')}/>;
  return <main className="dashboard"><header className="dashboard-hero"><h1>Weather<br/>Operations</h1><nav className="segmented mode-switch" aria-label="App mode"><button className="is-active" aria-pressed="true" onClick={()=>changeMode('dashboard')}>Dashboard</button><button aria-pressed="false" onClick={()=>changeMode('map')}>Map view</button></nav><span className="dashboard-location">Frankfurt Airport<span>{frankfurtClock(now)}</span></span></header><div className="dashboard-context"><h2>Airport movement outlook</h2><span>{error?'Connection lost':dataset.mode==='demo'?'Demo weather':'Airport weather'} · {formatUtc(dataset.currentObservation?.validTime??dataset.generatedAt)} UTC</span></div><TrafficOverview view={view} traffic={traffic} onMap={()=>changeMode('map')}/><OperationsOverview view={view} onOpenMap={()=>changeMode('map')}/><WeatherBot selectedTime={frame.validTime} onOpenMap={()=>changeMode('map')}/><button className="map-entry" onClick={()=>changeMode('map')}><span className="map-entry-icon"><Icon name="map" size={28}/></span><span><strong>Explore the wind</strong><small>Aircraft, airport wind and runway forecasts.</small></span><span className="map-entry-action">Open map<Icon name="arrow" size={18}/></span></button><footer className="dashboard-footer"><span>{dataset.mode==='demo'?'Demo mode · actual data will be connected after integration.':'Airport forecast · not official runway status.'}</span><span>Frankfurt · 48-hour outlook</span></footer></main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
