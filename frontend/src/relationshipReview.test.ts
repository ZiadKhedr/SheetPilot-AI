import { expect, test } from 'vitest';
import { relationshipReview, relationshipSummary } from './relationshipReview';
import type { Relationship, TableInfo } from './types';

const left={id:'sales',sheet:'Sales',ref:'A1:C9',status:'confirmed',revision:5,fields:{'1':'order_id'}} as unknown as TableInfo;
const right={id:'orders',sheet:'Orders',ref:'A1:C5',status:'confirmed',revision:6,fields:{'1':'order_id'}} as unknown as TableInfo;
const link:Relationship={id:'r',left_table:'sales',right_table:'orders',field:'order_id',left_column:'1',right_column:'1',status:'stale',
 revisions:[4,5],coverage:1,overlap_count:4,strength:'strong',matching_examples:['O1'],evidence:'Four matching IDs.',
 blockers:['Confirm both source mappings with these identifier columns first.']};

test('confirmed mappings with old evidence need refresh, not repeated confirmation',()=>{
 const review=relationshipReview(link,left,right);
 expect(review.ready).toBe(false);expect(review.needsRefresh).toBe(true);
 expect(review.reasons).toEqual(['Source mappings changed. Refresh relationship evidence to use their current revisions.']);
 expect(relationshipSummary([link],[left,right])).toContain('Source mappings are confirmed. Refresh');
});
test('fresh proposal enables confirmation even if a legacy blocker string is persisted',()=>{
 const fresh={...link,status:'proposed',revisions:[5,6] as [number,number]};
 expect(relationshipReview(fresh,left,right)).toEqual({ready:true,needsRefresh:false,reasons:[]});
 expect(relationshipSummary([fresh],[left,right])).toContain('Review each proposed relationship');
});
test('unfinished mapping is identified by sheet and range',()=>{
 const review=relationshipReview(link,left,{...right,status:'suggested'});
 expect(review.reasons[0]).toBe('Confirm source mapping: Orders (A1:C5).');
 expect(relationshipSummary([link],[left,{...right,status:'suggested'}])).toContain('Some source mappings');
});
test('current review constraints still reject normalized previews and changed identifier meanings',()=>{
 const fresh={...link,status:'proposed',revisions:[5,6] as [number,number],match_mode:'normalized-preview'};
 expect(relationshipReview(fresh,left,right).ready).toBe(false);
 expect(relationshipReview({...fresh,match_mode:'exact'},left,{...right,fields:{'1':'customer_id'}}).ready).toBe(false);
});
test('completed relationship summary does not ask for mapping confirmation again',()=>{
 expect(relationshipSummary([{...link,status:'confirmed',revisions:[5,6]}],[left,right])).toBe('1 relationship confirmed. 0 rejected. No proposed links remain.');
});
