import { useEffect, useState } from 'react';
import { Check, ChevronDown, FileSpreadsheet, GitBranch, Link2, ShieldCheck, Sparkles } from 'lucide-react';
import { api, label } from './api';
import { Badge, Button, Empty, SectionTitle } from './components';
import type { Column, Context, Entity, SemanticCatalog, TableInfo, WorkbookInfo } from './types';
import { relationshipReview, relationshipSummary } from './relationshipReview';

const entities:Entity[]=['unknown','sales','orders','inventory','products','suppliers','supplier_directory','customers','purchases','payments'];
const required:Record<string,string[]>={sales:['product_id','quantity'],orders:['order_id'],inventory:['product_id','stock_quantity'],products:['product_id'],suppliers:['product_id','supplier_id','supplier_name','unit_cost'],supplier_directory:['supplier_id','supplier_name'],customers:['customer_id'],purchases:['purchase_order_id','product_id','quantity'],payments:['payment_id','payment_amount']};
interface Preview{columns:Column[];row_count:number;header_candidates:{row:number;labels:string[]}[];arithmetic_evidence:string[];label_hints?:{currency:string|null}}

export function MappingPage(context:Context){
 const {state,provider,root,busy,perform,fields,catalog}=context;
 const [filter,setFilter]=useState('all');
 const shown=state.tables.filter(t=>filter==='all'||(filter==='needs_review'?t.status!=='confirmed'&&t.status!=='ignored':t.status===filter));
 return <>
  <SectionTitle eyebrow="UNDERSTANDING, WITH EVIDENCE" title="Make the right connections." description="Map each table at its real business grain. Review evidence before using its data."/>
  <div className="mapping-toolbar panel"><div><Sparkles size={21}/><div><strong>Business meaning, with context.</strong><p>{fields.length} meanings · orders, customers, products, inventory, suppliers, payments and more.</p><small>Meta uses profiles, aligned samples, price arithmetic, and the other tables. Confirmed mappings stay unchanged unless you reanalyze a specific table.</small></div></div>
   <div><Button variant="secondary" disabled={!!busy} onClick={()=>void perform('Matching multilingual headers…',()=>api(root+'/suggest-labels','POST'),'Label suggestions and relationship previews generated. These are rules, not AI.')}>Label suggestions · no AI</Button><Button disabled={!!busy||!provider.configured} onClick={()=>void perform('Meta is interpreting profiles and business context…',()=>api(root+'/analyze-meta','POST'),'Meta suggestions are ready for your review.')}><Sparkles size={16}/>Analyze with Meta</Button></div>
  </div>
  {!state.tables.length&&<Empty icon={<GitBranch/>} title="No tables to map yet">Upload an Excel workbook, or add a source region in the structure explorer.</Empty>}
  {!!state.tables.length&&<div className="filter-tabs">{['all','needs_review','confirmed','ignored'].map(f=><button key={f} className={filter===f?'selected':''} onClick={()=>setFilter(f)}>{label(f)}</button>)}</div>}
  <div className="mapping-list">{shown.map(t=><MappingEditor key={t.id+':'+t.revision} table={t} workbook={state.workbooks.find(w=>w.id===t.workbook_id)!} fields={fields} catalog={catalog} root={root} busy={!!busy}
   save={body=>perform('Saving reviewed mapping…',()=>api(root+'/tables/'+t.id,'PUT',body),'Mapping saved. Calculations use confirmed tables only.')}
   reanalyze={()=>void perform('Meta is rechecking this table against the workspace…',()=>api(root+'/analyze-meta','POST',{table_ids:[t.id],include_confirmed:t.status==='confirmed'}),'New proposal ready. Confirm this mapping again before operational use.')}/>)}</div>
  <div className="panel relationships" id="relationships"><SectionTitle title="Relationships between tables" description="Connect sheets in the same workbook or different files. Discovery never confirms a link." action={<Button variant="secondary" disabled={!!busy} onClick={()=>void perform('Comparing business identifiers…',()=>api(root+'/relationships/discover','POST'),'Relationship evidence refreshed. Confirm source mappings before accepting links.')}><Link2 size={16}/>Discover relationships</Button>}/>
   {(state.relationship_report||!!state.relationships.length)&&<div className="relationship-report"><p>{relationshipSummary(state.relationships,state.tables)}</p>{state.relationship_report&&<><small>{state.relationship_report.compared_identifier_pairs} identifier pairs checked</small>{!!state.relationship_report.notes.length&&<details><summary>Discovery diagnostics</summary><ul>{state.relationship_report.notes.map((n,i)=><li key={i}>{n}</li>)}</ul></details>}</>}</div>}
   {!state.relationships.length?<Empty icon={<Link2/>} title="Find shared business identifiers">Map product, order, customer, supplier or other IDs, then discover links. Unconfirmed mappings can show previews; both tables must be confirmed to accept a link.</Empty>:state.relationships.map(r=>{
    const left=state.tables.find(t=>t.id===r.left_table),right=state.tables.find(t=>t.id===r.right_table);
    const {ready,needsRefresh,reasons}=relationshipReview(r,left,right);
    const source=(t:TableInfo|undefined)=>{const w=state.workbooks.find(w=>w.id===t?.workbook_id);return `${w?.name||'Workbook'} / ${t?.sheet||'Table'} · ${t?.ref||''}`};
    return <div className="relationship" key={r.id}>
     <div className="relationship-join"><Badge>{label(left?.entity||'table')}</Badge><Link2 size={16}/><Badge>{label(right?.entity||'table')}</Badge><strong>{label(r.field)}</strong><Badge tone={r.status==='confirmed'?'green':r.strength==='weak'?'amber':''}>{r.status==='proposed'?r.strength+' evidence':r.status}</Badge>{r.cardinality&&<Badge tone="outline">{r.cardinality}</Badge>}</div>
     <div className="relationship-sources"><span>{source(left)}<small>Column {r.left_column}: {left?.columns.find(c=>String(c.index)===r.left_column)?.label}</small></span><span>{source(right)}<small>Column {r.right_column}: {right?.columns.find(c=>String(c.index)===r.right_column)?.label}</small></span></div>
     <p>{r.evidence}</p><small>Matching values: {r.matching_examples.join(', ')||'none'}</small>
     {reasons.map((b,i)=><p className="mapping-warning" key={i}>{b}</p>)}
     {r.cardinality==='many-to-many'&&<p className="mapping-warning">Neither side is unique. A direct join could multiply rows; master-data enrichment requires a unique match.</p>}
     <div className="relationship-actions">{needsRefresh&&<Button variant="secondary" disabled={!!busy} onClick={()=>void perform('Refreshing relationship evidence…',()=>api(root+'/relationships/discover','POST'),'Relationship evidence refreshed. Review the current proposals before confirming.')}>Refresh relationship evidence</Button>}{r.status!=='confirmed'&&r.status!=='rejected'&&<><Button variant="secondary" disabled={!!busy||!ready} onClick={()=>void perform('Confirming relationship…',()=>api(root+'/relationships/'+r.id,'PUT',{decision:'approve'}),'Relationship confirmed. Eligible derived context refreshed.')}>Confirm relationship</Button><Button variant="ghost" disabled={!!busy} onClick={()=>void perform('Rejecting relationship…',()=>api(root+'/relationships/'+r.id,'PUT',{decision:'reject'}))}>Reject</Button></>}</div>
    </div>
   })}
  </div>
 </>
}

