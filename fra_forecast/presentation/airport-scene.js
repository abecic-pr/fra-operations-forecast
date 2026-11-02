// Shared 3D Frankfurt Airport scene: the app's loading screen and the /how-it-works page both use it.
// Plain ES module so the Python-served page can load it without a build; types are in airport-scene.d.ts.
import { Map as MapLibre } from 'maplibre-gl';

// Runway ends from public/data/frankfurt-airport.geojson, in metres east (x) and south (y) of 50.033 N, 8.553 E.
const LAT0=50.033,LON0=8.553,KX=111320*Math.cos(LAT0*Math.PI/180),KY=110574;
const lngLat=(x,y)=>[LON0+x/KX,LAT0-y/KY];
const RUNWAYS={ // [west/north end, east/south end]
  '07L/25R':[[-3999,-448],[-1379,-1418]],'07C/25C':[[-1313,43],[2430,-1341]],
  '07R/25L':[[-1345,603],[2398,-780]],'18':[[-1935,-128],[-1909,3816]],
};
// Same roles and colours as the map view: per the brief, 07L/25R and 07R/25L land, 07C/25C and 18 depart.
const LANDING='#63d6ff',DEPARTURE='#ffffff',SOUTH='#69df9b';
const role=name=>name==='18'?SOUTH:name==='07C/25C'?DEPARTURE:LANDING;
const FLIGHTS=[{runway:'07L/25R',land:true,start:1.6,length:7},{runway:'07C/25C',land:false,start:2.4,length:6.8},
  {runway:'07R/25L',land:true,start:3.8,length:7},{runway:'18',land:false,start:4.6,length:6.6}];
const PHASE=12,APPROACH=4200,LIFTOFF=2000,CLIMB=650,SCALE=6; // aircraft drawn 6x real size to read at airport scale
const FRAME=[lngLat(-4000,-1500),lngLat(3000,2600)]; // runways, cropping the south of 18
// Low-poly airliner in metres: forward f, right r, and [bottom, top] above the aircraft's altitude.
const PARTS=[
  [[[19,0],[17,1.9],[-15,2],[-19,.5],[-19,-.5],[-15,-2],[17,-1.9]],0,4],
  [[[4,1.5],[-5,17],[-8,17],[-6,1.5],[-6,-1.5],[-8,-17],[-5,-17],[4,-1.5]],1,2],
  [[[-14,1],[-18,7],[-20,7],[-19,1],[-19,-1],[-20,-7],[-18,-7],[-14,-1]],3.2,3.9],
  [[[-13,.35],[-19.5,.35],[-19.5,-.35],[-13,-.35]],4,10],
];
const clamp=v=>Math.min(1,Math.max(0,v));
const smooth=v=>v*v*(3-2*v);

function ends(name,westbound) {
  const [a,b]=RUNWAYS[name];
  return name==='18'||!westbound?[a,b]:[b,a];
}

function flight(f,westbound,t) {
  const [from,to]=ends(f.runway,westbound),len=Math.hypot(to[0]-from[0],to[1]-from[1]);
  const ux=(to[0]-from[0])/len,uy=(to[1]-from[1])/len,p=(t-f.start)/f.length;
  if(p<0||p>1)return null;
  let along,alt;
  if(f.land){ // steady glide, touchdown 300 m past the threshold, then braking
    const s=p<.7?APPROACH*p/.7:APPROACH+APPROACH/.7*((p-.7)-(p-.7)**2/.6);
    along=s-APPROACH;alt=clamp((APPROACH+300-s)/(APPROACH+300));
  } else { // accelerating roll, rotation, climb-out
    along=p<.5?LIFTOFF*(p/.5)**2:LIFTOFF+4*LIFTOFF*(p-.5);alt=clamp((along-LIFTOFF)/(2*LIFTOFF))**1.3;
  }
  return {x:from[0]+ux*along,y:from[1]+uy*along,ux,uy,alt,fade:Math.min(clamp(p/.06),clamp((1-p)/.1))};
}

const ring=points=>[...points,points[0]].map(([x,y])=>lngLat(x,y));
const place=(points,x,y,ux,uy,scale)=>
  points.map(([f,r])=>[x+(f*ux-r*uy)*scale,y+(f*uy+r*ux)*scale]);

