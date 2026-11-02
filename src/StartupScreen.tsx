import { useEffect, useRef, useState, type CSSProperties } from 'react';
import Icon from './Icon';

// Sources fetched by fra_forecast.pipeline.refresh on a cold start.
const sources=['Airport wind sensor','METAR & TAF','ICON weather models','Operating direction'];

export default function StartupScreen({error}:{error:boolean}) {
  const host=useRef<HTMLDivElement>(null),wind=useRef<HTMLCanvasElement>(null),labels=useRef<HTMLDivElement>(null);
  const card=useRef<HTMLElement>(null),explain=useRef<HTMLElement>(null);
  const [westbound,setWestbound]=useState(true),[scene,setScene]=useState<'loading'|'ready'|'failed'>('loading');
  useEffect(()=>{
    let stop:(()=>void)|undefined,cancelled=false;
    const still=error||window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const padding=()=>{ // keep the airport clear of the two panels
      const box=card.current!.getBoundingClientRect(),top=explain.current!.getBoundingClientRect().bottom,wide=window.innerWidth>=900;
      return wide?{top:top+16,bottom:32,left:box.right+24,right:32}:{top:top+12,bottom:window.innerHeight-box.top+8,left:12,right:12};
    };
    import('./StartupScene').then(({startScene})=>{
      if(cancelled)return;
      stop=startScene(host.current!,wind.current!,labels.current!,{still,onPhase:setWestbound,onReady:()=>setScene('ready'),padding});
    }).catch(()=>{if(!cancelled)setScene('failed');}); // no WebGL or chunk: the panels still explain the wait
    return()=>{cancelled=true;stop?.();};
  },[error]);

  // The scene is an illustration; no current operating direction is known until the forecast arrives.
  return <main className={`startup is-${scene}${error?' is-error':''}`}>
    <div ref={host} className="startup-map" aria-hidden="true"/>
    <canvas ref={wind} className="startup-wind" aria-hidden="true"/>
    <div ref={labels} className="startup-labels" aria-hidden="true"/>
    <aside ref={explain} className="glass startup-explain" aria-hidden="true">
      <p className="startup-heading"><strong key={String(westbound)}>{westbound?'Westbound':'Eastbound'}</strong><span>{westbound?'25 · 250°T':'07 · 70°T'}</span></p>
      <p>Wind from the {westbound?'west':'east'}: aircraft land and take off into it.</p>
      <div className="aircraft-key"><span className="arrival-key">Landing</span><span className="departure-key">Departure</span></div>
      <small>Illustration · 18 always south · not today’s direction</small>
    </aside>
    <section ref={card} className="glass startup-card" role={error?'alert':'status'} aria-live="polite">
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
