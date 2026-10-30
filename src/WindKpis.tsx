import type { CSSProperties } from 'react';
import Icon from './Icon';
import { formatUtc, windFromVector, windSummary, type WindDataset } from './data/wind';

export default function WindKpis({dataset,connectionError}:{dataset:WindDataset;connectionError:boolean}) {
  const summary=windSummary(dataset),current=dataset.currentObservation??(dataset.mode==='demo'?dataset.frames[0]:undefined);
  const from=current?.eastKt!==null&&current?.eastKt!==undefined&&current.northKt!==null?windFromVector(current.eastKt,current.northKt):null;
  const scale=Math.max(20,Math.ceil(Math.max(summary.current??0,summary.maximum??0)/10)*10);
  const complete=summary.count===48;
  const cards=[
    {label:'Current wind',period:null,value:summary.current,caption:from===null?'Direction unavailable':`From ${String(Math.round(from)%360).padStart(3,'0')}°T`,detail:summary.observedAt?`Observed ${formatUtc(summary.observedAt)} UTC`:'No current observation',icon:'wind' as const},
    {label:'Max wind',period:'48h',value:summary.maximum,caption:summary.maximumAt?`Peak ${new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(summary.maximumAt))} UTC`:'Forecast unavailable',detail:complete?'48 hourly forecasts':`${summary.count} of 48 hours available`,icon:'arrow' as const},
    {label:'Average wind',period:'48h',value:summary.average,caption:'Mean hourly wind speed',detail:complete?'48 hourly forecasts':`${summary.count} of 48 hours available`,icon:'wind' as const},
  ];
  return <section className="wind-kpi-section" aria-label="Main wind indicators"><div className="wind-kpis">{cards.map(card=><article className={`wind-kpi ${card.value===null?'is-unavailable':''}`} key={card.label}>
    <div className="kpi-header"><h2>{card.label}{card.period&&<span> ({card.period})</span>}</h2><span className="kpi-symbol"><Icon name={card.icon} size={17}/></span></div>
    <div className="kpi-body"><div className="kpi-reading"><p className="kpi-number"><span>{card.value===null?'—':card.value.toFixed(1)}</span><span className="kpi-unit">knots</span></p><p className="kpi-caption">{card.caption}</p></div><div className="kpi-gauge" role="img" aria-label={card.value===null?'No wind value available':`${card.value.toFixed(1)} knots on a 0 to ${scale} knot scale`} style={{'--wind-level':`${card.value===null?0:Math.min(100,card.value/scale*100)}%`} as CSSProperties}><span className="gauge-top">{scale}</span><div className="gauge-track"><span className="gauge-mark"/><span className="gauge-fill"/></div><span className="gauge-zero">0</span></div></div>
    <div className="kpi-detail"><span className={`kpi-source-dot ${connectionError?'is-offline':''}`}/>{connectionError?'Last received data':card.detail}</div>
  </article>)}</div><p className="kpi-note"><span>Total wind speed · gauges share a 0–{scale} kt scale.</span><span>Forecast issued {formatUtc(dataset.generatedAt)} UTC{!complete?' · Partial coverage':''}</span></p></section>;
}
