import { Link } from 'react-router-dom';
import { Badge, SectionTitle } from './components';
export interface StepChecklist {fingerprint:string;items:{id:string;title:string;status:string;explanation:string;targets:{label:string;href:string}[]}[]}
export function NextSteps({steps}:{steps?:StepChecklist}){
 if(!steps)return null;
 return <section className="panel next-steps" aria-label="Workspace next steps"><SectionTitle title="Your next useful steps" description="Based on the current files, reviews and results in this workspace."/>
 <ol>{steps.items.map(item=><li key={item.id} data-step={item.id}><div><strong>{item.title}</strong><Badge tone={item.status==='done'?'green':item.status==='blocked'?'':'amber'}>{item.status==='done'?'Reviewed / complete':item.status==='blocked'?'Waiting':'Next step'}</Badge></div><p>{item.explanation}</p><div className="next-step-links">{item.targets.map((target,i)=><Link key={i} to={target.href}>{target.label}</Link>)}</div></li>)}</ol></section>;
}