export function startScene(container,wind,labels,options) {
  const map=new MapLibre({container,interactive:false,center:lngLat(-600,1200),zoom:11.4,pitch:0,bearing:0,maxPitch:70,
    attributionControl:{compact:true},fadeDuration:0,
    style:{version:8,
      sky:{'sky-color':'#2c3a44','horizon-color':'#8aa0ad','fog-color':'#55646d','sky-horizon-blend':.6,'horizon-fog-blend':.6,'fog-ground-blend':.4},
      sources:{
        imagery:{type:'raster',tileSize:256,maxzoom:18,attribution:'Imagery © Esri, Vantor, Earthstar Geographics',
          tiles:['https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}']},
        runways:{type:'geojson',data:{type:'FeatureCollection',features:[]}},
        moving:{type:'geojson',data:{type:'FeatureCollection',features:[]}},
        shadows:{type:'geojson',data:{type:'FeatureCollection',features:[]}},
      },
      layers:[
        {id:'imagery',type:'raster',source:'imagery',paint:{'raster-saturation':-.15,'raster-contrast':.05}},
        {id:'runways',type:'line',source:'runways',layout:{'line-cap':'round'},paint:{'line-color':['get','color'],'line-opacity':.55,'line-width':['interpolate',['exponential',2],['zoom'],11,2,15,22]}},
        {id:'shadows',type:'fill',source:'shadows',paint:{'fill-color':'#05090b','fill-opacity':['get','opacity']}},
        {id:'moving',type:'fill-extrusion',source:'moving',paint:{'fill-extrusion-color':['get','color'],'fill-extrusion-base':['get','base'],'fill-extrusion-height':['get','top'],'fill-extrusion-opacity':1,'fill-extrusion-vertical-gradient':true}},
      ]},
  });
  const tags=Object.keys(RUNWAYS).map(name=>{
    const tag=document.createElement('div');tag.className='aircraft-runway-label';tag.append(document.createElement('span'));labels.append(tag);
    return {name,tag};
  });
  let frame=0,phase=-1,begin=0,last=0,ready=false;
  // Portrait screens look east along the runways so they fill the tall frame.
  const heading=()=>container.clientWidth<container.clientHeight?62:-18;
  const particles=Array.from({length:220},()=>({x:Math.random(),y:Math.random(),age:Math.random()*3}));
  const context=wind.getContext('2d');

  const draw=now=>{
    if(!begin)begin=last=now;
    if(options.paused?.()){begin+=now-last;last=now;frame=requestAnimationFrame(draw);return;} // hold the clock while off-screen
    const t=options.still?7.5:(now-begin)/1000,cycle=Math.floor(t/PHASE)%2,local=t%PHASE,westbound=cycle===0;
    if(cycle!==phase){
      phase=cycle;options.onPhase(westbound);
      map.getSource('runways').setData({type:'FeatureCollection',features:Object.keys(RUNWAYS).map(name=>(
        {type:'Feature',properties:{color:role(name)},geometry:{type:'LineString',coordinates:RUNWAYS[name].map(([x,y])=>lngLat(x,y))}}))});
    }
    const moving=[],shadows=[];
    // Chevrons slide along each runway in the direction aircraft use it.
    for(const name of Object.keys(RUNWAYS)){
      const [from,to]=ends(name,westbound),len=Math.hypot(to[0]-from[0],to[1]-from[1]),ux=(to[0]-from[0])/len,uy=(to[1]-from[1])/len;
      for(let k=0;k<4;k++){
        const s=((k/4+local*.06)%1)*len;
        moving.push({type:'Feature',properties:{color:role(name),base:0,top:4},geometry:{type:'Polygon',coordinates:[ring(place([[60,0],[-40,70],[-70,70],[0,0],[-70,-70],[-40,-70]],from[0]+ux*s,from[1]+uy*s,ux,uy,1))]}});
      }
    }
    FLIGHTS.forEach(f=>{
      const state=flight(f,westbound,local);
      if(!state||state.fade<.02)return;
      const lift=state.alt*CLIMB;
      for(const [shape,bottom,top] of PARTS)
        moving.push({type:'Feature',properties:{color:'#f4f7f8',base:lift+bottom*SCALE,top:lift+top*SCALE},geometry:{type:'Polygon',coordinates:[ring(place(shape,state.x,state.y,state.ux,state.uy,SCALE*(.4+.6*state.fade)))]}});
      // Sun from the north-west: the shadow slides south-east and fades as the aircraft climbs.
      for(const [shape] of PARTS.slice(0,3))
        shadows.push({type:'Feature',properties:{opacity:.45*(1-state.alt*.7)*state.fade},geometry:{type:'Polygon',coordinates:[ring(place(shape,state.x+lift*.55,state.y+lift*.75,state.ux,state.uy,SCALE))]}});
    });
    map.getSource('moving').setData({type:'FeatureCollection',features:moving});
    map.getSource('shadows').setData({type:'FeatureCollection',features:shadows});
    if(ready&&!options.still&&!map.isMoving())map.setBearing(heading()+9*Math.sin(t*2*Math.PI/48)); // slow drift around the airport
    for(const {name,tag} of tags){
      const [from,to]=ends(name,westbound),[west,east]=name.split('/'),label=name==='18'?'18':westbound?east:west;
      const at=name==='18'?.45:name==='07C/25C'?.3:0,point=map.project(lngLat(from[0]+(to[0]-from[0])*at,from[1]+(to[1]-from[1])*at));
      // Landings label above the threshold, departures below, so the parallel runway labels do not collide.
      tag.style.transform=`translate(${point.x}px,${point.y}px) translate(${name==='18'?'14px,-50%':`-50%,${role(name)===LANDING?'-150%':'50%'}`})`;
      tag.firstElementChild.textContent=`${label} · ${name==='18'||name==='07C/25C'?'Departure':'Landing'}`;
    }
    // Wind streaks travel with the wind, converted to screen direction for the current camera.
    const mix=smooth(clamp(local/2.4)),angle=dir=>dir*Math.PI/180;
    const before=westbound?250:70,after=westbound?70:250; // travel bearing: wind from 250° moves towards 070°
    const vx=Math.sin(angle(before))*(1-mix)+Math.sin(angle(after))*mix,vy=-Math.cos(angle(before))*(1-mix)-Math.cos(angle(after))*mix;
    const origin=map.project(lngLat(0,1000)),ahead=map.project(lngLat(vx*800,1000+vy*800));
    const sx=(ahead.x-origin.x),sy=(ahead.y-origin.y),dt=Math.min(.05,(now-last)/1000);last=now;
    const ratio=window.devicePixelRatio||1,w=wind.clientWidth,h=wind.clientHeight;
    if(wind.width!==Math.round(w*ratio)||wind.height!==Math.round(h*ratio)){wind.width=Math.round(w*ratio);wind.height=Math.round(h*ratio);}
    context.setTransform(ratio,0,0,ratio,0,0);
    context.globalCompositeOperation='destination-out';context.fillStyle='rgba(0,0,0,.16)';context.fillRect(0,0,w,h);
    context.globalCompositeOperation='source-over';context.strokeStyle='rgba(255,255,255,.6)';context.lineWidth=1.2;context.lineCap='round';
    if(!options.still){
      context.beginPath();
      for(const p of particles){
        const x=p.x*w,y=p.y*h;p.x+=sx*.9*dt/w;p.y+=sy*.9*dt/h;p.age+=dt;
        if(p.age>3||p.x<-.02||p.x>1.02||p.y<-.02||p.y>1.02){Object.assign(p,{x:Math.random(),y:Math.random(),age:0});continue;}
        context.moveTo(x,y);context.lineTo(p.x*w,p.y*h);
      }
      context.stroke();
      frame=requestAnimationFrame(draw);
    }
  };

  map.on('load',()=>{
    // Buildings stream in after the imagery so a slow vector source never holds back the scene.
    map.addSource('buildings',{type:'vector',url:'https://tiles.openfreemap.org/planet',attribution:'<a href="https://openfreemap.org">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/">OpenMapTiles</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});
    map.addLayer({id:'buildings',type:'fill-extrusion',source:'buildings','source-layer':'building',minzoom:12,
      paint:{'fill-extrusion-color':'#dfe5ea','fill-extrusion-opacity':.92,'fill-extrusion-vertical-gradient':true, // heights x2.5 so terminals read at this distance
        'fill-extrusion-height':['*',2.5,['coalesce',['get','render_height'],8]],'fill-extrusion-base':['*',2.5,['coalesce',['get','render_min_height'],0]]}},'moving');
    options.onReady();
    const camera=map.cameraForBounds(FRAME,{padding:options.padding(),pitch:60,bearing:heading()});
    const target={...camera,zoom:(camera?.zoom??13)+.05,pitch:60,bearing:heading()};
    if(options.still)map.jumpTo(target); else map.easeTo({...target,duration:4200,easing:t=>1-(1-t)**3});
    map.once('moveend',()=>{ready=true;});
    if(options.still)ready=true;
    frame=requestAnimationFrame(draw);
  });
  if(options.still)map.on('move',()=>requestAnimationFrame(draw)); // keep labels on the still frame
  const resize=new ResizeObserver(()=>{map.resize();if(ready){const c=map.cameraForBounds(FRAME,{padding:options.padding(),pitch:60,bearing:map.getBearing()});if(c)map.jumpTo({center:c.center,zoom:(c.zoom??13)+.05});}});
  resize.observe(container);
  return()=>{cancelAnimationFrame(frame);resize.disconnect();map.remove();labels.replaceChildren();};
}
