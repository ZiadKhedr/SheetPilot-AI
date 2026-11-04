import { useState } from 'react';
import { Archive, ShieldCheck } from 'lucide-react';
import { api, downloadBackup } from './api';
import { Button, SectionTitle } from './components';
import type { Context } from './types';

interface RestoreResult {status:string;data_dir:string;message:string;counts:{workspaces:number;objects:number;files:number}}
export function WorkspaceRecovery({busy,perform}:Context){
 const [file,setFile]=useState<File|null>(null),[restored,setRestored]=useState<RestoreResult|null>(null);
 return <><SectionTitle eyebrow="KEEP YOUR WORK" title="Backup and restore" description="Save a consistent copy of all local workspaces, including reviews, policies, audit history and referenced Excel files."/>
 <section className="panel recovery-panel"><Archive size={24}/><h3>Download an installation backup</h3><p>Includes the database, immutable originals and approved output workbooks, with a versioned manifest and SHA256 hashes. Store the download somewhere you can recover it.</p><Button disabled={!!busy} onClick={()=>void perform('Creating a consistent backup…',downloadBackup,'Backup downloaded. Keep it in a safe location.')}>Download backup</Button></section>
 <section className="panel recovery-panel"><ShieldCheck size={24}/><h3>Restore into a separate installation</h3><p>Choose a SheetPilot backup ZIP. The server validates paths, sizes, schema, references and every file hash before publishing a new data folder. Your current workspaces stay available.</p>
 <label>Backup archive<input type="file" accept=".zip" aria-label="Backup archive" disabled={!!busy} onChange={e=>{setFile(e.target.files?.[0]||null);setRestored(null)}}/></label>
 <Button disabled={!!busy||!file} onClick={()=>void perform('Validating and restoring the backup…',async()=>{if(!file)return;const form=new FormData();form.append('file',file);setRestored(null);setRestored(await api<RestoreResult>('/backups/restore','POST',form))},'Backup verified and restored into a separate installation.')}>Validate and restore</Button>
 {restored&&<div className="alert success restore-result" role="status"><div><strong>Restore verified</strong><p>{restored.counts.workspaces} workspaces · {restored.counts.files} Excel files · {restored.counts.objects} saved objects</p><p>{restored.message}</p><label>Restored data folder<input readOnly value={restored.data_dir} onFocus={e=>e.target.select()}/></label><p>For a separate local server, set this environment variable in a new terminal, then start SheetPilot on an unused port:</p><code>SHEETPILOT_DATA_DIR={restored.data_dir}</code><p>Connection credentials are configured separately on that server.</p></div></div>}
 </section></>;
}
