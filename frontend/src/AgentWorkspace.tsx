import {useEffect,useRef,useState} from 'react';
import {ArrowRight,Boxes,ChartNoAxesCombined,ClipboardCheck,ShieldCheck,Sparkles} from 'lucide-react';
import {api} from './api';
import {Badge,Button,SectionTitle} from './components';
import {ProcurementReviewNotice} from './ProcurementReviewNotice';
import {AgentWorkReport} from './AgentWork';
import type {Context,ProcurementReadiness,Run} from './types';

const jobs=[
 {id:'daily_review',name:'Review the business',agent:'Orchestrator + all specialists',icon:Sparkles,description:'Bring sales changes, stock risks and supplier checks into one brief.',output:'A business review you can download',prompt:'Prepare a business review: summarize reviewed sales, compare the latest 7 sales days with the preceding 7 days, prioritize stock risks, and check supplier readiness. Do not create purchase drafts.'},
 {id:'sales_review',name:'Explain sales performance',agent:'Sales Agent',icon:ChartNoAxesCombined,description:'Compare recent periods and identify the products behind revenue changes.',output:'Sales brief + period comparison',prompt:'Summarize reviewed sales and compare two 7-day periods ending at the latest reviewed sale. Show product changes and flag incomplete history. Do not prepare purchases.'},
 {id:'stock_review',name:'Prioritize stock risks',agent:'Inventory Agent',icon:Boxes,description:'Find what may run out before delivery and put the urgent products first.',output:'A ranked stock review list',prompt:'Inspect all reviewed stock, prioritize stockout risks using dated demand evidence, and show current top-up quantities. Do not create purchases.'},
 {id:'supplier_review',name:'Check suppliers before ordering',agent:'Procurement Agent',icon:ClipboardCheck,description:'Match low-stock products to quotes and explain missing checks.',output:'Supplier shortlist + review issues',prompt:'Review all low-stock supplier matches, prices, currency and relationships. Prepare a read-only shortlist; do not create purchase drafts.'},
 {id:'replenishment',name:'Prepare purchase drafts',agent:'Inventory + Procurement',icon:ClipboardCheck,description:'Calculate quantities, match suppliers and prepare a draft for approval.',output:'A pending purchase proposal',prompt:'Inspect stock and prepare purchase-order drafts for all reviewed low-stock products. Do not approve, execute or send any order.'},
];
const roles=[{name:'Orchestrator',icon:Sparkles,role:'Chooses the checks and assembles your brief'},{name:'Sales Agent',icon:ChartNoAxesCombined,role:'Summarizes sales and compares periods'},{name:'Inventory Agent',icon:Boxes,role:'Ranks stock risks and calculates top-ups'},{name:'Procurement Agent',icon:ClipboardCheck,role:'Checks quotes and prepares approved-workflow drafts'}];

