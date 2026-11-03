import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Activity, ArrowUpRight, Bot, ChartNoAxesCombined, ChevronDown, CircleCheck, CircleX, ClipboardCheck, Database, FolderOpen, GitBranch, Layers3, LayoutDashboard, Menu, Plus, ShieldCheck, X } from 'lucide-react';
import { api } from './api';
import { Badge, Busy, Button, Empty, Modal } from './components';
import { Analytics, Overview, Welcome } from './DashboardPage';
import { ActivityPage, FilesPage, MappingPage, Structure } from './DataPages';
import { AgentWorkspace, ApprovalCenter } from './AgentPages';
import type { Context, Dashboard, Provider, SemanticCatalog, State, Workspace } from './types';

const pages=[
 {path:'/',name:'Overview',icon:LayoutDashboard,section:'workspace'},
 {path:'/files',name:'Excel files',icon:FolderOpen},
 {path:'/structure',name:'Structure explorer',icon:Layers3},
 {path:'/mapping',name:'Mapping review',icon:GitBranch},
 {path:'/analytics',name:'Business analytics',icon:ChartNoAxesCombined},
 {path:'/agents',name:'Agent workspace',icon:Bot,section:'your AI workforce'},
 {path:'/approvals',name:'Approval center',icon:ClipboardCheck},
 {path:'/activity',name:'Activity timeline',icon:Activity},
];
const emptyDashboard:Dashboard={revenue:[],units_sold:null,inventory_units:null,inventory_products:0,low_stock_count:0,stock:[],low_stock:[],sales_records:0,sales_trend:[],top_products:[],quality_issues:[],warnings:[],available_entities:[],confirmed_tables:0,pending_actions:0};
export default function App(){return <BrowserRouter><WorkspaceApp/></BrowserRouter>}
function WorkspaceApp(){
 const navigate=useNavigate(),location=useLocation();
 const [workspaces,setWorkspaces]=useState<Workspace[]>([]),[workspace,setWorkspace]=useState(localStorage.getItem('sheetpilot-workspace')||'');
 const [state,setState]=useState<State|null>(null),[stats,setStats]=useState<Dashboard>(emptyDashboard),[provider,setProvider]=useState<Provider>({configured:false,verified:false,model:'muse-spark-1.3',generation_verified:false});
 const [fields,setFields]=useState<string[]>([]),[busy,setBusy]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[loading,setLoading]=useState(true);
 const [semanticCatalog,setSemanticCatalog]=useState<SemanticCatalog>();
 const [newOpen,setNewOpen]=useState(false),[newName,setNewName]=useState(''),[mobile,setMobile]=useState(false),[settingsOpen,setSettingsOpen]=useState(false),[accessToken,setAccessToken]=useState(sessionStorage.getItem('sheetpilot-token')||'');
 const fileInput=useRef<HTMLInputElement>(null);
 const root='/workspaces/'+workspace;
 const reload=useCallback(async(id:string)=>{const [s,d]=await Promise.all([api<State>('/workspaces/'+id+'/state'),api<Dashboard>('/workspaces/'+id+'/dashboard')]);setState(s);setStats(d)},[]);
 async function initialize(){
  setLoading(true);setError('');
  try{
   const [list,p,catalog]=await Promise.all([api<Workspace[]>('/workspaces'),api<Provider>('/provider'),api<SemanticCatalog&{fields:string[]}>('/catalog')]);
   setProvider(p);setFields(catalog.fields);setSemanticCatalog(catalog);
   let available=list;
   if(!available.length)available=[await api<Workspace>('/workspaces','POST',{name:'My workspace'})];
   setWorkspaces(available);
   const id=available.some(w=>w.id===workspace)?workspace:available[0].id;
   setWorkspace(id);localStorage.setItem('sheetpilot-workspace',id);await reload(id);
  }catch(e){setError((e as Error).message)}
  finally{setLoading(false)}
 }
 const started=useRef(false);
 useEffect(()=>{if(!started.current){started.current=true;void initialize()}},[]);
 async function perform(message:string,task:()=>Promise<unknown>,success=''){
  setBusy(message);setError('');setNotice('');
  try{await task();if(workspace)await reload(workspace);if(success)setNotice(success)}
  catch(e){setError((e as Error).message);if(workspace)await reload(workspace).catch(()=>{})}
  finally{setBusy('')}
 }
 async function switchWorkspace(id:string){setWorkspace(id);localStorage.setItem('sheetpilot-workspace',id);setError('');setNotice('');await reload(id)}
 async function loadDemo(company:string){
  setBusy('Loading the company’s real Excel fixtures…');setError('');
  try{const w=await api<Workspace>('/demo/'+company,'POST');setWorkspaces(ws=>[w,...ws]);await switchWorkspace(w.id);navigate('/mapping');setNotice('Three workbooks loaded. Review their structure and mappings before using the numbers.')}
  catch(e){setError((e as Error).message)}finally{setBusy('')}
 }
 async function upload(files:FileList|File[]|null){
  if(!files)return;await perform('Inspecting your Excel workbooks…',async()=>{
   for(const file of Array.from(files)){const form=new FormData();form.append('file',file);await api(root+'/uploads','POST',form)}
   navigate('/files');
  },'Workbooks inspected. Your originals are preserved. Review mappings next.');
 }
 async function createWorkspace(){
  if(!newName.trim())return;
  setBusy('Creating workspace…');
  try{const w=await api<Workspace>('/workspaces','POST',{name:newName.trim()});setWorkspaces(ws=>[w,...ws]);setNewOpen(false);setNewName('');await switchWorkspace(w.id);navigate('/files')}
  catch(e){setError((e as Error).message)}finally{setBusy('')}
 }
 async function verify(){await perform('Verifying the official Meta API…',async()=>setProvider(await api<Provider>('/provider/verify','POST')),'Meta model access and a real generation request are verified.')}
 useEffect(()=>{const target=location.hash&&document.getElementById(location.hash.slice(1));if(target)target.scrollIntoView({block:"start"});else window.scrollTo(0,0)},[location.pathname,location.hash]);
 const page=pages.find(p=>p.path===location.pathname)||pages[0];
 const context:Context={state:state!,stats,provider,fields,catalog:semanticCatalog,busy,perform,root,workspace,navigate};
 return <div className="app-shell">
  <input ref={fileInput} className="hidden" type="file" accept=".xlsx" multiple aria-label="Upload Excel workbooks" data-testid="file-upload" onChange={e=>{void upload(e.target.files);e.target.value=''}}/>
  <aside className={'sidebar '+(mobile?'mobile-open':'')}>
   <NavLink to="/" className="brand"><span className="brand-mark"><i/><i/><i/><i/></span><span>sheetpilot<span className="brand-ai">AI</span></span></NavLink>
   <div className="workspace-switch"><span className="workspace-avatar">{state?.workspace.name.charAt(0)||'W'}</span><select aria-label="Select workspace" value={workspace} disabled={!!busy} onChange={e=>void switchWorkspace(e.target.value)}>{workspaces.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select><ChevronDown size={14}/></div>
   <nav aria-label="Main navigation">{pages.map(p=><div key={p.path}>{p.section&&<p className="nav-section">{p.section}</p>}<NavLink to={p.path} end={p.path==='/'} onClick={()=>setMobile(false)} className={({isActive})=>'nav-link '+(isActive?'active':'')}><p.icon size={19}/><span>{p.name}</span>{p.path==='/approvals'&&stats.pending_actions>0&&<span className="nav-count">{stats.pending_actions}</span>}</NavLink></div>)}</nav>
   <button className="new-workspace" onClick={()=>setNewOpen(true)}><Plus size={15}/>New workspace</button>
   <div className="sidebar-bottom"><div className="preserved"><ShieldCheck size={18}/><div><strong>Your Excel, preserved.</strong><span>Every change stays in your control.</span></div></div><button onClick={()=>setSettingsOpen(true)} className="meta-status"><span className={'status-dot '+(provider.verified?'online':'')}/><span>{provider.verified?'Meta connected':provider.configured?'Meta ready to verify':'Connect Meta AI'}<small>{provider.model}</small></span><ArrowUpRight size={15}/></button></div>
  </aside>
  <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" onClick={()=>setMobile(!mobile)} aria-label="Toggle navigation"><Menu size={20}/></button><span>Workspace</span><span className="crumb-divider">/</span><strong>{page.name}</strong></div><div className="top-actions"><span className="local-pill"><span className="status-dot online"/>Local workspace</span><Button onClick={()=>fileInput.current?.click()} disabled={!!busy}><Plus size={15}/>Upload workbooks</Button></div></header>
   <main className="content">
    {error&&<div role="alert" className="alert error"><CircleX size={18}/><span>{error}</span><button className="icon-button" onClick={()=>setError('')} aria-label="Dismiss error"><X size={16}/></button></div>}
    {notice&&<div className="alert success" role="status"><CircleCheck size={18}/><span>{notice}</span><button className="icon-button" onClick={()=>setNotice('')} aria-label="Dismiss notification"><X size={16}/></button></div>}
    {busy&&<div className="progress-banner"><Busy message={busy}/></div>}
    {loading?<div className="skeleton"><div/><div/><div/></div>:!state?<Empty icon={<Database/>} title="Connect to your workspace">Check that the backend is running. If an access token is configured, enter it in Connection settings.<Button onClick={()=>setSettingsOpen(true)}>Connection settings</Button></Empty>:
    <>
    {page.path==='/'&&<Overview {...context}>{!state.workbooks.length&&<Welcome loadDemo={loadDemo} upload={()=>fileInput.current?.click()} busy={!!busy}/>}</Overview>}
    {page.path==='/files'&&<FilesPage {...context} upload={upload} loadDemo={loadDemo} browse={()=>fileInput.current?.click()}/>}
    {page.path==='/structure'&&<Structure {...context}/>}
    {page.path==='/mapping'&&<MappingPage {...context}/>}
    {page.path==='/analytics'&&<Analytics {...context}/>}
    {page.path==='/agents'&&<AgentWorkspace {...context}/>}
    {page.path==='/approvals'&&<ApprovalCenter {...context}/>}
    {page.path==='/activity'&&<ActivityPage {...context}/>}
    </>}
    <footer className="page-footer"><span>SheetPilot AI · Your Spreadsheets. Your AI Workforce.</span><span>Built around your Excel. Controlled by you.</span></footer>
   </main>
  </div>
  <Modal open={newOpen} onOpenChange={setNewOpen} title="Create a workspace" description="Keep each business and its files separate."><form onSubmit={e=>{e.preventDefault();void createWorkspace()}}><label>Workspace name<input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="Your company" required maxLength={80}/></label><Button type="submit" disabled={!!busy||!newName.trim()}>Create workspace</Button></form></Modal>
  <Modal open={settingsOpen} onOpenChange={setSettingsOpen} title="Connections" description="Your Meta API key stays in the server’s ignored .env file."><div className="connection-card"><Badge tone={provider.verified?'green':'amber'}>{provider.verified?'Live generation verified':provider.configured?'Configured, not verified':'Not configured'}</Badge><h3>Meta Model API</h3><p>{provider.model}</p><p className="subtle">Set MODEL_API_KEY in the project’s .env, then verify a real generation request.</p><Button onClick={()=>void verify()} disabled={!!busy||!provider.configured}>Verify Meta connection</Button></div><form onSubmit={e=>{e.preventDefault();sessionStorage.setItem('sheetpilot-token',accessToken);setSettingsOpen(false);void initialize()}}><label>Workspace access token (optional)<input type="password" autoComplete="off" value={accessToken} onChange={e=>setAccessToken(e.target.value)} placeholder="Only if configured on your local server"/></label><Button variant="secondary" type="submit">Reconnect workspace</Button></form></Modal>
 </div>
}
