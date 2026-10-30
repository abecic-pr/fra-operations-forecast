import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import type { FeatureCollection } from 'geojson';
import Icon from './Icon';
import WindLayer from './WindLayer';
import { formatUtc, runwayPresentation, type WindDataset, type WindFrame } from './data/wind';
import 'leaflet/dist/leaflet.css';

export default function AirportPreview({dataset,frame,connectionError,onOpenMap}:{dataset:WindDataset;frame:WindFrame;connectionError:boolean;onOpenMap:()=>void}) {
  const host=useRef<HTMLDivElement>(null),runway=useRef<L.GeoJSON|null>(null);
  const [map,setMap]=useState<L.Map|null>(null),[error,setError]=useState(false),[ready,setReady]=useState(false);
  const [animated,setAnimated]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const tone=runwayPresentation(frame,connectionError);
  useEffect(()=>{
    if(!host.current)return;
    const controller=new AbortController(),instance=L.map(host.current,{zoomControl:false,scrollWheelZoom:false,attributionControl:true}).setView([50.024,8.526],14);
    L.control.zoom({position:'topright'}).addTo(instance);
    L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:18,attribution:'Imagery © Esri, Vantor, Earthstar Geographics'}).on('tileerror',()=>setError(true)).addTo(instance);
    instance.attributionControl.addAttribution('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors');
    setMap(instance);
    fetch('/data/frankfurt-airport.geojson',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then((data:FeatureCollection)=>{if(controller.signal.aborted)return;runway.current=L.geoJSON(data,{filter:f=>f.properties?.aeroway==='runway'&&f.properties?.ref==='18',style:{color:'#a8b3bd',weight:10,opacity:.9,className:'runway-highlight'}}).bindTooltip('18',{permanent:true,direction:'center',className:'runway-label'}).addTo(instance);if(runway.current.getBounds().isValid())instance.fitBounds(runway.current.getBounds().pad(.15),{padding:[40,40],maxZoom:15});setReady(true);}).catch(()=>{if(!controller.signal.aborted)setError(true);});
    const resize=new ResizeObserver(()=>instance.invalidateSize());resize.observe(host.current);
    return()=>{controller.abort();resize.disconnect();instance.remove();runway.current=null;};
  },[]);
  useEffect(()=>{runway.current?.setStyle({color:tone.color});},[tone.color,ready]);
  return <section className="airport-preview" aria-label="Runway 18 wind map preview"><div ref={host} className="airport-preview-canvas"/><WindLayer map={map} dataset={dataset} frame={frame} enabled animated={animated}/><div className="preview-topline"><span>Runway 18 · {formatUtc(frame.validTime)} UTC</span></div><div className="preview-actions"><button className="glass" aria-label={animated?'Pause preview wind animation':'Animate preview wind'} aria-pressed={animated} onClick={()=>setAnimated(!animated)}><Icon name={animated?'pause':'play'} size={14}/></button><button className="glass" onClick={onOpenMap}>Open map<Icon name="arrow" size={15}/></button></div><div className="preview-wind-key"><span>Airport-point wind</span><small>Flow shows travel direction · no spatial grid</small></div>{error&&<p className="preview-map-error">Some map imagery or geometry could not load.</p>}</section>;
}