export function AgentWorkspace({state,provider,root,busy,perform,navigate}:Context){
 const [message,setMessage]=useState('Analyze sales and inventory. Prepare purchase order drafts for all low-stock products, and explain what needs my approval.');
 const [readiness,setReadiness]=useState<ProcurementReadiness|null>(null),[readinessError,setReadinessError]=useState('');
 const [mode,setMode]=useState<'meta'|'guided'>(provider.configured?'meta':'guided');
 const [runMode,setRunMode]=useState<'meta'|'guided'>('guided');
 const [running,setRunning]=useState(''),[live,setLive]=useState<Run|null>(null),[result,setResult]=useState<Run|null>(null),[jobError,setJobError]=useState('');
 const active=useRef(''),timer=useRef<ReturnType<typeof setInterval>|null>(null);
 useEffect(()=>{setResult(null);setLive(null);setJobError('');setRunning('');active.current='';return()=>{active.current='';if(timer.current)clearInterval(timer.current)}},[root]);
 useEffect(()=>{let valid=true;setReadiness(null);setReadinessError('');
  api<ProcurementReadiness>(root+'/procurement/readiness').then(r=>{if(valid)setReadiness(r)}).catch(e=>{if(valid)setReadinessError((e as Error).message)});
  return()=>{valid=false};
 },[root,state.tables,state.relationships]);

 async function start(task:string,execution:'meta'|'guided',question:string){
  if(active.current)return;
  const tag=crypto.randomUUID().replaceAll('-','');active.current=tag;setRunning(task);setRunMode(execution);setLive(null);setResult(null);setJobError('');
  const polling=setInterval(()=>{void api<Run>(root+'/agents/progress/'+tag).then(r=>{if(active.current===tag)setLive(r)}).catch(()=>{})},1200);timer.current=polling;
  try{await perform(execution==='meta'?'Meta is choosing and running specialist tools…':'Running the reviewed-data checks…',async()=>{
   try{const r=await api<Run>(root+'/agents','POST',{message:question,mode:execution,task,request_id:tag});if(active.current===tag)setResult(r)}
   catch(e){if(active.current===tag)setJobError((e as Error).message);throw e}
  })}finally{clearInterval(polling);if(active.current===tag){active.current='';setRunning('');setLive(null)}}
 }
 function reviewPrerequisites(){
  if(readiness?.blockers.some(b=>b.next_step==='review_relationships'))void perform('Discovering supplier links for your review…',async()=>{await api(root+'/relationships/discover','POST');navigate('/mapping#relationships')});
  else if(readiness?.blockers.some(b=>b.code==='reorder_threshold_missing'))navigate('/analytics#demand-planner');
  else navigate('/mapping');
 }
 const history=state.runs.slice().reverse();
 const reports=result&&!history.some(r=>r.id===result.id)?[result,...history]:history;
 const working=!!busy||!!running;
 return <>
  <SectionTitle eyebrow="YOUR SPREADSHEETS. YOUR AI WORKFORCE." title="Give your agents a job." description="Get a finished brief, a stock priority list, or a purchase draft—with the work and sources shown."/>
  <div className="agent-team-strip">{roles.map(a=>{const count=state.runs.reduce((n,r)=>n+r.steps.filter(s=>s.agent===a.name&&s.status==='completed').length,0);const doing=live?.steps.some(s=>s.agent===a.name&&s.status==='running');return <div key={a.name}><a.icon size={20}/><strong>{a.name}</strong><p>{a.role}</p><small>{a.name==='Orchestrator'?state.runs.filter(r=>r.status==='completed').length+' completed runs':count+' completed checks'}{doing?' · Working now':''}</small></div>})}</div>
  <div className="agent-job-toolbar"><div><h3>Choose the work to hand over</h3><p>Reports are read-only. Only “Prepare purchase drafts” creates an approval item.</p></div><label>How to run<select aria-label="Job execution mode" value={mode} disabled={working} onChange={e=>setMode(e.target.value as 'meta'|'guided')}><option value="meta" disabled={!provider.configured}>Meta chooses and runs tools</option><option value="guided">Data checks · no AI</option></select></label></div>
  <div className="agent-jobs">{jobs.map(j=><article className="panel agent-job" aria-label={j.name} key={j.id}><span className="job-owner"><j.icon size={17}/>{j.agent}</span><h3>{j.name}</h3><p>{j.description}</p><small>You receive: {j.output}</small><Button disabled={working||(mode==='meta'&&!provider.configured)} onClick={()=>void start(j.id,mode,j.prompt)}>{running===j.id?'Working…':'Start job'}<ArrowRight size={14}/></Button></article>)}</div>
  {!!running&&<section className="panel agent-live" aria-label="Live job activity"><h3>Agents at work</h3>{!live?.steps.length?<p role="status">{runMode==='meta'?'The Orchestrator is choosing tools for this job.':'Starting the reviewed-data checks.'}</p>:<ol>{live.steps.map((s,i)=><li key={i}><strong>{s.agent}</strong><span>{s.status==='running'?'Running '+s.tool.replaceAll('_',' ')+'…':s.status==='completed'?'Completed '+s.tool.replaceAll('_',' '):s.status==='needs_review'?'Waiting for review':s.status}</span></li>)}</ol>}<small>Activity appears when the backend starts or completes a real tool call.</small></section>}
  {jobError&&<p className="alert error" role="alert">{running==='custom'?'Guided check failed: ':'Job failed: '}{jobError}</p>}
  {result&&<section className="agent-job-feedback" aria-label="Latest guided check"><p role="status">{result.status==='needs_review'?'Check completed — review required.':'Check completed.'} {result.origin==='meta'?'Meta planned the tool calls.':'No AI was used.'}</p><p>{result.task&&result.task!=='custom'?'Your work report is ready below. Review the findings or download it to share.':result.summary}</p><Button variant="secondary" onClick={()=>{const el=document.getElementById('run-'+result.id);el?.scrollIntoView({block:'start',behavior:'smooth'});el?.focus({preventScroll:true})}}>View this check’s details<ArrowRight size={14}/></Button>{!!result.action_ids.length&&<Button variant="ghost" onClick={()=>navigate('/approvals')}>Open Approval Center<ArrowRight size={14}/></Button>}</section>}
  {readiness&&<ProcurementReviewNotice readiness={readiness} busy={working} onReview={reviewPrerequisites}/>}
  {readinessError&&<p className="alert warning">Readiness check unavailable: {readinessError}</p>}
  <details className="panel agent-custom"><summary>Ask a custom question or run the full guided check</summary><div className="agent-prompt"><form onSubmit={e=>{e.preventDefault();void start('custom','meta',message)}}><textarea aria-label="Ask your AI workforce" value={message} maxLength={2000} onChange={e=>setMessage(e.target.value)}/><div className="prompt-footer"><span><ShieldCheck size={14}/>Agents prepare proposals. Only you approve them.</span><Button type="submit" disabled={working||!provider.configured||!message.trim()}>Ask Meta</Button></div></form><div className="guided-path"><span>Full sales, stock and purchase-preparation check. No model is used.</span><Button variant="ghost" disabled={working} onClick={()=>void start('custom','guided','Guided replenishment check')}>{running==='custom'?'Checking…':'Run guided check'}<ArrowRight size={14}/></Button></div></div></details>
  <div className="agent-work-heading"><h2>Work delivered</h2><p>Open results, inspect source cells, or download the brief for a colleague.</p></div>
  {!reports.length&&<div className="panel agent-no-work">Choose a job above. Its findings and work report will appear here.</div>}
  {reports.map(run=><AgentWorkReport key={run.id} run={run} state={state} root={root} busy={busy} perform={perform} navigate={navigate} onReview={reviewPrerequisites}/>)}
 </>;
}
