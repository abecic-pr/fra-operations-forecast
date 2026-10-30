import {runwayConfiguration} from './data/direction';
import { useEffect, useState } from 'react';
import L from 'leaflet';
import { airportDirection, formatUtc, frameAt, movementEndpoints, runwayPresentation, type WindView } from './data/wind';

type Runway = {ref:string; coordinates:number[][]};
function useRunways(){
  const [runways,setRunways]=useState<Runway[]>([]);
  useEffect(()=>{const controller=new AbortController();fetch('/data/frankfurt-airport.geojson',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>setRunways(data.features.filter((f:any)=>f.properties.aeroway==='runway'&&f.geometry.type==='LineString').map((f:any)=>({ref:f.properties.ref,coordinates:f.geometry.coordinates})))).catch(()=>{});return()=>controller.abort();},[]);
  return runways;
}
const isArrival=(ref:string)=>ref==='07L/25R'||ref==='07R/25L';
export function DirectionBadge({view}:{view:WindView}){
  const direction=airportDirection(view.dataset,view.hour,view.connectionError);
  return <div className="airport-direction-copy"><h2>Airport direction</h2><p><strong>{direction.label}</strong>{direction.direction&&<span> {direction.direction} · {direction.heading}°T</span>}</p><small>{direction.basis}{direction.time?` · ${formatUtc(direction.time)} UTC`:''}</small></div>;
}
export function AirportDirectionLayer({map,view}:{map:L.Map|null;view:WindView}){
  const runways=useRunways(),direction=airportDirection(view.dataset,view.hour,view.connectionError),tone=runwayPresentation(frameAt(view.dataset,view.hour),view.connectionError);
  useEffect(()=>{
    if(!map)return;
    if(!map.getPane('aircraft-directions')){const pane=map.createPane('aircraft-directions');pane.style.zIndex='620';pane.style.pointerEvents='none';}
    const group=L.layerGroup().addTo(map);
    for(const runway of runways){
      const south=runway.ref==='18',arrival=isArrival(runway.ref),configuration=runwayConfiguration(direction.direction).find(r=>r.ref===runway.ref),heading=configuration?.heading??null;
      if(heading===null)continue;
      const color=south?tone.color:arrival?'#63d6ff':'#ffffff';
      const [start,end]=movementEndpoints(runway.coordinates,heading);
      if(!south)L.polyline(runway.coordinates.map(p=>[p[1],p[0]] as L.LatLngTuple),{pane:'aircraft-directions',color,weight:5,opacity:.75,interactive:false}).addTo(group);
      for(const t of [.32,.68]){
        const lat=start[1]+(end[1]-start[1])*t,lng=start[0]+(end[0]-start[0])*t;
        L.marker([lat,lng],{pane:'aircraft-directions',interactive:false,keyboard:false,icon:L.divIcon({className:'aircraft-arrow',iconSize:[26,26],iconAnchor:[13,13],html:`<svg viewBox="0 0 26 26" style="color:${color};transform:rotate(${heading}deg)"><path d="M13 23V4M5 12l8-8 8 8"/></svg>`})}).addTo(group);
      }
      const endName=configuration?.end??'Direction not supplied';
      L.marker([end[1],end[0]],{pane:'aircraft-directions',interactive:false,keyboard:false,icon:L.divIcon({className:'aircraft-runway-label',iconSize:[80,25],iconAnchor:south?[-12,12]:[40,-9],html:`<span>${endName} · ${arrival?'Landing':'Departure'}</span>`})}).addTo(group);
    }
    return()=>{group.remove();};
  },[map,runways,direction.direction,direction.heading,tone.color]);
  return null;
}
export default function AirportDirection({view}:{view:WindView}){
  const runways=useRunways(),direction=airportDirection(view.dataset,view.hour,view.connectionError),tone=runwayPresentation(frameAt(view.dataset,view.hour),view.connectionError);
  const project=(p:number[])=>[45+(p[0]-8.50)/.105*510,290-(p[1]-49.995)/.065*255];
  return <section className="airport-model-card" aria-label="Airport operating direction and runway model">
    <div className="airport-model-info"><DirectionBadge view={view}/><p className="airport-model-description">{direction.direction?`Landings approach from the ${direction.approach}. The three parallel runways move ${direction.label.toLowerCase()} together.`:'No east/west movement is shown without an available direction.'}</p><div className="aircraft-key"><span className="arrival-key">Landing</span><span className="departure-key">Departure</span></div><p className="airport-model-source">{direction.source}{direction.certainty!==null?` · ${(direction.certainty*100).toFixed(0)}% model certainty`:''}<br/>Runway 18 always departs south. Arrows show the runway configuration; individual flights are unassigned.</p></div>
    <div className="airport-model-drawing"><svg viewBox="0 0 600 345" role="img" aria-label={`${direction.label}. Parallel runways share direction; Runway 18 departs south.`}><path className="model-airport-outline" d="M45 105L185 53L530 110L548 179L220 250L203 302L118 302L112 180Z"/><g className="model-compass"><path d="M556 56V26m-5 7 5-7 5 7"/><text x="556" y="18">N</text></g>
      {runways.map(runway=>{const south=runway.ref==='18',arrival=isArrival(runway.ref),configuration=runwayConfiguration(direction.direction).find(r=>r.ref===runway.ref),heading=configuration?.heading??null;const [a,b]=movementEndpoints(runway.coordinates,heading??70).map(project),angle=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI+90;const color=south?tone.color:arrival?'#007fa4':'#173b72';return <g key={runway.ref} style={{color}}><path d={`M${a}L${b}`} className="model-runway"/>{heading!==null&&[.3,.65].map(t=><g key={t} transform={`translate(${a[0]+(b[0]-a[0])*t},${a[1]+(b[1]-a[1])*t}) rotate(${angle})`}><path d="M0 10V-10m-6 6 6-6 6 6" className="model-movement"/></g>)}<text x={(a[0]+b[0])/2+(south?-16:0)} y={(a[1]+b[1])/2+(south?35:-18)} className="model-runway-name">{runway.ref}</text></g>;})}
      {!runways.length&&<text x="300" y="170" textAnchor="middle">Airport geometry unavailable</text>}
      <text className="model-footnote" x="300" y="330" textAnchor="middle">North up · OSM runway geometry · wind suitability is separate</text></svg></div>
  </section>;
}
