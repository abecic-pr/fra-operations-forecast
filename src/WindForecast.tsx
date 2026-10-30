import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { DEPARTURE_LIMIT_KT, formatUtc, frameAt, type WindView } from './data/wind';

export default function WindForecast({ dataset, hour, horizon, playing, onHour, onHorizon, onPlaying }: WindView) {
  const chartContainer = useRef<HTMLDivElement>(null);
  const [chartSize, setChartSize] = useState({ width: 480, height: 230 });
  useEffect(() => {
    if (!chartContainer.current) return;
    const observer = new ResizeObserver(([entry]) => { const { width, height } = entry.contentRect; if (width > 0 && height > 0) setChartSize({ width, height }); });
    observer.observe(chartContainer.current); return () => observer.disconnect();
  }, []);
  const frame = frameAt(dataset, hour);
  const values = Array.from({ length: horizon + 1 }, (_, index) => frameAt(dataset, index).tailwindKt);
  const max = Math.max(25, Math.ceil(Math.max(...values.map(value => value ?? 0)) / 5) * 5);
  const { width, height } = chartSize, left = 30, right = 12, top = 24, bottom = 30;
  const x = (h: number) => left + h / horizon * (width-left-right);
  const y = (value: number) => height-bottom-value/max*(height-top-bottom);
  // Separate paths at missing values rather than bridging gaps in real data.
  const segments: { h: number; value: number }[][] = [];
  values.forEach((value, h) => { if (value === null) { if (segments.at(-1)?.length) segments.push([]); } else { if (!segments.length) segments.push([]); segments.at(-1)!.push({ h, value }); } });
  return <section className="glass forecast-panel" aria-label="Runway 18 wind forecast">
    <div className="panel-heading"><div><p className="overline">Runway 18 · departures</p><h2>Tailwind forecast</h2></div><Icon name="wind" size={23} /></div>
    <div className="forecast-toolbar"><div className="segmented" aria-label="Forecast horizon">{[12,24,48].map(value => <button key={value} aria-pressed={horizon===value} className={horizon===value?'is-active':''} onClick={() => onHorizon(value)}>{value} hours</button>)}</div></div>
    <div className="chart-caption"><span>Tailwind <span className="subtle">· kt</span></span><span className="sample-label">{dataset.mode==='demo'?'Demo forecast':'Airport forecast'}</span></div>
    <div className="chart-container" ref={chartContainer}>
      <svg className="wind-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${dataset.mode==='demo'?'Synthetic demo':'Forecast'} Runway 18 tailwind over ${horizon} hours`}>
        <defs><linearGradient id="wind-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#55a7ff" stopOpacity=".26"/><stop offset="1" stopColor="#55a7ff" stopOpacity=".01"/></linearGradient><clipPath id="above-limit"><rect x={left} y={top} width={width-left-right} height={y(DEPARTURE_LIMIT_KT)-top}/></clipPath></defs>
        {Array.from({length:6},(_,i)=>max*i/5).map(value=><g key={value}><line x1={left} x2={width-right} y1={y(value)} y2={y(value)} className="chart-grid"/><text x={left-10} y={y(value)+4} textAnchor="end">{value}</text></g>)}
        {[0,horizon/4,horizon/2,horizon*3/4,horizon].map(h=><text key={h} x={x(h)} y={height-7} textAnchor={h===horizon?'end':h===0?'start':'middle'}>{h===0?'Now':`+${h}h`}</text>)}
        <line x1={left} x2={width-right} y1={y(DEPARTURE_LIMIT_KT)} y2={y(DEPARTURE_LIMIT_KT)} className="limit-line"/>
        <text x={width-right} y={y(DEPARTURE_LIMIT_KT)-8} textAnchor="end" className="limit-label">Departure limit · 15 kt</text>
        {segments.filter(segment=>segment.length).map((segment,index)=>{const points=segment.map(p=>`${x(p.h)},${y(p.value)}`).join(' ');const area=`M ${x(segment[0].h)} ${y(0)} L ${points.replaceAll(' ',' L ')} L ${x(segment.at(-1)!.h)} ${y(0)} Z`;return <g key={index}><path d={area} fill="url(#wind-fill)"/><path d={area} fill="#ff6b5d" fillOpacity=".22" clipPath="url(#above-limit)"/><polyline points={points} className="wind-line"/></g>;})}
        <line x1={x(hour)} x2={x(hour)} y1={top} y2={height-bottom} className="hover-line"/>
        {frame.tailwindKt!==null&&<circle cx={x(hour)} cy={y(frame.tailwindKt)} r="4" fill="#fff" stroke="#75b8ff" strokeWidth="2"/>}
        <rect x={left} y={top} width={width-left-right} height={height-top-bottom} fill="transparent" style={{cursor:'crosshair'}} onClick={event=>{const rect=event.currentTarget.ownerSVGElement!.getBoundingClientRect();const position=(event.clientX-rect.left)/rect.width*width;onHour(Math.max(0,Math.min(horizon,Math.round((position-left)/(width-left-right)*horizon))));}}/>
      </svg>
    </div>
    <div className="forecast-timeline"><button className="play-forecast" aria-label={playing?'Pause forecast':'Play forecast'} onClick={()=>onPlaying(!playing)}><Icon name={playing?'pause':'play'} size={17}/></button><div className="timeline-content"><label htmlFor="forecast-time">{hour===0?'Now':`+${Number(hour.toFixed(2))}h`}<span>{formatUtc(frame.validTime)} UTC</span></label><input id="forecast-time" aria-label="Forecast time" type="range" min="0" max={horizon} step="0.25" value={hour} onChange={event=>{onPlaying(false);onHour(Number(event.target.value));}}/></div><output className="timeline-value">{frame.tailwindKt===null?'—':frame.tailwindKt.toFixed(1)}<small> kt</small></output></div>
    <div className="chart-footer"><span>{dataset.mode==='demo'?'Synthetic weather · not a live forecast':dataset.source}</span><span>Runway heading 180°T</span></div>
  </section>;
}
