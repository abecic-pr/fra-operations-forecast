import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import AirportMap from './AirportMap';
import Icon from './Icon';
import { demoWindProvider, formatUtc, frameAt, type WindDataset, type WindProvider } from './data/wind';
import './styles.css';

// Change only this provider after integration is agreed; map/chart components do not fetch.
const provider: WindProvider = demoWindProvider;
function App() {
  const [mode,setMode]=useState<'dashboard'|'map'>(()=>window.location.hash==='#map'?'map':'dashboard');
  const [dataset,setDataset]=useState<WindDataset|null>(null),[error,setError]=useState(false);
  const [hour,setHour]=useState(0),[horizon,setHorizon]=useState(12),[playing,setPlaying]=useState(false);
  useEffect(()=>{const controller=new AbortController();provider.load(controller.signal).then(data=>{if(!controller.signal.aborted)setDataset(data);}).catch(()=>{if(!controller.signal.aborted)setError(true);});return()=>controller.abort();},[]);
  useEffect(()=>{if(!playing)return;const id=window.setInterval(()=>setHour(previous=>previous+.25>horizon?0:previous+.25),400);return()=>clearInterval(id);},[playing,horizon]);
  function changeMode(next:'dashboard'|'map'){setMode(next);window.history.replaceState(null,'',`#${next}`);}
  if(!dataset)return <main className="dashboard" role="status"><h1>{error?'Forecast data unavailable':'Loading wind demonstration…'}</h1></main>;
  const frame=frameAt(dataset,hour),next=dataset.frames.find(p=>Date.parse(p.validTime)>Date.parse(frame.validTime)&&p.weatherState!==frame.weatherState&&p.weatherState!=='unknown');
  const view={dataset,hour,horizon,playing,onHour:setHour,onHorizon:(value:number)=>{setHorizon(value);setHour(previous=>Math.min(previous,value));},onPlaying:setPlaying};
  if(mode==='map')return <AirportMap {...view} onBack={()=>changeMode('dashboard')}/>;
  return <main className="dashboard"><header className="dashboard-header"><a className="wordmark" href="/">FRA<span>Forecast</span></a><nav className="segmented mode-switch" aria-label="App mode"><button className="is-active" aria-pressed="true"><Icon name="grid" size={16}/>Dashboard</button><button aria-pressed="false" onClick={()=>changeMode('map')}><Icon name="map" size={16}/>Map</button></nav><span className="demo-badge">{dataset.mode==='demo'?'Demo data':'Airport forecast'}</span></header><section className="dashboard-intro"><p className="overline">Frankfurt Airport <span>FRA / EDDF</span></p><h1>Runway 18 outlook.</h1><p>Departure wind conditions and the next weather change.<br/>{dataset.mode==='demo'?'Dynamic demo · synthetic weather, not live airport status.':dataset.source}</p></section><section className="overview-cards" aria-label="Runway 18 forecast summary"><article><div className="card-top"><span>Weather suitability</span><Icon name="wind"/></div><h2 className="weather-card-value">{frame.weatherState==='usable'?'Within limits':frame.weatherState==='not_usable'?'Wind limited':'Unknown'}</h2><p>Runway 18 · southbound departures</p><span className="card-caption">{dataset.mode==='demo'?'Simulated conditions':'Weather only'}</span></article><article><div className="card-top"><span>Tailwind</span><Icon name="arrow"/></div><h2>{frame.tailwindKt?.toFixed(1)??'—'}<small> kt</small></h2><p>Departure limit 15 kt</p><span className="card-caption">{formatUtc(frame.validTime)} UTC</span></article><article><div className="card-top"><span>Next weather change</span><Icon name="locate"/></div><h2>{next?formatUtc(next.validTime):'—'}<small> UTC</small></h2><p>First forecast change in wind suitability</p><span className="card-caption">Model confidence unavailable</span></article></section><button className="map-entry" onClick={()=>changeMode('map')}><span className="map-entry-icon"><Icon name="map" size={28}/></span><span><strong>Explore the wind</strong><small>Animated wind field and Runway 18 forecast.</small></span><span className="map-entry-action">Open map<Icon name="arrow" size={18}/></span></button><footer className="dashboard-footer"><span>{dataset.mode==='demo'?'Demo mode · actual data will be connected after integration.':'Airport forecast · not official runway status.'}</span><span>Runway 18 · 48-hour outlook</span></footer></main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
