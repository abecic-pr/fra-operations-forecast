import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import type { FeatureCollection } from 'geojson';
import Icon from './Icon';
import { formatUtc } from './data/wind';
import 'leaflet/dist/leaflet.css';

type Visual = {type:'tailwind_chart'|'crosswind_chart'|'airport_map';title:string;generated_at?:string;unit?:string;limit?:number;points?:{time:string;value:number|null}[]};
type Reply = {answer:string;explanation:string;sources:string[];visuals:Visual[];mode:'ai'|'preview';as_of:string;model?:string};
type Message = {id:number;role:'user'|'assistant';text:string;reply?:Reply};
function AirportChatMap({onOpenMap}:{onOpenMap:()=>void}) {
  const host=useRef<HTMLDivElement>(null);
  const [error,setError]=useState(false);
  useEffect(()=>{
    if(!host.current)return;
    const controller=new AbortController(),map=L.map(host.current,{scrollWheelZoom:false}).setView([50.025,8.53],13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).on('tileerror',()=>setError(true)).addTo(map);
    fetch('/data/frankfurt-airport.geojson',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then((data:FeatureCollection)=>{if(controller.signal.aborted)return;const runway=L.geoJSON(data,{filter:f=>f.properties?.aeroway==='runway'&&f.properties?.ref==='18',style:{color:'#274eb0',weight:7,opacity:.85}}).bindTooltip('18 · Southbound departures').addTo(map);if(runway.getBounds().isValid())map.fitBounds(runway.getBounds().pad(.25));}).catch(()=>{if(!controller.signal.aborted)setError(true);});
    const observer=new ResizeObserver(()=>map.invalidateSize());observer.observe(host.current);
    return()=>{controller.abort();observer.disconnect();map.remove();};
  },[]);
  return <figure className="bot-map"><div ref={host} className="bot-map-canvas" aria-label="Interactive OpenStreetMap of Frankfurt Airport Runway 18"/><figcaption><span>{error?'Some map data could not load.':'Runway 18 · location, not operational status'}</span><button onClick={onOpenMap}>Open map<Icon name="arrow" size={13}/></button></figcaption></figure>;
}
function ForecastGraphic({visual}:{visual:Visual}) {
  const points=visual.points??[], values=points.filter(p=>typeof p.value==='number'&&Number.isFinite(p.value));
  if(!values.length)return <p className="bot-no-data">No forecast values available for this chart.</p>;
  const width=560,height=210,left=30,right=12,top=22,bottom=30,limit=visual.limit??15;
  const start=Date.parse(points[0].time),end=Date.parse(points.at(-1)!.time),max=Math.ceil(Math.max(limit*1.2,...values.map(p=>p.value!))/5)*5;
  const x=(time:string)=>left+(Date.parse(time)-start)/Math.max(1,end-start)*(width-left-right),y=(v:number)=>height-bottom-v/max*(height-top-bottom);
  const segments:{time:string;value:number}[][]=[];
  let current:{time:string;value:number}[]=[];
  points.forEach(p=>{if(p.value===null){current=[];return;}if(!current.length||Date.parse(p.time)-Date.parse(current.at(-1)!.time)>90*60000){current=[];segments.push(current);}current.push({time:p.time,value:p.value});});
  return <figure className="bot-chart"><figcaption>{visual.title}<span>Forecast · kt · UTC</span></figcaption><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${visual.title}, saved hourly forecast in knots. Departure wind limit ${limit} knots.`}>
    {[0,max/2,max].map(value=><g key={value}><line x1={left} x2={width-right} y1={y(value)} y2={y(value)} className="bot-chart-grid"/><text x={left-8} y={y(value)+3} textAnchor="end">{value}</text></g>)}
    <line x1={left} x2={width-right} y1={y(limit)} y2={y(limit)} className="bot-limit"/><text x={width-right} y={y(limit)-6} textAnchor="end">Wind limit · {limit} kt</text>
    {segments.map((segment,i)=><polyline key={i} points={segment.map(p=>`${x(p.time)},${y(p.value)}`).join(' ')} className="bot-wind-line"/>)}
    {values.map(p=><circle key={p.time} cx={x(p.time)} cy={y(p.value!)} r="2" fill="#2588dd"><title>{formatUtc(p.time)} UTC · {p.value!.toFixed(1)} kt</title></circle>)}
    {[points[0],points[Math.floor((points.length-1)/2)],points.at(-1)!].filter((p,i,a)=>a.findIndex(v=>v.time===p.time)===i).map(p=><text key={p.time} x={x(p.time)} y={height-8} textAnchor={p===points[0]?'start':p===points.at(-1)?'end':'middle'}>{formatUtc(p.time)}</text>)}
  </svg><p>Forecast issued {visual.generated_at?new Date(visual.generated_at).toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}):'unknown'} UTC · raw weather baseline</p></figure>;
}
export default function WeatherBot({selectedTime,onOpenMap}:{selectedTime:string;onOpenMap:()=>void}) {
  const [configured,setConfigured]=useState<boolean|null>(null),[messages,setMessages]=useState<Message[]>([]),[question,setQuestion]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const [preview,setPreview]=useState<Reply|null>(null);
  const abort=useRef<AbortController|null>(null),counter=useRef(0);
  const transcript=useRef<HTMLDivElement>(null);
  useEffect(()=>{const controller=new AbortController();const check=()=>fetch('/api/ui-chat/status',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(s=>setConfigured(s.configured===true)).catch(()=>{if(!controller.signal.aborted)setConfigured(false);});void check();const timer=window.setInterval(check,15000);return()=>{controller.abort();clearInterval(timer);abort.current?.abort();};},[]);
  useEffect(()=>{if(transcript.current)transcript.current.scrollTo({top:transcript.current.scrollHeight,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});},[messages,busy,error]);
  async function showPreview(){setError('');try{const r=await fetch('/api/ui-chat/preview');if(!r.ok)throw Error('Saved data is unavailable.');setPreview(await r.json());}catch{setError('The data preview could not load. Please try again.');}}
  async function send(text=question){
    if(!text.trim()||busy)return;
    if(!configured){setError('The AI connection is pending. You can explore the real-data preview below.');return;}
    const history=messages.slice(-10).map(m=>({role:m.role,content:m.text.slice(0,3000)}));
    setMessages(previous=>[...previous,{id:++counter.current,role:'user',text:text.trim()}]);setQuestion('');setError('');setBusy(true);setPreview(null);
    const controller=new AbortController();abort.current=controller;
    try{const r=await fetch('/api/ui-chat',{method:'POST',headers:{'Content-Type':'application/json','X-FRA-Chat':'1'},body:JSON.stringify({message:text.trim(),history,selected_time:selectedTime}),signal:controller.signal});const data=await r.json();if(!r.ok)throw Error(data.error||'The bot could not answer.');if(typeof data.answer!=='string'||!Array.isArray(data.visuals))throw Error('The bot returned an invalid answer.');setMessages(previous=>[...previous,{id:++counter.current,role:'assistant',text:data.answer,reply:data}]);}catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Connection unavailable. Please try again.');}finally{setBusy(false);abort.current=null;}
  }
  function renderReply(reply:Reply){return <><p className="bot-answer">{reply.answer}</p>{reply.visuals.map((v,i)=>v.type==='airport_map'?<AirportChatMap key={i} onOpenMap={onOpenMap}/>:<ForecastGraphic key={i} visual={v}/>)}<details className="bot-evidence"><summary>Explanation & sources</summary><p>{reply.explanation}</p><ul>{reply.sources.map(source=><li key={source}>{source}</li>)}</ul><small>Data checked {formatUtc(reply.as_of)} UTC{reply.model?` · ${reply.model}`:''}</small></details></>;}
  return <section className="weather-bot" aria-labelledby="bot-title"><div className="bot-heading"><div><span className="bot-emblem"><Icon name="sparkles" size={19}/></span><h2 id="bot-title">AI Weather Bot</h2></div><span className="bot-connection"><i className={configured?'connected':''}/>{configured?'OpenAI configured':configured===null?'Connecting…':'AI connection pending'}</span>{messages.length>0&&<button className="bot-clear" disabled={busy} onClick={()=>{setMessages([]);setError('');setPreview(null);}}>New chat</button>}</div>
    <div className="bot-transcript" ref={transcript} role="log" aria-label="Weather bot conversation" aria-live="polite">{!messages.length&&!preview&&<div className="bot-welcome"><h3>A clearer view of what’s ahead.</h3><p>Ask about wind, departures or Runway 18. Answers can include charts and an interactive map.</p><div className="bot-suggestions">{['How does the wind look for the next 6 hours?','Show Runway 18 on a map','What data is missing?'].map(text=><button key={text} onClick={()=>{setQuestion(text);if(configured)void send(text);}}>{text}<Icon name="arrow" size={14}/></button>)}</div></div>}{messages.map(m=><article key={m.id} className={`bot-message bot-${m.role}`} aria-label={m.role==='user'?'Your question':'AI answer'}>{m.reply?renderReply(m.reply):<p>{m.text}</p>}</article>)}{preview&&<article className="bot-message bot-assistant" aria-label="Data preview"><span className="bot-preview-label">Real-data preview · AI not connected</span>{renderReply(preview)}</article>}{busy&&<div className="bot-working" role="status"><span/><span/><span/><p>Checking project data and preparing an answer…</p></div>}{error&&<p className="bot-error" role="alert">{error}</p>}</div>
    {!configured&&<div className="bot-setup"><span>Connect OpenAI to ask questions. Your project data is ready.</span><button onClick={()=>void showPreview()}>Preview charts & map<Icon name="arrow" size={14}/></button></div>}
    <form className="bot-compose" onSubmit={e=>{e.preventDefault();void send();}}><textarea aria-label="Ask the AI Weather Bot" placeholder="Ask about weather or runway conditions…" rows={2} maxLength={4000} value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();void send();}}}/><button type="submit" aria-label="Send question" disabled={busy||!question.trim()}><Icon name="send" size={24}/></button></form><p className="bot-footer">Answers use available project data. Wind suitability is separate from official runway status.</p>
  </section>;
}
