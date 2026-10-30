/** Antonio's departure-board boundary. Published departure times are not wheels-off. */
export type Departure = {
  id:string; number:string; destination:string; at:string; timeBasis:'Estimated'|'Scheduled';
  assignedRunway:string|null; status:string; sourceUrl:string|null;
};
export type DepartureBoard = {generatedAt:string; status:'available'|'partial'|'unavailable'; flights:Departure[]};
export function adaptDepartures(input:unknown):DepartureBoard {
  if(!input||typeof input!=='object')throw new Error('Invalid departure board');
  const data=input as Record<string,unknown>;
  if(data.schema_version!=='1.0'||!Array.isArray(data.departures)||!Number.isFinite(Date.parse(String(data.generated_at))))throw new Error('Unsupported departure board');
  const source=data.source as Record<string,unknown>|undefined;
  const flights:Departure[]=data.departures.flatMap((raw:unknown)=>{
    if(!raw||typeof raw!=='object')return [];
    const row=raw as Record<string,unknown>,at=row.estimated_departure_at||row.scheduled_departure_at;
    if(typeof row.flight_id!=='string'||typeof row.flight_number!=='string'||!Number.isFinite(Date.parse(String(at))))return [];
    return [{id:row.flight_id,number:row.flight_number,destination:String(row.destination||row.destination_iata||'Destination unavailable'),at:String(at),timeBasis:row.estimated_departure_at?'Estimated' as const:'Scheduled' as const,assignedRunway:typeof row.assigned_runway==='string'?row.assigned_runway:null,status:String(row.status||'Status not supplied'),sourceUrl:typeof row.source_url==='string'&&row.source_url.startsWith('https://www.frankfurt-airport.com/')?row.source_url:null}];
  }).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  return {generatedAt:String(data.generated_at),status:source?.status==='available'?'available':source?.status==='partial'?'partial':'unavailable',flights};
}
export const frankfurtTime=(at:string|number)=>new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(at));
