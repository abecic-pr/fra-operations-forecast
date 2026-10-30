import {forecastWindows,flightReviews} from './data/planning';
import RunwayPlan,{type PlanningControl} from './RunwayPlan';
import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import type { FeatureCollection, Geometry } from 'geojson';
import Icon from './Icon';
import {AircraftLayer, RunwayTrafficSummary, ParallelForecast, type TrafficControl} from './Traffic';
import WindLayer from './WindLayer';
import WindForecast from './WindForecast';
import { AirportDirectionLayer, DirectionBadge } from './AirportDirection';
import { formatUtc, frameAt, runwayPresentation, windFromVector, type WindView } from './data/wind';
import 'leaflet/dist/leaflet.css';

type AirportProperties = { aeroway: string; ref?: string; name?: string; osmUrl: string };
const airportBounds: L.LatLngBoundsExpression = [[49.996,8.505],[50.054,8.595]];
function fitRunway(map: L.Map, bounds: L.LatLngBoundsExpression = airportBounds) {
  const size=map.getSize(), compact=size.x<=900;
  map.fitBounds(bounds,{paddingTopLeft:[compact?70:100,90],paddingBottomRight:[compact?40:Math.min(540,size.x*.4),compact?size.y*.56:100],maxZoom:15,animate:!window.matchMedia('(prefers-reduced-motion: reduce)').matches,duration:.45});
}
export default function AirportMap({onBack,traffic,focus,onFocus,planning,...view}:WindView&{planning:PlanningControl;onBack:()=>void;traffic:TrafficControl;focus:'runway18'|'airport';onFocus:(value:'runway18'|'airport')=>void}) {
  const {dataset,hour}=view;
  const frame=useMemo(()=>frameAt(dataset,hour),[dataset,hour]);
  const presentation=runwayPresentation(frame,view.connectionError);
  const container=useRef<HTMLDivElement>(null), map=useRef<L.Map|null>(null);
  const [mapInstance,setMapInstance]=useState<L.Map|null>(null);
  const runway=useRef<L.GeoJSON|null>(null), boundary=useRef<L.GeoJSON|null>(null),parallel=useRef<L.GeoJSON|null>(null);
  const [showRunway,setShowRunway]=useState(true), [showBoundary,setShowBoundary]=useState(false);
  const [windEnabled,setWindEnabled]=useState(true);
  const [animated,setAnimated]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [status,setStatus]=useState<'loading'|'ready'|'error'>('loading'), [tileError,setTileError]=useState(false);
  const [basemap,setBasemap]=useState<'satellite'|'street'>('satellite'), [showLayers,setShowLayers]=useState(false);
  useEffect(()=>{
    if(!container.current)return;
    const controller=new AbortController();
    const instance=L.map(container.current,{zoomControl:false,zoomSnap:.25,attributionControl:false});map.current=instance;
    L.control.attribution({position:'bottomleft',prefix:false}).addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors').addTo(instance);
    fitRunway(instance);setMapInstance(instance);
    fetch('/data/frankfurt-airport.geojson',{signal:controller.signal}).then(response=>{if(!response.ok)throw new Error('Airport geometry unavailable');return response.json();}).then((data:FeatureCollection<Geometry,AirportProperties>)=>{
      if(controller.signal.aborted)return;
      runway.current=L.geoJSON(data,{filter:f=>f.properties.aeroway==='runway'&&f.properties.ref==='18',style:{color:'#a8b3bd',weight:12,opacity:.9,className:'runway-highlight'},onEachFeature:(feature,layer)=>layer.bindTooltip(String(feature.properties.ref),{permanent:true,direction:'center',className:'runway-label is-selected'})}).addTo(instance);
      parallel.current=L.geoJSON(data,{filter:f=>f.properties.aeroway==='runway'&&f.properties.ref!=='18',style:{color:'#9db8bf',weight:4,opacity:.7}});
      boundary.current=L.geoJSON(data,{filter:f=>f.properties.aeroway==='aerodrome',style:{color:'#f5f5e0',weight:1.5,dashArray:'5 7',fillOpacity:.02}});
      fitRunway(instance);
      setStatus('ready');
    }).catch(error=>{if(error.name!=='AbortError')setStatus('error');});
    const resize=new ResizeObserver(()=>instance.invalidateSize());resize.observe(container.current);
    return()=>{controller.abort();resize.disconnect();instance.remove();map.current=null;runway.current=null;boundary.current=null;parallel.current=null;};
  },[]);
  useEffect(()=>{
    if(!mapInstance)return;setTileError(false);
    const tile=L.tileLayer(basemap==='satellite'?'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}':'https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:basemap==='satellite'?'Imagery &copy; Esri, Vantor, Earthstar Geographics, GIS User Community':''}).on('tileerror',()=>setTileError(true)).addTo(mapInstance);
    return()=>{tile.remove();tile.off();};
  },[mapInstance,basemap]);
  useEffect(()=>{if(!map.current||status!=='ready')return;for(const [layer,enabled]of [[runway.current,showRunway],[parallel.current,showRunway&&focus==='airport'],[boundary.current,showBoundary]] as const){if(layer){if(enabled)layer.addTo(map.current);else layer.remove();}}},[showRunway,showBoundary,status,focus]);
  const windows=forecastWindows(dataset,view.now??Date.now()).windows;
  const selectedRisk=windows.find(w=>w.id===planning.selected)??windows.find(w=>w.kind==='restricted')??windows[0]??null;
  const proposedEnds=flightReviews(dataset,planning.board,selectedRisk,view.now??Date.now()).filter(r=>planning.proposals.includes(r.flight.id)&&r.candidate).map(r=>r.candidate).join(',');
  useEffect(()=>{
    if(!mapInstance||!proposedEnds)return;
    const controller=new AbortController();let layer:L.GeoJSON|undefined;
    fetch('/data/frankfurt-airport.geojson',{signal:controller.signal}).then(r=>r.json()).then((data:FeatureCollection<Geometry,AirportProperties>)=>{if(controller.signal.aborted)return;layer=L.geoJSON(data,{filter:f=>f.properties.aeroway==='runway'&&Boolean(f.properties.ref?.includes('C')),style:{color:'#7bb8ff',weight:10,opacity:.9,dashArray:'8 8'}}).bindTooltip(`Draft: ${proposedEnds} · wind suitable · availability unverified`,{permanent:true,direction:'center',className:'runway-label'}).addTo(mapInstance);}).catch(()=>{});
    return()=>{controller.abort();layer?.remove();};
  },[mapInstance,proposedEnds]);
  const speed=frame.eastKt===null||frame.northKt===null?null:Math.hypot(frame.eastKt,frame.northKt);
  const from=speed===null?null:windFromVector(frame.eastKt!,frame.northKt!);
  const next=frame.weatherState==='unknown'?undefined:(dataset.planningFrames??dataset.frames).find(point=>Date.parse(point.validTime)>Date.parse(frame.validTime)&&point.weatherState!==frame.weatherState&&point.weatherState!=='unknown');
  useEffect(()=>{
    if(status!=='ready'||!runway.current)return;
    runway.current.setStyle({color:presentation.color,weight:focus==='runway18'?12:6,opacity:focus==='runway18'?.9:.55});
    runway.current.eachLayer(layer=>{layer.getTooltip()?.getElement()?.style.setProperty('--runway-color',presentation.color);});
    parallel.current?.eachLayer(layer=>{const path=layer as L.Path & {feature?:{properties?:{ref?:string}}};path.setStyle({color:path.feature?.properties?.ref===traffic.runway?'#f3d36d':'#9db8bf',weight:path.feature?.properties?.ref===traffic.runway?11:4});});
  },[status,presentation.color,traffic.runway,showRunway,focus]);
  useEffect(()=>{if(mapInstance&&status==='ready')fitRunway(mapInstance,focus==='runway18'?runway.current?.getBounds().pad(.35):airportBounds);},[mapInstance,status,focus]);
  return <main className={`map-experience ${basemap}`} data-runway-tone={presentation.tone}>
    <div ref={container} className="map-canvas" aria-label="Interactive Frankfurt Airport runway and aircraft map"/>
    <WindLayer map={mapInstance} dataset={dataset} frame={frame} enabled={windEnabled} animated={animated}/>
    <AirportDirectionLayer map={mapInstance} view={view}/>
    {focus==='airport'&&<AircraftLayer map={mapInstance} traffic={traffic}/>}
    <div className="map-vignette"/>
    <section className="glass map-direction-badge"><DirectionBadge view={view}/><div className="aircraft-key"><span className="arrival-key">Landing</span><span className="departure-key">Departure</span></div><small>Aircraft travel · 18 always south · configuration only</small></section>
    <button className="glass back-button" onClick={onBack}><Icon name="back" size={19}/>Dashboard</button>
    <div className="map-tools glass" aria-label="Map controls"><button aria-label="Zoom in" onClick={()=>map.current?.zoomIn()}><Icon name="plus"/></button><button aria-label="Zoom out" onClick={()=>map.current?.zoomOut()}><Icon name="minus"/></button><span className="tool-divider"/><button aria-label={focus==='runway18'?'Show Runway 18':'Show airport directions'} onClick={()=>{if(map.current)fitRunway(map.current,focus==='runway18'?runway.current?.getBounds().pad(.35):airportBounds);}}><Icon name="locate"/></button><span className="tool-divider"/><button aria-label="Wind layer" aria-pressed={windEnabled} className={windEnabled?'tool-active':''} onClick={()=>setWindEnabled(!windEnabled)}><Icon name="wind"/></button><button aria-label="Map layers" aria-expanded={showLayers} aria-controls="layer-options" onClick={()=>setShowLayers(!showLayers)}><Icon name="layers"/></button></div>
    <section id="layer-options" className="glass layer-popover" data-open={showLayers} aria-hidden={!showLayers} inert={!showLayers}><div className="popover-heading"><h2>Map layers</h2><button aria-label="Close map layers" onClick={()=>setShowLayers(false)}><Icon name="close" size={17}/></button></div><div className="segmented"><button className={basemap==='satellite'?'is-active':''} aria-pressed={basemap==='satellite'} onClick={()=>setBasemap('satellite')}>Satellite</button><button className={basemap==='street'?'is-active':''} aria-pressed={basemap==='street'} onClick={()=>setBasemap('street')}>Street map</button></div><div className="layer-options"><label>Wind speed & flow<input type="checkbox" checked={windEnabled} onChange={e=>setWindEnabled(e.target.checked)}/></label><label>Animate wind<input type="checkbox" checked={animated} onChange={e=>setAnimated(e.target.checked)}/></label><label>Runway highlights<input type="checkbox" checked={showRunway} onChange={e=>setShowRunway(e.target.checked)}/></label><label>Airport boundary<input type="checkbox" checked={showBoundary} onChange={e=>setShowBoundary(e.target.checked)}/></label></div><p>{dataset.mode==='demo'?'Synthetic spatial field for design review.':dataset.source} Runway highlight identifies location.</p></section>
    <section className="glass wind-legend" aria-label="Wind layer legend"><div className="wind-legend-heading"><Icon name="wind" size={18}/><strong>Wind speed</strong><span className="wind-mode">{dataset.mode==='demo'?'Demo':'Airport'}</span><span>kt</span></div><div className="wind-scale"/><div className="wind-scale-labels"><span>0</span><span>10</span><span>20</span><span>30</span><span>40+</span></div><p>{speed===null?'Wind unavailable':`${speed.toFixed(1)} kt · from ${Math.round(from!)}°T`}<span>{formatUtc(frame.validTime)} UTC</span></p><small>{windEnabled?'Particles travel with the wind':'Wind layer hidden'}</small></section>
    <div className={`map-inspector ${focus==='airport'?'traffic-inspector':'primary-inspector'}`}>
      <nav className="glass segmented map-focus-switch" aria-label="Map focus"><button className={focus==='runway18'?'is-active':''} aria-pressed={focus==='runway18'} onClick={()=>onFocus('runway18')}>Runway 18</button><button className={focus==='airport'?'is-active':''} aria-pressed={focus==='airport'} onClick={()=>onFocus('airport')}>Other runways</button></nav>
      {focus==='runway18'?<><section className="glass runway-panel" aria-label="Runway 18 summary" data-tone={presentation.tone}>
      <div className="runway-summary-heading"><h1>Runway 18</h1><div className="source-actions"><span className="demo-badge">{view.connectionError?'Connection lost':dataset.mode==='demo'?'Demo':hour===0&&dataset.currentObservationSource?'DWD · provisional':'Live'}</span>{view.onRefresh&&<button className="refresh-data" aria-label="Refresh weather" disabled={view.refreshing} onClick={view.onRefresh}><Icon name="refresh" size={16}/></button>}</div></div>
      <div className={`runway-status tone-${presentation.tone}`} title={presentation.detail+(hour===0?` ${dataset.currentObservationNote??''}`:'')}><span className="status-dot"/><span key={presentation.label} className="status-copy">{presentation.label}</span><span className="status-detail">{dataset.mode==='demo'?'Simulated':'Weather only'}</span></div>
      <dl className="compact-metrics"><div><dt>Tailwind</dt><dd>{frame.tailwindKt===null?'—':frame.tailwindKt.toFixed(1)}<small> kt</small></dd></div><div><dt>Gust crosswind</dt><dd>{frame.gustCrosswindKt===null?'—':frame.gustCrosswindKt.toFixed(1)}<small> kt</small></dd></div><div><dt>Next change</dt><dd>{next?formatUtc(next.validTime):'—'}<small> UTC</small></dd></div></dl>
    </section><details className="glass map-planning"><summary>Restriction windows & flights{planning.proposals.length?` · ${planning.proposals.length} drafts`:""}</summary><RunwayPlan view={view} planning={planning} compact/></details><WindForecast {...view}/></>:<><RunwayTrafficSummary view={view} traffic={traffic} compact/><ParallelForecast view={view} traffic={traffic}/></>}
    </div>
    {status==='loading'&&<div className="map-notice glass" role="status">Loading airport runways…</div>}{status==='error'&&<div className="map-notice glass" role="alert">Runway overlay unavailable. Reload to try again.</div>}{tileError&&<div className="map-notice glass" role="status">Some map tiles did not load. <button onClick={()=>setBasemap(basemap==='satellite'?'street':'satellite')}>Try another map</button></div>}
  </main>;
}
