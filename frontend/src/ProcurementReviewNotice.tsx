import { GitBranch } from 'lucide-react';
import { Badge, Button } from './components';
import type { ProcurementReadiness } from './types';

export function ProcurementReviewNotice({readiness,busy,onReview}:{readiness:ProcurementReadiness;busy:boolean;onReview:()=>void}){
 if(!readiness.blockers.length)return null;
 const relationships=readiness.blockers.some(b=>b.next_step==='review_relationships');
 return <section className="procurement-review panel" aria-label="Procurement review required">
  <div className="review-notice-heading"><GitBranch size={22}/><div><h3>Procurement needs your review</h3><p>Purchase-order drafts stay blocked until these source checks are resolved.</p></div><Badge tone="amber">Needs review</Badge></div>
  <ul>{readiness.blockers.map(b=><li key={b.product_id+':'+b.code}>{b.message}</li>)}</ul>
  <Button variant="secondary" disabled={busy} onClick={onReview}>{relationships?'Discover & review supplier links':'Review supplier data'}</Button>
  <small>Relationships are proposed using actual matching values. Only you can confirm them.</small>
 </section>
}
