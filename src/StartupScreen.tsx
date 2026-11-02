import { useEffect, useRef, useState, type CSSProperties } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import Icon from './Icon';

// Runway ends from public/data/frankfurt-airport.geojson, in metres east (x) and south (y) of 50.033 N, 8.553 E.
const LAT0=50.033,LON0=8.553,KX=111320*Math.cos(LAT0*Math.PI/180),KY=110574;
const latLng=(x:number,y:number):L.LatLngTuple=>[LAT0-y/KY,LON0+x/KX];
type Point=[number,number];
const RUNWAYS:Record<string,[Point,Point]>={ // [west/north end, east/south end]
  '07L/25R':[[-3999,-448],[-1379,-1418]],'07C/25C':[[-1313,43],[2430,-1341]],
  '07R/25L':[[-1345,603],[2398,-780]],'18':[[-1935,-128],[-1909,3816]],
};
// Illustration only: per the brief, 07L/25R and 07R/25L land, 07C/25C and 18 depart.
const FLIGHTS=[{runway:'07L/25R',land:true,start:1.8,length:6.5},{runway:'07C/25C',land:false,start:2.6,length:6.2},
  {runway:'07R/25L',land:true,start:3.6,length:6.5},{runway:'18',land:false,start:4.4,length:6}];
const PHASE=11,APPROACH=3500,LIFTOFF=2000,SIZE=4.2; // aircraft drawn ~420 m long so they read at airport scale
const PLANE='M0-50C4-46 5-40 5-30V-8L46 10V17L5 8 4 34 18 44V49L0 45-18 49V44L-4 34-5 8-46 17V10L-5-8V-30C-5-40-4-46 0-50Z';
// Wind travel direction on screen: from 250° blows towards 070° (right), from 070° towards 250° (left).
const WIND=[[Math.sin(70*Math.PI/180),-Math.cos(70*Math.PI/180)],[-Math.sin(70*Math.PI/180),Math.cos(70*Math.PI/180)]];
const sources=['Airport wind sensor','METAR & TAF','ICON weather models','Operating direction'];
const clamp=(v:number)=>Math.min(1,Math.max(0,v));
const smooth=(v:number)=>v*v*(3-2*v);

function flight(f:typeof FLIGHTS[number],od25:boolean,t:number) {
  const [a,b]=RUNWAYS[f.runway],[from,to]=f.runway==='18'||!od25?[a,b]:[b,a];
  const len=Math.hypot(to[0]-from[0],to[1]-from[1]),ux=(to[0]-from[0])/len,uy=(to[1]-from[1])/len;
  const p=(t-f.start)/f.length;
  if(p<0||p>1)return null;
  let along:number,alt:number;
  if(f.land){ // constant-speed glide, touchdown 250 m past the threshold, then braking
    const s=p<.7?APPROACH*p/.7:APPROACH+APPROACH/.7*((p-.7)-(p-.7)**2/.6);
    along=s-APPROACH;alt=clamp((APPROACH+250-s)/(APPROACH+250));
  } else { // accelerating roll, lift-off, climb-out
    along=p<.5?LIFTOFF*(p/.5)**2:LIFTOFF+4*LIFTOFF*(p-.5);alt=clamp((along-LIFTOFF)/(2*LIFTOFF));
  }
  return {x:from[0]+ux*along,y:from[1]+uy*along,heading:Math.atan2(ux,-uy)*180/Math.PI,alt,opacity:Math.min(clamp(p/.08),clamp((1-p)/.12))};
}

const svg=(tag:string,attributes:Record<string,string|number>={})=>{
  const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));
  return node;
};

