import { useEffect, useState } from 'react';
export default function App() {
 const [files,setFiles]=useState<any[]>([]);
 const [workspace,setWorkspace]=useState('');
 const [error,setError]=useState('');
 useEffect(()=>{fetch('/api/workspaces').then(r=>r.json()).then(async w=>{
  const selected=w[0]||await fetch('/api/workspaces',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'My workspace'})}).then(r=>r.json());
  setWorkspace(selected.id);
  fetch('/api/workspaces/'+selected.id+'/state').then(r=>r.json()).then(s=>setFiles(s.workbooks));
 }).catch(e=>setError(String(e)))},[]);
 async function upload(input:FileList|null) {
  if(!input)return;
  for(const file of Array.from(input)){const form=new FormData();form.append('file',file);
   const response=await fetch('/api/workspaces/'+workspace+'/uploads',{method:'POST',body:form});
   const data=await response.json();if(!response.ok){setError(data.detail);return;}
   setFiles(f=>[...f,data]);
  }
 }
 return <main><h1>SheetPilot AI</h1><p>Your Spreadsheets. Your AI Workforce.</p><h2>Excel File Manager</h2><input aria-label="Upload Excel workbooks" type="file" multiple accept=".xlsx" onChange={e=>upload(e.target.files)}/>{error&&<p role="alert">{error}</p>}{files.map(f=><section key={f.id}><h3>{f.name}</h3><p>{f.report.sheet_count} worksheets · original preserved</p><pre>{JSON.stringify(f.report.worksheets.map((s:any)=>({sheet:s.title,state:s.state,tables:s.tables.map((t:any)=>({ref:t.ref,header:t.header_row}))})),null,2)}</pre></section>)}</main>;
}
