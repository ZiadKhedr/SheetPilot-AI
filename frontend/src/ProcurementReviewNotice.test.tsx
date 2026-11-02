import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ProcurementReviewNotice } from './ProcurementReviewNotice';
afterEach(cleanup);
const readiness={ready:false,low_stock_count:3,ready_count:0,blockers:[{
 code:'relationship_review',product_id:'R01',message:'R01: supplier quote exists, but its relationship needs review.',
 next_step:'review_relationships',inventory_table_id:'stock',
}]};
test('missing supplier review has a direct recovery button',()=>{
 const onReview=vi.fn();render(<ProcurementReviewNotice readiness={readiness} busy={false} onReview={onReview}/>);
 expect(screen.getByRole('heading',{name:'Procurement needs your review'})).toBeInTheDocument();
 expect(screen.getByText(/R01: supplier quote exists/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Discover & review supplier links'}));expect(onReview).toHaveBeenCalledOnce();
});
test('data issues point to data review and do not claim relationship review will fix them',()=>{
 render(<ProcurementReviewNotice readiness={{...readiness,blockers:[{...readiness.blockers[0],code:'missing_supplier_quote',next_step:'review_data'}]}} busy={false} onReview={()=>{}}/>);
 expect(screen.getByRole('button',{name:'Review supplier data'})).toBeVisible();
});
test('ready workspace has no blocker notice',()=>{
 const {container}=render(<ProcurementReviewNotice readiness={{ready:true,low_stock_count:3,ready_count:3,blockers:[]}} busy={false} onReview={()=>{}}/>);
 expect(container).toBeEmptyDOMElement();
});
