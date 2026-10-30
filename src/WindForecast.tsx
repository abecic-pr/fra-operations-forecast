import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { DEPARTURE_LIMIT_KT, comparisonPairs, formatUtc, frameAt, type WindView } from './data/wind';

type PlotPoint = { time: number; value: number; resolution?:number };
function segments(points: PlotPoint[], maxGap: number) {
  const result: PlotPoint[][]=[];
  points.forEach(point=>{const last=result.at(-1);if(!last||point.time-last.at(-1)!.time>Math.min(maxGap,Math.min(point.resolution??60,last.at(-1)!.resolution??60)*60000*1.1))result.push([point]);else last.push(point);});
  return result;
}
export default function WindForecast({dataset,hour,horizon,playing,onHour,onHorizon,onPlaying,now=Date.now(),connectionError,hideHorizon=false}:WindView&{hideHorizon?:boolean}) {
  const chartContainer=useRef<HTMLDivElement>(null);
  const [size,setSize]=useState({width:360,height:260});
  useEffect(()=>{if(!chartContainer.current)return;const observer=new ResizeObserver(([entry])=>{const{width,height}=entry.contentRect;if(width>0&&height>0)setSize({width,height});});observer.observe(chartContainer.current);return()=>observer.disconnect();},[]);
  const frame=frameAt(dataset,hour), origin=Date.parse(dataset.generatedAt), start=origin-6*3600000, end=origin+horizon*3600000;
  const observations=(dataset.observations??[]).filter(p=>Date.parse(p.validTime)>=start&&Date.parse(p.validTime)<=Math.min(now,end));
  const historical=new Map<number, {time:number;value:number;issued:number}>();
  for(const point of dataset.issuedForecasts??[]){const time=Date.parse(point.validTime),issued=Date.parse(point.issuedAt);if(time>=start&&time<=now&&issued<time&&(!historical.has(time)||historical.get(time)!.issued<issued))historical.set(time,{time,value:point.tailwindKt,issued});}
  const forecastPoints:PlotPoint[]=[...historical.values(),...(dataset.planningFrames??dataset.frames).filter(p=>p.tailwindKt!==null&&Date.parse(p.validTime)>now&&Date.parse(p.validTime)<=end).map(p=>({time:Date.parse(p.validTime),value:p.tailwindKt!,resolution:p.resolutionMinutes}))].sort((a,b)=>a.time-b.time);
  const measuredPoints=observations.map(p=>({time:Date.parse(p.validTime),value:p.tailwindKt}));
  const pairs=comparisonPairs(observations,dataset.issuedForecasts??[],now),mae=pairs.length?pairs.reduce((sum,p)=>sum+Math.abs(p.error),0)/pairs.length:null;
  const max=Math.max(25,Math.ceil(Math.max(...forecastPoints.map(p=>p.value),...measuredPoints.map(p=>p.value),0)/5)*5);
  const {width,height}=size,left=28,right=10,top=30,bottom=28;
  const x=(time:number)=>left+(time-start)/(end-start)*(width-left-right),y=(value:number)=>height-bottom-value/max*(height-top-bottom);
  const line=(points:PlotPoint[])=>points.map(p=>`${x(p.time)},${y(p.value)}`).join(' ');
  const latest=observations.at(-1);
  return <section className="glass forecast-panel" aria-label="Runway 18 wind forecast">
    <div className="panel-heading"><h2>Tailwind forecast</h2><Icon name="wind" size={21}/></div>
    {!hideHorizon&&<div className="forecast-toolbar"><div className="segmented" aria-label="Forecast horizon">{[6,12,24,48].map(value=><button key={value} aria-pressed={horizon===value} className={horizon===value?'is-active':''} onClick={()=>onHorizon(value)}>{value} hours</button>)}</div></div>}
    <div className="chart-key"><span><i className="forecast-key"/>Forecast</span><span><i className="measured-key"/>Measured <small>provisional</small></span><span className="chart-unit">kt</span></div>
    <div className="chart-container" ref={chartContainer}>
      <svg key={horizon} className="wind-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Runway 18 tailwind forecast in blue and ${observations.length} checked provisional measured values in green; current time ${formatUtc(new Date(now).toISOString())} UTC`}>
        <defs><linearGradient id="wind-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#55a7ff" stopOpacity=".2"/><stop offset="1" stopColor="#55a7ff" stopOpacity="0"/></linearGradient><clipPath id="above-limit"><rect x={left} y={top} width={width-left-right} height={Math.max(0,y(DEPARTURE_LIMIT_KT)-top)}/></clipPath></defs>
        <rect x={left} y={y(DEPARTURE_LIMIT_KT)} width={width-left-right} height={y(DEPARTURE_LIMIT_KT-4)-y(DEPARTURE_LIMIT_KT)} fill="#e4bd58" fillOpacity=".1"/>
        {[0,5,10,15,20,25].filter(v=>v<=max).map(value=><g key={value}><line x1={left} x2={width-right} y1={y(value)} y2={y(value)} className="chart-grid"/><text x={left-7} y={y(value)+3} textAnchor="end">{value}</text></g>)}
        {[0,.25,.5,.75,1].map(ratio=>{const time=start+ratio*(end-start);return <text key={ratio} x={x(time)} y={height-7} textAnchor={ratio===0?'start':ratio===1?'end':'middle'}>{formatUtc(new Date(time).toISOString())}</text>;})}
        <line x1={left} x2={width-right} y1={y(DEPARTURE_LIMIT_KT)} y2={y(DEPARTURE_LIMIT_KT)} className="limit-line"/><text x={width-right} y={y(DEPARTURE_LIMIT_KT)-7} textAnchor="end" className="limit-label">Departure limit · 15 kt</text>
        {segments(forecastPoints,90*60000).map((points,i)=>{const area=`M ${x(points[0].time)} ${y(0)} L ${line(points).replaceAll(' ',' L ')} L ${x(points.at(-1)!.time)} ${y(0)} Z`;return <g key={i}><path d={area} fill="url(#wind-fill)"/><path d={area} fill="#ff6b5d" fillOpacity=".18" clipPath="url(#above-limit)"/><polyline points={line(points)} className="wind-line"/></g>;})}
        {segments(measuredPoints,20*60000).map((points,i)=><polyline key={i} points={line(points)} className="measured-line"/>)}
        {measuredPoints.map(point=><circle key={point.time} cx={x(point.time)} cy={y(point.value)} r="2" className="measured-point"><title>{formatUtc(new Date(point.time).toISOString())} UTC · {point.value.toFixed(1)} kt measured · DWD 01420 provisional</title></circle>)}
        {now>=start&&now<=end&&<g aria-label={`Current time ${formatUtc(new Date(now).toISOString())} UTC`}><line x1={x(now)} x2={x(now)} y1={top-5} y2={height-bottom} className="now-line"/><text x={Math.max(left+42,Math.min(width-right-42,x(now)))} y={14} textAnchor="middle" className="now-label">Now {formatUtc(new Date(now).toISOString())}</text></g>}
        {hour>0&&<line x1={x(origin+hour*3600000)} x2={x(origin+hour*3600000)} y1={top} y2={height-bottom} className="hover-line"/>}
        <rect x={left} y={top} width={width-left-right} height={height-top-bottom} fill="transparent" style={{cursor:'crosshair'}} onClick={event=>{const rect=event.currentTarget.ownerSVGElement!.getBoundingClientRect();const position=(event.clientX-rect.left)/rect.width*width;const selected=(start+(position-left)/(width-left-right)*(end-start)-origin)/3600000;if(selected>=0){onPlaying(false);onHour(Math.max(0,Math.min(horizon,Math.round(selected*4)/4)));}}}/>
      </svg>
    </div>
    <div className="comparison-status"><span className="live-clock">{formatUtc(new Date(now).toISOString())} UTC</span><span>{mae===null?'Awaiting forecast matches':`MAE ${mae.toFixed(1)} kt · ${pairs.length} matches`}</span></div>
    <div className="forecast-timeline"><button className="play-forecast" aria-label={playing?'Pause forecast':'Play forecast'} onClick={()=>onPlaying(!playing)}><span key={String(playing)} className="control-glyph"><Icon name={playing?'pause':'play'} size={16}/></span></button><div className="timeline-content"><label htmlFor="forecast-time">{hour===0?'Latest reading':`+${Number(hour.toFixed(2))}h`}<span>{formatUtc(frame.validTime)} UTC</span></label><input id="forecast-time" aria-label="Forecast time" type="range" min="0" max={horizon} step="0.25" value={hour} onChange={event=>{onPlaying(false);onHour(Number(event.target.value));}}/></div><output className="timeline-value">{frame.tailwindKt===null?'—':frame.tailwindKt.toFixed(1)}<small> kt</small></output></div>
    <div className="chart-footer"><span>{connectionError?'Connection lost · showing last received data':latest?`DWD 01420 · measured ${formatUtc(latest.validTime)} UTC`:'No checked measurements available'}</span><span>{latest?'Provisional':'UTC'}</span></div>
  </section>;
}
