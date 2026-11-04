import {ArrowDownToLine,ArrowRight,CheckCheck,Clock3} from 'lucide-react';
import {download,formatMoney,label} from './api';
import {Badge,Button} from './components';
import type {AgentStep,Context,Run} from './types';

interface Source {workbook_id:string;table_id?:string;sheet:string;row:number;cells:Record<string,string>}
interface Item {product_id:string;product_name?:string;name?:string;units?:string;quantity?:string;revenue?:string;currency?:string;line_total?:string;supplier_id?:string;supplier_name?:string;change?:string;percent?:string|null;reason?:string;suggested_quantity?:string;source?:Source}
interface ToolResult {action_id?:string;total?:number;rows_compared?:number;total_products?:number;low_stock_count?:number;ready_count?:number;supplier_count?:number;draft_created?:boolean;status?:string;message?:string;approval_required?:boolean;revenue?:{currency:string;amount:string}[];totals?:{currency:string;amount:string}[];top_products?:Item[];product_changes?:Item[];priorities?:Item[];stock?:Item[];lines?:Item[];rows?:{source:Source}[];source_examples?:{source:Source}[];source_examples_raw?:Source[];blockers?:{message:string}[];warnings?:string[];periods?:{name:string;from:string;to:string;rows:number;units:string;revenue:{currency:string;amount:string}[]}[];revenue_changes?:{currency:string;previous:string;current:string;change:string|null;percent:string|null}[]}
const seconds=(ms:number)=>ms<1000?'<1 sec':(ms/1000).toFixed(1)+' sec';
const toolNames:Record<string,string>={sales_analysis:'Sales brief',sales_comparison:'Sales comparison',inventory_analysis:'Stock priorities',procurement_review:'Supplier shortlist',draft_purchase_orders:'Purchase draft'};

function WorkResult({step,state,navigate}:Pick<Context,'state'|'navigate'>&{step:AgentStep}){
 const r=(step.result||{}) as ToolResult;
 const actionStatus=state.actions.find(a=>a.id===r.action_id)?.status||r.status;
 const evidence=[...(r.rows||r.source_examples||[]).map(p=>p.source),...(r.source_examples_raw||[]),...(r.stock||[]).flatMap(p=>p.source?[p.source]:[])].slice(0,5);
 return <div className="agent-work-result">
  {step.tool==='sales_analysis'&&<><div className="work-facts"><strong>{r.total||0} sales rows summarized</strong>{r.revenue?.map(t=><span key={t.currency}>{formatMoney(t.amount,t.currency)} revenue</span>)}</div>{!!r.top_products?.length&&<div className="work-list">{r.top_products.slice(0,3).map((p,i)=><div key={p.product_id+'-'+p.currency}><span>{i+1}. {p.name||p.product_id}</span><strong>{p.units} units{p.currency&&p.revenue?' · '+formatMoney(p.revenue,p.currency):''}</strong></div>)}</div>}</>}
  {step.tool==='sales_comparison'&&<>
   {r.status!=='completed'&&<p className="work-caution">There isn’t enough earlier history for a reliable increase/decrease comparison.</p>}
   <div className="work-periods">{r.periods?.map(p=><div key={p.name}><span>{p.name==='current'?'Latest period':'Previous period'}</span><strong>{p.from} → {p.to}</strong><small>{p.rows} sales rows · {p.units} units</small>{p.revenue.map(t=><p key={t.currency}>{formatMoney(t.amount,t.currency)}</p>)}</div>)}</div>
   {!!r.revenue_changes?.length&&<div className="work-list">{r.revenue_changes.map(c=><div key={c.currency}><span>{c.currency} revenue change</span><strong>{c.change===null?'History incomplete':formatMoney(c.change,c.currency)}{c.percent!==null?' ('+c.percent+'%)':''}</strong></div>)}</div>}
   {!!r.product_changes?.length&&<details className="work-evidence"><summary>Products behind the change</summary>{r.product_changes.slice(0,5).map(p=><p key={p.product_id+'-'+p.currency}>{p.name||p.product_id}: {p.change&&p.currency?formatMoney(p.change,p.currency):'—'}</p>)}</details>}
  </>}
  {step.tool==='inventory_analysis'&&<><div className="work-facts"><strong>{r.total_products||0} stock products checked</strong><span>{r.low_stock_count||0} below their reorder point</span></div>{!!r.priorities?.length?<div className="work-priorities">{r.priorities.slice(0,5).map(p=><div key={p.product_id}><strong>{p.product_name||p.product_id}</strong><p>{p.reason}</p><small>Top-up from reviewed rules: {p.suggested_quantity} units</small></div>)}</div>:<p>{r.priorities?'No stock priorities were identified from the reviewed data.':'Priority rankings were not recorded for this older check.'}</p>}</>}
  {(step.tool==='procurement_review'||step.tool==='draft_purchase_orders')&&<>
   {step.tool==='procurement_review'&&<div className="work-facts"><strong>{r.ready_count||0} products matched to usable quotes</strong><span>{r.supplier_count||0} suppliers · No purchase draft created</span></div>}
   {step.tool==='draft_purchase_orders'&&<p className="work-caution">{actionStatus==='executed'?'This output already exists. No duplicate was generated.':actionStatus==='pending'?'A purchase draft is waiting for your approval.':r.message||'Check the proposal status before taking action.'}</p>}
   {!!r.lines?.length&&<div className="table-wrap"><table><thead><tr><th>Product / supplier</th><th>Quantity</th><th>Cost</th></tr></thead><tbody>{r.lines.slice(0,10).map(p=><tr key={p.product_id}><td>{p.product_name||p.product_id}<small>{p.supplier_name||p.supplier_id}</small></td><td>{p.quantity}</td><td>{p.line_total&&p.currency?formatMoney(p.line_total,p.currency):'—'}</td></tr>)}</tbody></table></div>}
   {r.blockers?.map((b,i)=><p className="work-caution" key={i}>{b.message}</p>)}
  </>}
  {!!r.warnings?.length&&<details className="work-evidence"><summary>Data notes ({r.warnings.length})</summary>{r.warnings.map((w,i)=><p key={i}>{w}</p>)}</details>}
  {!!evidence.length&&<details className="work-evidence"><summary>Example source cells</summary>{evidence.map((s,i)=><div className="work-source" key={i}><span>{state.workbooks?.find(w=>w.id===s.workbook_id)?.name||'Workbook'} · {s.sheet} · row {s.row}<small>{Object.entries(s.cells||{}).map(([field,cell])=>field+': '+cell).join(' · ')}</small></span>{s.table_id&&<Button variant="ghost" onClick={()=>navigate('/mapping#table-'+s.table_id)}>Review source<ArrowRight size={12}/></Button>}</div>)}</details>}
 </div>;
}

