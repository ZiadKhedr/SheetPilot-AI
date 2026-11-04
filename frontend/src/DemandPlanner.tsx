import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Clock3, PackageCheck, Settings2, TriangleAlert } from 'lucide-react';
import { api } from './api';
import { Badge, Button } from './components';
import type { Context } from './types';

interface Parameters {window_days:number;lead_time_days:number;safety_days:number;review_period_days:number;as_of:string|null}
interface ProductPlan {
 product_id:string;product_name:string;stock_quantity:string;source_reorder_point?:string|null;observed_days:number;
 sales_units:string|null;daily_sales:string|null;days_remaining:string|null;estimated_stockout_date:string|null;
 reorder_point:string|null;target_stock:string|null;suggested_quantity:string|null;eligible:boolean;needs_reorder:boolean;
 status:string;warnings:string[];window_start:string|null;window_end:string|null;sales_records:number;active_days:number;
}
interface Report {parameters:Parameters;policy:{enabled:boolean;revision:number;reviewed_at:string|null};preview:boolean;as_of:string|null;products:ProductPlan[];warnings:string[]}
type Props = Pick<Context,'root'|'state'|'busy'|'perform'|'navigate'> & {stats?:Pick<Context['stats'],'stock'>};
const format=(value:string|null)=>value===null?'—':new Intl.NumberFormat('en-US',Number(value)!==0&&Math.abs(Number(value))<0.01?{maximumSignificantDigits:3}:{maximumFractionDigits:2}).format(Number(value));
const dateLabel=(value:string|null)=>value?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric'}).format(new Date(value+'T12:00:00')):'Choose a stock date';
const ranges=[['window_days',7,365],['lead_time_days',1,365],['safety_days',0,365],['review_period_days',1,365]] as const;

