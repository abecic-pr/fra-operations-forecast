import type { CSSProperties } from 'react';
import Icon from './Icon';

// Runway centrelines from public/data/frankfurt-airport.geojson, projected to metres (same as the ML page).
const runways=['M-986 -1282L-3606 -305','M-952 751L2790 -640','M2822 -1205L-920 187','M-1516 3986L-1542 15'];
// Sources fetched by fra_forecast.pipeline.refresh on a cold start.
const sources=['Airport wind sensor','METAR & TAF','ICON weather models','Operating direction'];

export default function StartupScreen({error}:{error:boolean}) {
  // No operating direction is shown here: nothing is known until the forecast arrives.
  return <main className={`startup${error?' is-error':''}`}>
    <svg className="startup-wind" viewBox="0 0 1200 800" preserveAspectRatio="none" aria-hidden="true">
      <path d="M-40 180C220 120 420 230 660 170S1020 100 1240 160"/><path d="M-40 330C260 280 460 380 720 320S1040 260 1240 310"/>
      <path d="M-40 500C200 460 480 540 740 490S1060 440 1240 480"/><path d="M-40 650C280 620 540 680 780 640S1080 610 1240 630"/>
    </svg>
    <svg className="startup-runways" viewBox="-3900 -1700 6900 5900" aria-hidden="true">
      {runways.map((d,i)=><g key={d} style={{'--i':i} as CSSProperties}><path className="edge" d={d}/><path className="strip" d={d}/><path className="scan" d={d} pathLength={1000}/></g>)}
    </svg>
    <section className="startup-card" role={error?'alert':'status'} aria-live="polite">
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