export default function StartupScreen({error}:{error:boolean}) {
  const host=useRef<HTMLDivElement>(null),wind=useRef<HTMLCanvasElement>(null),card=useRef<HTMLElement>(null),explain=useRef<HTMLElement>(null);
  const [od25,setOd25]=useState(true);
  useEffect(()=>{
    if(!host.current||!wind.current||!card.current)return;
    const still=error||window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const map=L.map(host.current,{zoomControl:false,dragging:false,scrollWheelZoom:false,doubleClickZoom:false,boxZoom:false,keyboard:false,touchZoom:false,zoomSnap:0,attributionControl:false});
    L.control.attribution({position:'bottomright',prefix:false}).addAttribution('Imagery © Esri, Vantor, Earthstar Geographics · Runways © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>').addTo(map);
    L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:18}).addTo(map);
    const fit=()=>{
      const box=card.current!.getBoundingClientRect(),top=explain.current!.getBoundingClientRect().bottom,wide=window.innerWidth>=900;
      map.invalidateSize();
      map.fitBounds(L.latLngBounds(latLng(-4300,-1800),latLng(3300,4000)),{animate:false,
        paddingTopLeft:[wide?box.right+24:16,wide?32:top+8],paddingBottomRight:[16,wide?32:window.innerHeight-box.top+12]});
    };
    fit();
    // Overlay in local metres; Leaflet keeps it registered to the imagery.
    const view=[-10000,-7000,20000,18000],overlay=svg('svg',{viewBox:view.join(' '),preserveAspectRatio:'none'});
    const defs=svg('defs'),shade=svg('linearGradient',{id:'startup-plane',x1:0,x2:1});
    for(const [offset,color] of [['0','#c9d2ce'],['.5','#ffffff'],['1','#aeb9b4']])shade.append(svg('stop',{offset,'stop-color':color}));
    defs.append(shade);overlay.append(defs);
    const lanes=Object.entries(RUNWAYS).map(([name,[a,b]])=>{
      const line=svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],class:`startup-lane${name==='18'?' is-18':''}`});
      overlay.append(line);return {name,line,a,b};
    });
    const labels=lanes.filter(l=>l.name!=='18').flatMap(({name,a,b})=>{
      const [west,east]=name.split('/');
      return ([[west,a,-1],[east,b,1]] as [string,Point,number][]).map(([text,[x,y],side])=>{
        const label=svg('text',{x:x+side*330,y:y+80,class:'startup-label'});label.textContent=text;overlay.append(label);
        return {label,east:side===1};
      });
    });
    const label18=svg('text',{x:-1590,y:-260,class:'startup-label is-on'});label18.textContent='18';overlay.append(label18);
    const planes=FLIGHTS.map(()=>{
      const shadow=svg('path',{d:PLANE,class:'startup-shadow'}),body=svg('g'),hull=svg('path',{d:PLANE,class:'startup-plane'});
      body.append(hull,svg('path',{d:'M-22 4h6M16 4h6',class:'startup-engine'}));overlay.append(shadow,body);
      return {shadow,body};
    });
    L.svgOverlay(overlay as unknown as SVGElement,L.latLngBounds(latLng(view[0],view[1]+view[3]),latLng(view[0]+view[2],view[1]))).addTo(map);
    const resize=new ResizeObserver(fit);resize.observe(host.current);

    const canvas=wind.current,context=canvas.getContext('2d')!;
    const particles=Array.from({length:150},()=>({x:Math.random(),y:Math.random(),age:Math.random()*4}));
    let frame=0,last=performance.now(),phase=-1;const begin=last;
    const draw=(now:number)=>{
      const t=still?7:(now-begin)/1000,cycle=Math.floor(t/PHASE)%2,local=t%PHASE,isWest=cycle===0;
      if(cycle!==phase){phase=cycle;setOd25(isWest);
        for(const {label,east} of labels)label.classList.toggle('is-on',east===isWest);}
      for(const {line,name} of lanes)line.style.strokeDashoffset=String((name!=='18'&&isWest?1:-1)*local*900); // dashes flow with the traffic
      FLIGHTS.forEach((f,i)=>{
        const state=flight(f,isWest,local),{shadow,body}=planes[i];
        shadow.style.opacity=body.style.opacity=state?String(state.opacity):'0';
        if(!state)return;
        const lift=state.alt*420,scale=SIZE*(1+state.alt*.5);
        body.setAttribute('transform',`translate(${state.x} ${state.y}) rotate(${state.heading}) scale(${scale})`);
        shadow.setAttribute('transform',`translate(${state.x+lift} ${state.y+lift*1.3}) rotate(${state.heading}) scale(${SIZE})`);
        shadow.style.opacity=String(state.opacity*(.45-state.alt*.25));
      });
      // Wind slackens, reverses, then settles at the start of each phase.
      const mix=smooth(clamp(local/2.2)),[px,py]=WIND[1-cycle],[nx,ny]=WIND[cycle];
      const vx=px+(nx-px)*mix,vy=py+(ny-py)*mix,dt=Math.min(.05,(now-last)/1000);last=now;
      const ratio=window.devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;
      if(canvas.width!==Math.round(w*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);}
      context.setTransform(ratio,0,0,ratio,0,0);
      context.globalCompositeOperation='destination-out';context.fillStyle='rgba(0,0,0,.14)';context.fillRect(0,0,w,h);
      context.globalCompositeOperation='source-over';context.strokeStyle='rgba(255,255,255,.55)';context.lineWidth=1.3;context.lineCap='round';
      if(!still){
        context.beginPath();
        for(const p of particles){
          const x=p.x*w,y=p.y*h;p.x+=vx*170*dt/w;p.y+=vy*170*dt/h;p.age+=dt;
          if(p.age>4||p.x<-.02||p.x>1.02||p.y<-.02||p.y>1.02){Object.assign(p,{x:Math.random(),y:Math.random(),age:0});continue;}
          context.moveTo(x,y);context.lineTo(p.x*w,p.y*h);
        }
        context.stroke();
        frame=requestAnimationFrame(draw);
      }
    };
    frame=requestAnimationFrame(draw);
    return()=>{cancelAnimationFrame(frame);resize.disconnect();map.remove();};
  },[error]);

  // The scene is an illustration; no current operating direction is known until the forecast arrives.
  return <main className={`startup${error?' is-error':''}`}>
    <div ref={host} className="startup-map" aria-hidden="true"/>
    <div className="startup-scrim" aria-hidden="true"/>
    <canvas ref={wind} className="startup-wind" aria-hidden="true"/>
    <aside ref={explain} className="startup-explain" aria-hidden="true">
      <strong key={od25?'25':'07'}>{od25?'25':'07'}</strong>
      <p>{od25?'Wind from the west, so aircraft land and take off heading west, into the wind.':'Wind from the east, so aircraft land and take off heading east, into the wind.'}<small>Runway 18 departs south either way. Illustration, not today’s direction.</small></p>
    </aside>
    <section ref={card} className="startup-card" role={error?'alert':'status'} aria-live="polite">
      <div className="startup-compass" aria-hidden="true"><span>N</span><svg viewBox="-50 -50 100 100"><path d="M0 34V-30M-11 -18L0 -32L11 -18"/></svg></div>
      <p className="startup-place">Frankfurt Airport</p>
      <h1>{error?'Live forecast unavailable':'Reading the wind…'}</h1>
      <p className="startup-copy">{error?'The forecast service did not respond. Your connection may be offline, or the service is restarting.':'Fetching the latest measurements and weather models. The first load after a quiet period can take a little longer.'}</p>
      {error
        ?<button className="startup-retry" onClick={()=>window.location.reload()}><Icon name="refresh" size={18}/>Try again</button>
        :<ul className="startup-sources" aria-label="Data being fetched">{sources.map((source,i)=><li key={source} style={{'--i':i} as CSSProperties}>{source}</li>)}</ul>}
    </section>
  </main>;
}