export function MappingEditor({table,workbook,fields,catalog,root,busy,save,reanalyze}:{table:TableInfo;workbook:WorkbookInfo;fields:string[];catalog?:SemanticCatalog;root:string;busy:boolean;save:(body:unknown)=>Promise<void>;reanalyze:()=>void}){
 const [open,setOpen]=useState(table.status!=='confirmed'&&table.status!=='ignored'||window.location.hash==='#table-'+table.id);
 const [entity,setEntity]=useState<Entity>(table.entity),[mapping,setMapping]=useState(table.fields),[header,setHeader]=useState(table.header_row);
 const [currency,setCurrency]=useState(table.constants?.currency||''),[search,setSearch]=useState('');
 const [preview,setPreview]=useState<Preview|null>(null),[previewError,setPreviewError]=useState(''),[loading,setLoading]=useState(false);
 useEffect(()=>{if(!open)return;let active=true;setLoading(true);setPreviewError('');
  api<Preview>(root+'/tables/'+table.id+'/preview?header_row='+header).then(p=>{if(active)setPreview(p)}).catch(e=>{if(active){setPreview(null);setPreviewError((e as Error).message)}}).finally(()=>{if(active)setLoading(false)});
  return ()=>{active=false};
 },[root,table.id,header,open]);
 const columns=preview?.columns||table.columns;
 const used=Object.values(mapping).filter(v=>v&&v!=='ignore');
 const missing=(catalog?.entity_catalog[entity]?.required||required[entity]||[]).filter(f=>!used.includes(f));
 const errors=[...missing.map(f=>'Required: '+label(f)),...(used.length!==new Set(used).size?['Each meaning can be used only once.']:[]),
  ...(entity==='sales'&&!used.includes('revenue')&&!(used.includes('quantity')&&used.includes('unit_price'))?['Sales need line revenue or quantity and actual selling unit price.']:[]),
  ...(currency&&!/^[A-Z]{3}$/.test(currency)?['Table currency must be a three-letter code.']:[]),
  ...(currency&&used.includes('currency')?['Choose a currency column or table currency, not both.']:[])];
 const warnings=[...(entity==='inventory'&&!used.includes('reorder_point')?['Stock can be analyzed. Replenishment stays disabled without a reviewed reorder point.']:[]),
  ...(['sales','orders','suppliers','payments','purchases'].includes(entity)&&!currency&&!used.includes('currency')?['No reviewed currency: monetary KPIs will omit these rows.']:[])];
 const body=(confirm:boolean,ignore=false)=>({entity:ignore?'unknown':entity,fields:ignore?{}:Object.fromEntries(Object.entries(mapping).filter(([,v])=>v)),header_row:header,expected_revision:table.revision,confirm,ignore,constants:ignore||!currency?{}:{currency}});
 const groups:Record<string,string[]>={};
 for(const field of fields){const info=catalog?.field_catalog[field];if(search&&!`${field} ${info?.description||''}`.toLowerCase().includes(search.toLowerCase()))continue;(groups[info?.group||'Business meanings']||=[]).push(field)}
 return <article id={'table-'+table.id} className={'panel mapping-card '+(table.status==='confirmed'?'reviewed':'')} data-testid={'mapping-'+table.entity} data-status={table.status}>
  <button className="mapping-card-heading" onClick={()=>setOpen(!open)}><span className="file-symbol"><FileSpreadsheet size={21}/></span><span><strong>{workbook.name} <span className="subtle">/ {table.sheet}</span></strong><small>{table.ref} · header row {table.header_row} · {table.columns.length} columns</small></span><Badge tone={table.status==='confirmed'?'green':table.status==='ignored'?'':'amber'}>{table.status}</Badge><Badge tone="outline">{label(table.entity)}</Badge><ChevronDown size={17} className={open?'rotated':''}/></button>
  {open&&<div className="mapping-body">
   <div className="mapping-meta"><label>Business entity<select aria-label={'Entity for '+workbook.name+' '+table.ref} value={entity} onChange={e=>setEntity(e.target.value as Entity)}>{entities.map(v=><option key={v} value={v}>{label(v)}</option>)}</select></label>
    <label>Header row<input aria-label={'Header row for '+table.sheet} type="number" min={1} value={header} onChange={e=>{setHeader(Number(e.target.value));setMapping({});setPreview(null)}}/></label>
    <div><Badge tone="outline">{table.origin==='meta'?'Meta proposal':table.origin==='label-rules'?'Label rules · not AI':table.origin==='human-reviewed'?'Reviewed by you':'Not yet mapped'}</Badge><small>{Math.round(table.confidence*100)}% estimated confidence · not measured accuracy</small></div>
   </div>
   {catalog?.entity_catalog[entity]&&<p className="subtle">{catalog.entity_catalog[entity].description}</p>}
   <div className="mapping-controls"><label>Find a meaning<input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Customer, discount, warehouse…"/></label><label>Table currency (optional)<input aria-label={'Table currency for '+table.sheet} value={currency} maxLength={3} placeholder="e.g. GBP" onChange={e=>setCurrency(e.target.value.toUpperCase().trim())}/><small>Applies to every row after confirmation. Leave blank if a currency column is mapped.</small></label></div>
   {!currency&&!used.includes('currency')&&preview?.label_hints?.currency&&<div className="source-checks"><p>The monetary headers explicitly name {preview.label_hints.currency}. Review this setting before including these rows in monetary analytics.</p><Button variant="secondary" disabled={busy} onClick={()=>setCurrency(preview.label_hints!.currency!)}>Use {preview.label_hints.currency} for this table</Button><small>This fills the draft only. Click Confirm mapping to apply it.</small></div>}
   {loading&&<p role="status">Loading source profile…</p>}{previewError&&<p role="alert" className="mapping-warning">{previewError}</p>}
   {header!==table.header_row&&<p className="mapping-warning">Header changed: source labels and samples are reloaded. Remap the columns before confirming.</p>}
   <div className="table-wrap"><table><thead><tr><th>Original column / profile</th><th>Sample values</th><th>Business meaning / evidence</th></tr></thead><tbody>{columns.map(c=>{
    const field=mapping[String(c.index)]||'',detail=table.field_details?.[String(c.index)];
    return <tr key={c.index}><td><strong dir="auto">{c.label||'Unlabeled column'}</strong><small>{c.coordinate}</small>{c.profile&&<small>{c.profile.distinct} distinct · {c.profile.missing} missing{c.profile.formula_count?` · ${c.profile.formula_count} formulas`:''}</small>}</td><td className="sample-values" dir="auto">{c.samples.map(v=>String(v)).join(' · ')}</td>
     <td className="meaning-cell"><select aria-label={'Meaning of '+c.label+' '+table.ref} value={field} onChange={e=>setMapping(m=>({...m,[String(c.index)]:e.target.value}))}><option value="">Keep as custom field</option>{field&&field!=='ignore'&&!Object.values(groups).flat().includes(field)&&<option value={field}>{label(field)}</option>}{Object.entries(groups).map(([group,options])=><optgroup key={group} label={group}>{options.map(f=><option key={f} value={f}>{label(f)}</option>)}</optgroup>)}<option value="ignore">Exclude this column</option></select>
      {catalog?.field_catalog[field]&&<small>{catalog.field_catalog[field].description}</small>}
      {detail&&header===table.header_row&&field===table.fields[String(c.index)]&&<details className="field-evidence"><summary>{Math.round(detail.confidence*100)}% estimate · evidence{detail.confidence<.75?' · review carefully':''}</summary><p>{detail.evidence}</p>{!!detail.alternatives?.length&&<p>Alternatives: {detail.alternatives.map(label).join(', ')}</p>}</details>}
     </td></tr>
   })}</tbody></table></div>
   {!!preview?.arithmetic_evidence.length&&<div className="source-checks"><strong>Observed arithmetic checks</strong>{preview.arithmetic_evidence.map((e,i)=><p key={i}>{e}</p>)}</div>}
   {!!table.evidence.length&&<details className="evidence"><summary>Why this mapping? View evidence</summary><ul>{table.evidence.map((e,i)=><li key={i}>{e}</li>)}</ul></details>}
   {!!errors.length&&<div className="mapping-warning" role="status">{errors.join(' · ')}</div>}{warnings.map(w=><p className="mapping-warning" key={w}>{w}</p>)}
   <div className="mapping-footer"><p><ShieldCheck size={14}/>Confirming updates the derived mirror. Originals stay untouched.</p><Button variant="ghost" disabled={busy} onClick={()=>void save(body(false,true))}>Exclude table</Button><Button variant="secondary" disabled={busy||loading||!!previewError} onClick={()=>void save(body(false))}>Save draft</Button><Button disabled={busy||loading||!!previewError||entity==='unknown'||!!errors.length} onClick={()=>void save(body(true))}><Check size={16}/>Confirm mapping</Button></div>
   <div className="mapping-reanalyze"><Button variant="ghost" disabled={busy} onClick={reanalyze}><Sparkles size={14}/>Reanalyze this table with Meta</Button><small>{table.status==='confirmed'?'Replaces this reviewed mapping with a proposal and invalidates its relationships. Review is required again.':'Only this table is analyzed; other mappings provide read-only context.'}</small></div>
  </div>}
 </article>
}