export function AgentWorkReport({run,state,root,busy,perform,navigate,onReview}:Pick<Context,'state'|'root'|'busy'|'perform'|'navigate'>&{run:Run;onReview:()=>void}){
 return <article className="panel run-card agent-work-report" id={'run-'+run.id} tabIndex={-1}>
  <div className="run-heading"><div><strong>{run.title||'Orchestrator run'}</strong><small>{new Date(run.created).toLocaleString()}</small></div><Badge tone={run.status==='completed'?'green':run.status==='needs_review'?'amber':'red'}>{label(run.status)}</Badge><Badge tone="outline">{run.origin==='meta'?'Meta Model API':'Guided tools · no AI'}</Badge></div>
  {run.work&&<div className="work-completed" aria-label="Work completed for you"><strong>Work completed for you</strong><div><span>{run.work.completed_checks} specialist checks</span>{run.work.sales_rows_in_largest_check>0&&<span>{run.work.sales_rows_in_largest_check} sales rows in the largest check</span>}{run.work.stock_products_checked>0&&<span>{run.work.stock_products_checked} stock products checked</span>}{run.elapsed_ms!==undefined&&<span><Clock3 size={13}/>{seconds(run.elapsed_ms)} elapsed</span>}</div><small>Counts and runtime come from this run. No manual-time saving is estimated.</small></div>}
  <p className="user-question">{run.message}</p>
  {!run.steps.length&&<p className="agent-summary">{run.summary}</p>}
  <div className="agent-deliverables">{run.steps.map((step,i)=><section className="agent-deliverable" key={i} aria-label={step.agent+' work product'}>
   <div className="deliverable-heading"><span className="step-number">{i+1}</span><div><strong>{step.agent}</strong><span>{toolNames[step.tool]||label(step.tool)}</span></div>{step.status==='needs_review'?<Badge tone="amber">Needs review</Badge>:step.status==='completed'?<CheckCheck size={18}/>:<Badge tone="outline">{label(step.status)}</Badge>}{step.elapsed_ms!==undefined&&<small>{seconds(step.elapsed_ms)}</small>}</div>
   {step.summary&&<p className="deliverable-summary">{step.summary}</p>}
   {step.status!=='running'&&<WorkResult step={step} state={state} navigate={navigate}/>}
   <details className="work-evidence"><summary>Technical tool result</summary><pre>{JSON.stringify(step.result,null,2)}</pre></details>
  </section>)}</div>
  <details className="work-evidence"><summary>Full decision summary</summary><p className="agent-summary">{run.summary}</p></details>
  <div className="work-report-actions"><Button variant="secondary" disabled={!!busy||run.status==='running'} onClick={()=>void perform('Downloading the agent work report…',()=>download(root+'/agent-runs/'+run.id+'/report','Agent-Work-'+run.id.slice(0,8)+'.txt'))}><ArrowDownToLine size={15}/>Download work report</Button>
   {(run.status==='needs_review'||(run.status==='failed'&&run.summary.startsWith('Cannot safely draft:')))&&<Button variant="secondary" disabled={!!busy} onClick={onReview}>Review procurement prerequisites<ArrowRight size={15}/></Button>}
   {!!run.action_ids.length&&<Button onClick={()=>navigate('/approvals')}>{run.action_ids.some(id=>state.actions.some(a=>a.id===id&&a.status==='executed'))?'View existing purchase-order output':'Review proposed actions'}<ArrowRight size={15}/></Button>}
  </div>
 </article>;
}
