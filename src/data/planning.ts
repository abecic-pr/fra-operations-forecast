import {components18,runwayComponents,runwayPresentation,vectorFromWind,type WindDataset,type WindFrame} from './wind';
import type {TrafficBoard,TrafficFlight} from './traffic';
export type RiskWindow={id:string;kind:'restricted'|'caution';start:number;earliest:number|null;last:number;end:number|null;resolution:number;samples:WindFrame[]};
export type FlightReview={flight:TrafficFlight;assigned18:boolean;candidate:string|null;reason:string};
export function planningState(frame:WindFrame){
  const status=runwayPresentation(frame);
  if(status.tone==='red')return 'restricted';
  if(frame.weatherState==='unknown'||frame.tailwindKt===null||frame.crosswindKt===null||frame.gustCrosswindKt===null)return 'unknown';
  return status.tone==='yellow'?'caution':'clear';
}
export function forecastWindows(dataset:WindDataset,now:number){
  const points=dataset.planningFrames?.length?dataset.planningFrames:dataset.frames;
  const step=(a:WindFrame,b:WindFrame)=>Date.parse(b.validTime)-Date.parse(a.validTime)<=Math.min(a.resolutionMinutes??60,b.resolutionMinutes??60)*60000*1.1;
  const windows:RiskWindow[]=[];
  for(let i=0;i<points.length;i++){
    const frame=points[i],kind=planningState(frame);if(kind!=='restricted'&&kind!=='caution')continue;
    const start=i,samples=[frame];
    while(i+1<points.length&&planningState(points[i+1])===kind&&step(points[i],points[i+1]))samples.push(points[++i]);
    const previous=points[start-1],next=points[i+1];
    const end=next&&step(points[i],next)&&planningState(next)!=='unknown'?Date.parse(next.validTime):null;
    const last=Date.parse(points[i].validTime);
    if((end??last)<=now)continue;
    const at=Date.parse(frame.validTime);
    windows.push({id:`${kind}-${at}`,kind,start:at,earliest:previous&&step(previous,frame)&&planningState(previous)!=='unknown'?Date.parse(previous.validTime):null,last,end,resolution:Math.max(...samples.map(f=>f.resolutionMinutes??60)),samples});
  }
  const future=points.filter(f=>Date.parse(f.validTime)>now&&Date.parse(f.validTime)<=now+48*3600000);
  return {windows,checked:future.filter(f=>planningState(f)!=='unknown').length,total:future.length,through:future.at(-1)?.validTime??null,continuous:future.length>0&&Date.parse(future[0].validTime)-now<=(future[0].resolutionMinutes??60)*60000*1.1&&Date.parse(future.at(-1)!.validTime)>=now+47*3600000&&future.every((f,i)=>!i||step(future[i-1],f)),finest:future.length?Math.min(...future.map(f=>f.resolutionMinutes??60)):null};
}
export function centreCandidate(dataset:WindDataset,at:number){
  const points=dataset.planningFrames?.length?dataset.planningFrames:dataset.frames;
  const next=points.find(f=>Date.parse(f.validTime)>=at),previous=points.filter(f=>Date.parse(f.validTime)<=at).at(-1);
  if(!next||!previous||Date.parse(next.validTime)-Date.parse(previous.validTime)>Math.min(next.resolutionMinutes??60,previous.resolutionMinutes??60)*60000*1.1)return null;
  const samples=next===previous?[next]:[previous,next],od=next.operatingDirection;
  if(!od||samples.some(f=>f.operatingDirection!==od||f.weatherState==='unknown'))return null;
  const hnext=dataset.frames.find(f=>Date.parse(f.validTime)>=at),hprevious=dataset.frames.filter(f=>Date.parse(f.validTime)<=at).at(-1);
  if(!hnext||!hprevious||hnext.operatingDirection!==od||hprevious.operatingDirection!==od||Date.parse(hnext.validTime)-Date.parse(hprevious.validTime)>66*60000)return null;
  const suitable=samples.every(f=>{const c=runwayComponents(f,od==='07'?70:250);return c.tailwind!==null&&c.tailwind<11&&c.crosswind!==null&&c.crosswind<36&&c.gustCrosswind!==null&&c.gustCrosswind<36;});
  return suitable?od==='07'?'07C':'25C':null;
}
export function flightReviews(dataset:WindDataset,board:TrafficBoard|null,window:RiskWindow|null,now:number):FlightReview[]{
  if(!board||!window||now-Date.parse(board.generatedAt)>15*60000||Date.parse(board.generatedAt)>now+300000||now-Date.parse(dataset.generatedAt)>7200000||Date.parse(dataset.generatedAt)>now+300000)return [];
  return board.flights.filter(f=>f.operation==='departure'&&(f.runway==='18'||f.runway===null)&&Date.parse(f.at)>=now&&Date.parse(f.at)>=(window.earliest??window.start)&&Date.parse(f.at)<=(window.end??window.last)&&!/cancel|departed|off.block/i.test(f.status)).map(f=>({flight:f,assigned18:f.runway==='18',candidate:f.runway==='18'?centreCandidate(dataset,Date.parse(f.at)):null,reason:f.runway==='18'?'Assigned to 18 · board-time overlap':'Runway unassigned · possible overlap'}));
}
/** Explicit design scenario: quarter-hour samples and a half-hour restriction, never live claims. */
export function examplePlan(base:number):{dataset:WindDataset;board:TrafficBoard}{
  const make=(minutes:number):WindFrame=>{const speed=minutes>=120&&minutes<150?16:minutes>=60&&minutes<120?12:7;const v=vectorFromWind(speed,0),gustKt=speed+4;return {validTime:new Date(base+minutes*60000).toISOString(),...v,gustKt,...components18(v.eastKt,v.northKt,gustKt),probability:null,operatingDirection:'07',directionBasis:'challenge_rules_raw_weather',resolutionMinutes:15};};
  const planningFrames=Array.from({length:193},(_,i)=>make(i*15));
  const flights:TrafficFlight[]=[90,130,140,170].map((m,i)=>({id:`plan-demo-${i}`,number:`DEMO ${401+i}`,operation:'departure',airport:['London','Madrid','Paris','Rome'][i],at:new Date(base+m*60000).toISOString(),estimated:false,runway:i===2?null:'18',runwayEnd:i===2?null:'18',position:null,status:'Design example'}));
  return {dataset:{mode:'demo',generatedAt:new Date(base).toISOString(),source:'Illustrative planning scenario',spatialMode:'uniform-airport',frames:planningFrames.filter((_,i)=>i%4===0),planningFrames,currentObservation:make(0),operations:{direction:'07',observedAt:new Date(base).toISOString(),since:null,source:'Simulated airport direction'}},board:{generatedAt:new Date(base).toISOString(),partial:false,flights}};
}
