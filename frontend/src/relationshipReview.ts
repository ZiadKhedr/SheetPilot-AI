import type { Relationship, TableInfo } from './types';

export function relationshipReview(relation:Relationship,left?:TableInfo,right?:TableInfo){
 const reasons:string[]=[];
 if(!left||!right)return {ready:false,needsRefresh:false,reasons:['A source table is missing. Review the source regions.']};
 const needsRefresh=relation.status==='stale'||!!relation.revisions&&
  (relation.revisions[0]!==left.revision||relation.revisions[1]!==right.revision);
 const unconfirmed=[left,right].filter(t=>t.status!=='confirmed');
 if(unconfirmed.length)reasons.push('Confirm source mapping: '+unconfirmed.map(t=>t.sheet+' ('+t.ref+')').join(', ')+'.');
 if(needsRefresh)reasons.push('Source mappings changed. Refresh relationship evidence to use their current revisions.');
 else {
  if(relation.left_column&&left.fields[relation.left_column]!==relation.field||relation.right_column&&right.fields[relation.right_column]!==relation.field)
   reasons.push('Review the identifier meanings in both source mappings, then refresh evidence.');
  if(relation.match_mode&&relation.match_mode!=='exact')reasons.push('Formatting-normalized matches are preview only. Resolve source ID formatting before confirmation.');
  if(relation.overlap_count<1)reasons.push('No shared source identifiers were found.');
 }
 return {ready:reasons.length===0,needsRefresh,reasons};
}

export function relationshipSummary(relationships:Relationship[],tables:TableInfo[]){
 if(!relationships.length)return 'Discover shared identifiers to review possible links.';
 const reviews=relationships.map(r=>relationshipReview(r,tables.find(t=>t.id===r.left_table),tables.find(t=>t.id===r.right_table)));
 const unconfirmed=relationships.some(r=>[r.left_table,r.right_table].some(id=>tables.find(t=>t.id===id)?.status!=='confirmed'));
 if(unconfirmed)return 'Some source mappings still need confirmation. Each link lists its remaining steps.';
 if(reviews.some(r=>r.needsRefresh))return 'Source mappings are confirmed. Refresh relationship evidence before confirming these links.';
 const pending=relationships.filter(r=>!['confirmed','rejected'].includes(r.status)).length;
 if(pending)return 'Source mappings are confirmed. Review each proposed relationship before accepting it.';
 const confirmed=relationships.filter(r=>r.status==='confirmed').length;
 return `${confirmed} relationship${confirmed===1?'':'s'} confirmed. ${relationships.length-confirmed} rejected. No proposed links remain.`;
}
