import { useEffect, useRef, useState } from 'react';
import { ArrowRight, TrendingDown } from 'lucide-react';
import { api, label } from './api';
import { Badge, Button, SectionTitle } from './components';
import type { Context } from './types';

interface Parameters{window_days:number;lead_time_days:number;safety_days:number;review_period_days:number;as_of:string|null}
interface ProductPlan{product_id:string;product_name:string;stock_quantity:string;observed_days:number;sales_units:string|null;daily_sales:string|null;days_remaining:string|null;estimated_stockout_date:string|null;reorder_point:string|null;target_stock:string|null;suggested_quantity:string|null;eligible:boolean;needs_reorder:boolean;status:string;warnings:string[];window_start:string|null;window_end:string|null;sales_records:number;active_days:number}
interface Report{parameters:Parameters;policy:{enabled:boolean;revision:number;reviewed_at:string|null};preview:boolean;as_of:string|null;basis:string;formula:string;products:ProductPlan[];warnings:string[]}
const format=(value:string|null)=>value===null?'—':new Intl.NumberFormat('en-US',{maximumFractionDigits:3,minimumSignificantDigits:1,maximumSignificantDigits:6}).format(Number(value));

export function DemandPlanner({root,state,busy,perform,navigate}:Pick<Context,'root'|'state'|'busy'|'perform'|'navigate'>){
 const [report,setReport]=useState<Report|null>(null),[params,setParams]=useState<Parameters|null>(null);
 const [ack,setAck]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [previewMessage,setPreviewMessage]=useState('');
 const resultsRef=useRef<HTMLDivElement>(null),policyRef=useRef<HTMLDivElement>(null);
 const scope=useRef(root);scope.current=root;
 useEffect(()=>{let active=true;setLoading(true);setError('');setReport(null);setParams(null);setAck(false);setPreviewMessage('');
  api<Report>(root+'/demand').then(r=>{if(active){setReport(r);setParams(r.parameters);setAck(false)}}).catch(e=>{if(active)setError((e as Error).message)}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[root,state.tables,state.relationships]);
 async function preview(){
  if(!params)return;const requestScope=root;setLoading(true);setError('');setPreviewMessage('');
  try{
   const r=await api<Report>(root+'/demand/preview','POST',params);
   if(scope.current===requestScope){
    const unchanged=JSON.stringify(r.products)===JSON.stringify(report?.products);
    const eligible=r.products.filter(p=>p.eligible).length;
    setReport(r);
    setPreviewMessage(!r.products.length?'Preview complete. No confirmed inventory products are available.':
     `Preview complete: ${eligible} of ${r.products.length} products have enough reviewed history for replenishment.`+
     (unchanged?' Results are unchanged; recalculating the same inputs does not change the numbers.':''));
   }
  }catch(e){if(scope.current===requestScope)setError((e as Error).message)}
  finally{if(scope.current===requestScope)setLoading(false)}
 }
 function edit(next:Parameters){setParams(next);setAck(false);setPreviewMessage('')}
 async function review(enabled:boolean){if(!params||!report)return;await perform(enabled?'Saving the reviewed demand policy…':'Disabling the demand policy…',async()=>{
  await api(root+'/demand/policy','PUT',{...params,expected_revision:report.policy.revision,enabled,stock_snapshot_confirmed:ack});
  const fresh=await api<Report>(root+'/demand');if(scope.current===root){setReport(fresh);setParams(fresh.parameters)}
 },enabled?'Demand policy confirmed. Only eligible products without source thresholds use its calculations. Purchase drafts still require supplier review and approval.':'Demand policy disabled. Source thresholds are unchanged.')}
 const fresh=!!report&&!!params&&Object.keys(report.parameters).every(key=>report.parameters[key as keyof Parameters]===params[key as keyof Parameters]);
 const working=!!busy||loading;
 const eligible=report?.products.filter(p=>p.eligible).length||0;
 const needsLinks=report?.products.some(p=>p.status==='relationship_review'||p.status==='insufficient_history');
 return <section className="panel demand-planner" id="demand-planner" aria-label="Sales-based stock planning">
  <SectionTitle title="How long will your stock last?" description="Per-product sales velocity, days of cover, and calculated replenishment scenarios." action={<TrendingDown size={22}/>}/>
  {error&&<p role="alert" className="mapping-warning">{error}</p>}
  {loading&&!report&&<p role="status">Analyzing reviewed sales history…</p>}
  {params&&report&&<>
   <div className="demand-basis"><Badge tone={report.policy.enabled&&!report.preview&&fresh?'green':'amber'}>{report.preview||!fresh?'Unsaved scenario · active policy unchanged':report.policy.enabled?'Reviewed policy enabled':'Scenario only · not an active policy'}</Badge><p>Scenario date: <strong>{report.as_of||'No dated sales available'}</strong>. Daily rate uses calendar days, including zero-sale days. This is a historical scenario when the date is in the past.</p><small>Defaults are editable planning assumptions, not values discovered in your Excel. Stock and sales must represent the same units and date.</small></div>
   <div className="demand-controls">{([
    ['window_days','Sales lookback (days)',7,365],['lead_time_days','Delivery lead time (days)',1,365],
    ['safety_days','Safety buffer (days)',0,365],['review_period_days','Extra coverage after delivery (days)',1,365],
   ] as const).map(([key,title,min,max])=><label key={key}>{title}<input type="number" min={min} max={max} value={params[key]} onChange={e=>edit({...params,[key]:Number(e.target.value)})}/></label>)}
    <label>Stock snapshot / scenario date<input type="date" value={params.as_of||''} onChange={e=>edit({...params,as_of:e.target.value||null})}/></label>
   </div>
   <Button variant="secondary" disabled={working} onClick={()=>void preview()}>{loading?'Calculating…':'Preview calculations'}</Button>
   <div className="source-checks" aria-label="Planning next step">
    <p>Preview recalculates the product table below. It does not activate the policy or create a purchase order.</p>
    {previewMessage&&<p role="status" aria-live="polite">{previewMessage}</p>}
    {eligible>0?<p>Next: review the results, then confirm the planning policy after checking its date and units.</p>:<p>No products can use this policy yet. {needsLinks?'Review sales dates and product relationships first.':'Check the product evidence for insufficient history, missing dates, or incompatible units.'}</p>}
    <Button variant="ghost" onClick={()=>resultsRef.current?.scrollIntoView({behavior:'smooth',block:'start'})}>View product results<ArrowRight size={14}/></Button>
    {eligible>0?<Button variant="ghost" onClick={()=>policyRef.current?.scrollIntoView({behavior:'smooth',block:'center'})}>Review policy confirmation<ArrowRight size={14}/></Button>:
     <Button variant="ghost" onClick={()=>navigate('/mapping#relationships')}>Review sales data and links<ArrowRight size={14}/></Button>}
   </div>
   {!fresh&&<p className="mapping-warning">Assumptions changed. Preview again before confirming this policy.</p>}
   <p className="demand-formula">Daily sales = units sold ÷ observed days · Days left = stock ÷ daily sales · Reorder point = daily sales × (lead time + buffer) · Target adds the extra coverage period. Order quantities round up to whole base units.</p>
   <div ref={resultsRef} className="table-wrap demand-results"><table><thead><tr><th>Product</th><th>On hand</th><th>Sales / day</th><th>Days left</th><th>Estimated depletion</th><th>Scenario order</th><th>Evidence / status</th></tr></thead><tbody>{report.products.map(p=><tr key={p.product_id}>
    <td><strong dir="auto">{p.product_name}</strong><small>{p.product_id}</small></td><td>{format(p.stock_quantity)}</td><td>{format(p.daily_sales)}</td><td>{format(p.days_remaining)}</td><td>{p.estimated_stockout_date||'Not estimated'}</td><td>{p.suggested_quantity===null?'—':format(p.suggested_quantity)}<small>Reorder at {format(p.reorder_point)} · target {format(p.target_stock)}</small></td>
    <td><Badge tone={!p.eligible||p.needs_reorder?'amber':'green'}>{label(p.status)}</Badge><details><summary>{p.sales_units===null?'Review needed':`${format(p.sales_units)} units / ${p.observed_days} calendar days`}</summary><p>{p.window_start} – {p.window_end}; {p.sales_records} sales rows on {p.active_days} positive sales days.</p>{p.warnings.map((w,i)=><p key={i}>{w}</p>)}{!p.eligible&&<p>Provisional or unavailable; cannot set a replenishment threshold.</p>}</details></td>
   </tr>)}</tbody></table></div>
   {!report.products.length&&<p>Confirm inventory mappings to see a plan for each product.</p>}
   <details className="evidence"><summary>Assumptions and limitations</summary><ul>{report.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></details>
   {report.products.some(p=>p.status==='relationship_review'||p.status==='insufficient_history')&&<Button variant="ghost" onClick={()=>navigate('/mapping#relationships')}>Review sales dates and relationships<ArrowRight size={14}/></Button>}
   <div ref={policyRef} className="demand-policy-review"><label><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>I confirm the scenario date matches this stock snapshot and sales/stock quantities use comparable units.</label><p>Enabling this policy fills missing thresholds for products with sufficient dated sales only. It preserves source thresholds and original files. Supplier quotes, currency checks, and purchase-order approval remain required.</p>
    {eligible===0&&<p className="mapping-warning">Policy confirmation is unavailable until at least one product has sufficient reviewed sales history.</p>}
    <Button disabled={working||!ack||!params.as_of||!fresh||eligible===0||!!error} onClick={()=>void review(true)}>Confirm sales-based planning policy</Button>
    {report.policy.enabled&&<Button variant="ghost" disabled={working} onClick={()=>void review(false)}>Disable sales-based policy</Button>}
   </div>
  </>}
 </section>
}