export function DemandPlanner({root,state,stats,busy,perform,navigate}:Props){
 const [report,setReport]=useState<Report|null>(null),[params,setParams]=useState<Parameters|null>(null);
 const [ack,setAck]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[feedback,setFeedback]=useState('');
 const [settingsOpen,setSettingsOpen]=useState(false),[orderingOpen,setOrderingOpen]=useState(false);
 const settingsRef=useRef<HTMLDivElement>(null),scope=useRef(root);scope.current=root;
 useEffect(()=>{
  let active=true;setLoading(true);setError('');setReport(null);setParams(null);setAck(false);setFeedback('');setSettingsOpen(false);setOrderingOpen(false);
  api<Report>(root+'/demand').then(r=>{if(active){setReport(r);setParams(r.parameters)}})
   .catch(e=>{if(active)setError((e as Error).message)}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[root,state.tables,state.relationships]);

 async function calculate(reset=false){
  if(!params)return;
  const requestScope=root;setLoading(true);setError('');setFeedback('');
  try{
   const r=reset?await api<Report>(root+'/demand'):await api<Report>(root+'/demand/preview','POST',params);
   if(scope.current!==requestScope)return;
   const unchanged=JSON.stringify(r.products)===JSON.stringify(report?.products);
   setReport(r);if(reset){setParams(r.parameters);setAck(false)}
   setFeedback(reset?'Saved settings restored.':unchanged?'Estimate updated. Results are unchanged because the inputs and data are the same.':'Estimate updated. The product results below use your test settings. Nothing was ordered or saved.');
  }catch(e){if(scope.current===requestScope)setError((e as Error).message)}
  finally{if(scope.current===requestScope)setLoading(false)}
 }
 function edit(next:Parameters){setParams(next);setAck(false);setFeedback('')}
 async function save(enabled:boolean){
  if(!params||!report)return;const requestScope=root;
  await perform(enabled?'Saving your ordering settings…':'Turning off sales-based ordering…',async()=>{
   await api(root+'/demand/policy','PUT',{...params,expected_revision:report.policy.revision,enabled,stock_snapshot_confirmed:ack});
   const r=await api<Report>(root+'/demand');
   if(scope.current===requestScope){setReport(r);setParams(r.parameters);setAck(false)}
  },enabled?'Ordering settings saved. You still review and approve each purchase order.':'Sales-based ordering turned off. Your Excel rules still apply.');
 }
 function changeSettings(){setSettingsOpen(v=>!v)}
 const working=!!busy||loading;
 const fresh=!!report&&!!params&&Object.keys(report.parameters).every(k=>report.parameters[k as keyof Parameters]===params[k as keyof Parameters]);
 const valid=!!params&&ranges.every(([key,min,max])=>Number.isInteger(params[key])&&params[key]>=min&&params[key]<=max);
 const usable=report?.products.filter(p=>p.eligible&&p.days_remaining!==null)||[];
 const attention=usable.filter(p=>p.needs_reorder||Number(p.days_remaining)<(report?.parameters.lead_time_days||0));
 const late=usable.filter(p=>Number(p.days_remaining)<(report?.parameters.lead_time_days||0));
 const missing=(report?.products.length||0)-usable.length;
 const sourceRules=report?.products.filter(p=>p.source_reorder_point!=null).length||0;
 const allSourceRules=!!report?.products.length&&sourceRules===report.products.length;
 const canUse=report?.products.filter(p=>p.eligible&&p.source_reorder_point==null).length||0;
 const products=report?.products.slice().sort((a,b)=>{
  const aRank=a.eligible?(a.needs_reorder||Number(a.days_remaining)<report.parameters.lead_time_days?0:2):1;
  const bRank=b.eligible?(b.needs_reorder||Number(b.days_remaining)<report.parameters.lead_time_days?0:2):1;
  return aRank-bRank||(Number(a.days_remaining??Infinity)-Number(b.days_remaining??Infinity));
 })||[];

 return <section className="panel demand-planner stock-outlook" id="demand-planner" aria-label="Sales-based stock planning">
  <div className="outlook-heading"><div><div className="eyebrow">PLAN YOUR NEXT RESTOCK</div><h2>Will your stock last until delivery?</h2><p>See what needs attention before you order more.</p></div><Button variant="secondary" onClick={changeSettings} aria-expanded={settingsOpen} aria-controls="stock-estimate-settings"><Settings2 size={16}/>{settingsOpen?'Hide settings':'Change settings'}</Button></div>
  {error&&<p role="alert" className="outlook-error">We couldn’t update the estimate. {error}</p>}
  {loading&&!report&&<p role="status">Checking your sales and stock…</p>}
  {report&&params&&<>
   <p className="outlook-context">Stock estimate starts <strong>{dateLabel(report.as_of)}</strong><span>·</span>Supplier delivery takes <strong>{report.parameters.lead_time_days} days</strong>{report.preview&&<Badge tone="amber">Test settings · not saved</Badge>}</p>
   <div className={'outlook-summary '+(attention.length?'needs-attention':'')}>
    <span className="outlook-summary-icon">{attention.length?<TriangleAlert size={24}/>:<PackageCheck size={24}/>}</span>
    <div><h3>{attention.length?`${attention.length} ${attention.length===1?'product needs':'products need'} attention`:usable.length?'Stock looks sufficient for the products we could check':'We need more sales data to estimate stock'}</h3>
     <p>{late.length?`${late.length} ${late.length===1?'product may':'products may'} run out before a ${report.parameters.lead_time_days}-day delivery arrives. Check whether your supplier can deliver sooner.`:attention.length?'Recent sales suggest topping up these products soon.':'Estimates assume products keep selling at their recent rate. Incoming deliveries are not included.'}</p>
     {!!missing&&<p>{missing} {missing===1?'product needs':'products need'} a data review before we can estimate how long the stock will last.</p>}
    </div>
    {!!attention.length&&<Button onClick={()=>navigate('/agents')}>Review restocking<ArrowRight size={15}/></Button>}
   </div>
   {sourceRules>0&&<p className="outlook-source" role="note" aria-label="Where order amounts come from"><strong>{allSourceRules?'Your Excel sets the order amounts.':`Your Excel sets order amounts for ${sourceRules} products.`}</strong> Changing these test settings won’t replace your Excel targets. {allSourceRules?'You don’t need to save an extra ordering rule.':'Only products without an Excel reorder point can use a sales-based rule.'}</p>}

   <div ref={settingsRef} id="stock-estimate-settings" className="outlook-settings" hidden={!settingsOpen}>
    <h3>Try a different delivery time or stock date</h3><p>Change the values, then click Update estimate. This only tests an idea.</p>
    <div className="outlook-controls">
     <label>When was this stock counted?<input aria-label="Stock count date" type="date" disabled={working} value={params.as_of||''} onChange={e=>edit({...params,as_of:e.target.value||null})}/><small>The stock amounts and estimates should start on this date.</small></label>
     <label>How many days does delivery take?<input aria-label="Supplier delivery days" type="number" min={1} max={365} disabled={working} value={params.lead_time_days} onChange={e=>edit({...params,lead_time_days:Number(e.target.value)})}/><small>Time from placing an order to receiving it.</small></label>
    </div>
    <details className="outlook-more"><summary>More settings</summary><div className="outlook-controls">
     <label>Use sales from the last<input aria-label="Sales history days" type="number" min={7} max={365} disabled={working} value={params.window_days} onChange={e=>edit({...params,window_days:Number(e.target.value)})}/><small>Days of past sales to average. Usually 30.</small></label>
     <label>Extra days for delivery delays<input aria-label="Delay buffer days" type="number" min={0} max={365} disabled={working} value={params.safety_days} onChange={e=>edit({...params,safety_days:Number(e.target.value)})}/><small>Add a cushion if deliveries are sometimes late.</small></label>
     <label>Days of stock to add after delivery<input aria-label="Extra stock days" type="number" min={1} max={365} disabled={working} value={params.review_period_days} onChange={e=>edit({...params,review_period_days:Number(e.target.value)})}/><small>Extra selling days to include in the test top-up amount.</small></label>
    </div></details>
    {!valid&&<p className="outlook-error">Use whole days: delivery and extra stock 1–365, sales history 7–365, and delay buffer 0–365.</p>}
    {!fresh&&<p className="outlook-pending">Your changes aren’t shown in the results yet. Click Update estimate.</p>}
    <div className="outlook-buttons"><Button disabled={working||!valid} onClick={()=>void calculate()}>{loading?'Updating…':'Update estimate'}</Button><Button variant="ghost" disabled={working} onClick={()=>void calculate(true)}>Reset to saved settings</Button><span>No purchase order will be created.</span></div>
   </div>
   {feedback&&<p className="outlook-feedback" role="status" aria-live="polite">{feedback}</p>}

   <div className="outlook-products">{products.map(p=>{
    const arrivesLate=p.eligible&&p.days_remaining!==null&&Number(p.days_remaining)<report.parameters.lead_time_days;
    const stock=stats?.stock.find(s=>s.product_id===p.product_id);
    const fromExcel=p.source_reorder_point!=null;
    return <article className={'outlook-product '+(arrivesLate||p.needs_reorder?'at-risk':'')} aria-label={p.product_name+' stock estimate'} key={p.product_id}>
     <div className="outlook-product-top"><div><h3 dir="auto">{p.product_name}</h3><span>{p.product_id}</span></div><Badge tone={!p.eligible||arrivesLate||p.needs_reorder?'amber':'green'}>{!p.eligible?'Check sales data':arrivesLate?'May run out before delivery':p.needs_reorder?'Top up soon':'Enough stock for now'}</Badge></div>
     <div className="outlook-product-facts"><div><span>In stock</span><strong>{format(p.stock_quantity)} <small>units</small></strong></div><div><span>Usually sells</span><strong>{format(p.daily_sales)} <small>/ day</small></strong></div><div><span>Stock lasts about</span><strong>{format(p.days_remaining)} <small>days</small></strong></div></div>
     <p className="outlook-product-date"><Clock3 size={15}/>{p.estimated_stockout_date?`Could run out around ${dateLabel(p.estimated_stockout_date)}`:'A run-out date can’t be estimated yet.'}</p>
     {stock?.commercial&&<p className="outlook-source">{stock.commercial.calculation}</p>}{stock?.replenishment_configured&&stock.low_stock?<p className="outlook-topup"><strong>Top-up to review: {format(stock.suggested_quantity)} units</strong><span>{stock.threshold_source==='source'?`From your Excel target of ${format(stock.target_stock)} units.`:'From your saved ordering settings.'} You still approve any purchase.</span></p>:fromExcel?<p className="outlook-topup"><span>{stock?'Your Excel rules don’t currently suggest a top-up.':'Purchase quantities follow your Excel rules.'}</span></p>:<p className="outlook-topup"><span>{p.eligible?'A test top-up is shown under “Why these numbers?” below.':'Review this product’s sales dates and links before using an estimate.'}</span></p>}
     <details className="outlook-calculation"><summary>Why these numbers?</summary><div>
      {p.sales_units!==null&&<><p>{format(p.sales_units)} units sold over {p.observed_days} calendar days = about {format(p.daily_sales)} sold per day.</p><p>{format(p.stock_quantity)} in stock ÷ {format(p.daily_sales)} sold per day = about {format(p.days_remaining)} days of stock, starting {dateLabel(report.as_of)}.</p></>}
      {p.suggested_quantity!==null&&<p><strong>Test top-up: {format(p.suggested_quantity)} units.</strong> These settings suggest topping up when stock falls below {format(p.reorder_point)}, aiming for {format(p.target_stock)} units. {fromExcel?'Your Excel targets still control actual purchase suggestions.':'This is an estimate until you choose to save an ordering rule.'}</p>}
      <p>Sales checked: {dateLabel(p.window_start)} to {dateLabel(p.window_end)}. Days without sales are included.</p>
      {p.warnings.map((w,i)=><p key={i}>{w}</p>)}
      {!p.eligible&&<><p>This estimate can’t be used to set an ordering rule yet.</p><Button variant="ghost" onClick={()=>navigate('/mapping#relationships')}>Review sales data and links<ArrowRight size={14}/></Button></>}
     </div></details>
    </article>;
   })}</div>
   {!products.length&&<div className="outlook-empty"><p>Start by reviewing an inventory table and linking it to dated sales.</p><Button variant="secondary" onClick={()=>navigate('/mapping')}>Review your files<ArrowRight size={15}/></Button></div>}

   {(!allSourceRules||report.policy.enabled)&&<div className="outlook-ordering">
    <button className="outlook-ordering-toggle" onClick={()=>setOrderingOpen(v=>!v)} aria-expanded={orderingOpen} aria-controls="outlook-ordering-review"><span>Optional: use sales to suggest future orders</span><Badge tone={report.policy.enabled?'green':'outline'}>{report.policy.enabled?'Saved rule is on':'Not in use'}</Badge></button>
    <div id="outlook-ordering-review" hidden={!orderingOpen}>
     <p>This fills in missing reorder rules only. Existing Excel rules always stay in control.</p>
     {canUse>0?<><p>{canUse} {canUse===1?'product can':'products can'} use this rule. Saving won’t create or approve a purchase order.</p><label className="outlook-ack"><input type="checkbox" checked={ack} disabled={working} onChange={e=>setAck(e.target.checked)}/>The stock date is correct, and sales and stock use the same unit.</label><Button disabled={working||!ack||!params.as_of||!fresh||!valid||!!error} onClick={()=>void save(true)}>Save ordering settings</Button></>:<p>{allSourceRules?'No extra rule is needed for your current products.':'No products have enough reviewed sales history to use an ordering rule yet.'}</p>}
     {report.policy.enabled&&<Button variant="ghost" disabled={working} onClick={()=>void save(false)}>Turn off sales-based ordering</Button>}
    </div>
   </div>}
   <details className="outlook-limitations"><summary>What this estimate includes</summary><p>Past sales are an estimate of future demand. These are uploaded snapshots, not live stock levels. Incoming orders, returns, promotions and seasonal changes aren’t included.</p><ul>{report.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></details>
  </>}
 </section>;
}
