import {airportDirection,components18,runwayPresentation,vectorFromWind,windFromVector,type WindDataset,type WindFrame} from './wind';
export type AirportFlow='07'|'25'|null;
export function runwayConfiguration(direction:AirportFlow){
 const heading=direction==='07'?70:direction==='25'?250:null;
 return [
  {ref:'07L/25R',name:'Northwest',operation:'Landing',end:direction==='07'?'07L':direction==='25'?'25R':null,heading},
  {ref:'07R/25L',name:'South',operation:'Landing',end:direction==='07'?'07R':direction==='25'?'25L':null,heading},
  {ref:'07C/25C',name:'Centre',operation:'Departure',end:direction==='07'?'07C':direction==='25'?'25C':null,heading},
  {ref:'18',name:'West',operation:'Departure',end:'18',heading:180},
 ];
}
export function windBearing(frame:WindFrame|undefined){
 if(!frame||frame.eastKt===null||frame.northKt===null)return {label:'Wind direction not supplied',degrees:null};
 if(Math.hypot(frame.eastKt,frame.northKt)<.01)return {label:'Calm',degrees:null};
 const degrees=windFromVector(frame.eastKt,frame.northKt),cardinal=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'][Math.round(degrees/22.5)%16];
 return {label:`${String(Math.round(degrees)%360).padStart(3,'0')}° ${cardinal}`,degrees};
}
export function directionRows(dataset:WindDataset,horizon:number,now:number,disconnected=false){
 const origin=Date.parse(dataset.generatedAt),end=origin+horizon*3600000;
 const make=(frame:WindFrame|undefined,hour:number,at:number,current:boolean)=>{
  const flow=airportDirection(dataset,hour,disconnected);
  return {at,hour,current,wind:windBearing(frame),flow,runways:runwayConfiguration(flow.direction),status18:frame?runwayPresentation(frame,disconnected):null,change:false};
 };
 const current=make(dataset.currentObservation,0,now,true);
 const future=dataset.frames.filter(f=>Date.parse(f.validTime)>now&&Date.parse(f.validTime)<=end).map(f=>make(f,(Date.parse(f.validTime)-origin)/3600000,Date.parse(f.validTime),false));
 future.forEach((row,i)=>{const before=i?future[i-1]:current;row.change=Boolean(row.flow.direction&&before.flow.direction&&row.flow.direction!==before.flow.direction&&(i?row.at-before.at<=66*60000:row.at-now<=66*60000));});
 return [current,...future];
}
/** Deliberate example, with switches that demonstrate the existing airport-wide rule. */
export function directionExample(base:number):WindDataset{
 const make=(hours:number):WindFrame=>{const from=hours<3?70:hours<8?250:70,vector=vectorFromWind(12,from),gustKt=18;return {validTime:new Date(base+hours*3600000).toISOString(),...vector,gustKt,...components18(vector.eastKt,vector.northKt,gustKt),probability:null,operatingDirection:from===70?'07':'25',directionBasis:'challenge_rules_raw_weather',resolutionMinutes:60};};
 return {mode:'demo',generatedAt:new Date(base).toISOString(),frames:Array.from({length:49},(_,i)=>make(i)),spatialMode:'uniform-airport',source:'Simulated direction-change example',currentObservation:make(0),operations:{direction:'07',observedAt:new Date(base).toISOString(),since:null,source:'Simulated airport direction'}};
}
