export const parallelRunways=['07L/25R','07C/25C','07R/25L'] as const;
export type ParallelRunway=typeof parallelRunways[number];
export type Movement='landing'|'departure';
export type TrafficFlight={id:string;number:string;operation:Movement;airport:string;at:string;estimated:boolean;runway:ParallelRunway|'18'|null;runwayEnd?:string|null;position:{lat:number;lon:number;heading:number;at:string}|null;status:string};
export type TrafficBoard={generatedAt:string;flights:TrafficFlight[];partial:boolean};
export function runwayPair(value:unknown):ParallelRunway|null{
  return parallelRunways.find(pair=>value===pair||pair.split('/').includes(String(value)))??null;
}
export function adaptTraffic(input:unknown):TrafficBoard{
  if(!input||typeof input!=='object')throw Error('Invalid traffic');const data=input as Record<string,unknown>;
  if(data.schema_version!=='1.0'||!Array.isArray(data.flights)||!Number.isFinite(Date.parse(String(data.generated_at))))throw Error('Unsupported traffic');
  const flights:TrafficFlight[]=data.flights.flatMap((value:unknown)=>{
    if(!value||typeof value!=='object')return [];const row=value as Record<string,unknown>,at=row.estimated_at||row.scheduled_at;
    if(typeof row.id!=='string'||typeof row.number!=='string'||!['landing','departure'].includes(String(row.operation))||!Number.isFinite(Date.parse(String(at))))return [];
    const p=row.position as Record<string,unknown>|null;
    const numeric=(v:unknown)=>typeof v==='number'&&Number.isFinite(v);
    const position=p&&numeric(p.latitude)&&numeric(p.longitude)&&numeric(p.heading_deg_true)&&Number(p.latitude)>=49.7&&Number(p.latitude)<=50.4&&Number(p.longitude)>=8.1&&Number(p.longitude)<=9&&Number(p.heading_deg_true)>=0&&Number(p.heading_deg_true)<=360&&Number.isFinite(Date.parse(String(p.observed_at)))&&typeof p.source_url==='string'&&p.source_url.startsWith('https://')?{lat:Number(p.latitude),lon:Number(p.longitude),heading:Number(p.heading_deg_true),at:String(p.observed_at)}:null;
    return [{id:row.id,number:row.number,operation:row.operation as Movement,airport:String(row.airport??'Airport not supplied'),at:String(at),estimated:Boolean(row.estimated_at),runway:row.assignment_status==='confirmed'?(row.assigned_runway==='18'?'18' as const:runwayPair(row.assigned_runway)):null,runwayEnd:row.assignment_status==='confirmed'&&typeof row.assigned_runway==='string'&&['18','07L','07C','07R','25R','25C','25L'].includes(row.assigned_runway)?row.assigned_runway:null,position,status:String(row.status??'Status not supplied')}];
  }).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  const sources=data.sources as Record<string,{status?:string}>|undefined;
  return {generatedAt:String(data.generated_at),flights,partial:!sources||Object.values(sources).some(s=>s.status!=='available')};
}
export function nextMovement(board:TrafficBoard|null,runway:ParallelRunway,now:number){
  if(!board||now-Date.parse(board.generatedAt)>15*60000||Date.parse(board.generatedAt)>now+5*60000)return null;
  return board.flights.find(f=>f.runway===runway&&Date.parse(f.at)>=now&&!/cancel|landed|arrived|departed|off.block/i.test(f.status))??null;
}
export function demoTraffic(now:number,direction:'07'|'25'|null):TrafficBoard{
  const heading=direction==='25'?250:70;
  return {generatedAt:new Date(now).toISOString(),partial:false,flights:parallelRunways.flatMap((runway,i)=>[0,1,2].map((n)=>({id:`demo-${i}-${n}`,number:`DEMO ${101+i*10+n}`,operation:(i===1?'departure':'landing') as Movement,airport:['London','Paris','Madrid'][i],at:new Date(now+(5+n*9+i*2)*60000).toISOString(),estimated:false,runway,runwayEnd:runway.split('/')[direction==='25'?1:0],position:n===0?{lat:[50.042,50.036,50.031][i]+Math.cos(heading*Math.PI/180)*.002*((now/1000%60)/60),lon:[8.511,8.553,8.550][i]+Math.sin(heading*Math.PI/180)*.005*((now/1000%60)/60),heading,at:new Date(now).toISOString()}:null,status:'Illustrative flight'})))};
}
