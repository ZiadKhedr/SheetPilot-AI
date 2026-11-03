import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DemandPlanner } from './DemandPlanner';
import { api } from './api';
import type { State } from './types';

vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const parameters={window_days:30,lead_time_days:2,safety_days:1,review_period_days:4,as_of:'2026-01-10'};
const report={parameters,policy:{enabled:false,revision:0,reviewed_at:null},preview:false,as_of:'2026-01-10',basis:'dated sales',formula:'',warnings:['Historical scenario.'],products:[{
 product_id:'A',product_name:'Fast widget',stock_quantity:'8',observed_days:10,sales_units:'40',daily_sales:'4.0000',days_remaining:'2.0000',estimated_stockout_date:'2026-01-12',
 reorder_point:'12',target_stock:'28',suggested_quantity:'20',eligible:true,needs_reorder:true,status:'reorder_soon',warnings:[],window_start:'2026-01-01',window_end:'2026-01-10',sales_records:3,active_days:3,
}]};
const state={tables:[],relationships:[]} as unknown as State;
function setup(){
 vi.mocked(api).mockResolvedValue(report);
 const perform=vi.fn(async(_message:string,task:()=>Promise<unknown>)=>{await task()});
 render(<DemandPlanner root="/workspaces/test" state={state} busy="" perform={perform} navigate={()=>{}}/>);
 return perform;
}
test('demand and days of cover display without enabling a policy',async()=>{
 setup();expect(await screen.findByText('Fast widget')).toBeVisible();
 expect(screen.getByText('2026-01-12')).toBeVisible();expect(screen.getByText('20')).toBeVisible();
 expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeDisabled();
 expect(api).toHaveBeenCalledTimes(1);
});
test('editing assumptions requires preview; preview does not save policy',async()=>{
 setup();await screen.findByText('Fast widget');
 fireEvent.change(screen.getByRole('spinbutton',{name:'Delivery lead time (days)'}),{target:{value:'4'}});
 fireEvent.click(screen.getByRole('checkbox'));
 expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeDisabled();
 vi.mocked(api).mockResolvedValue({...report,parameters:{...parameters,lead_time_days:4},preview:true});
 fireEvent.click(screen.getByRole('button',{name:'Preview calculations'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeEnabled());
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/demand/preview','POST',{...parameters,lead_time_days:4});
 expect(vi.mocked(api).mock.calls.some(c=>c[0].endsWith('/policy'))).toBe(false);
});
test('confirming a policy requires an explicit snapshot acknowledgement and current revision',async()=>{
 const perform=setup();await screen.findByText('Fast widget');
 fireEvent.click(screen.getByRole('checkbox'));
 fireEvent.click(screen.getByRole('button',{name:'Confirm sales-based planning policy'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/workspaces/test/demand/policy','PUT',{
  ...parameters,expected_revision:0,enabled:true,stock_snapshot_confirmed:true,
 }));
 expect(perform).toHaveBeenCalledOnce();
});

test('preview reports completion even when identical inputs leave all results unchanged',async()=>{
 setup();await screen.findByText('Fast widget');
 vi.mocked(api).mockResolvedValue({...report,preview:true});
 fireEvent.click(screen.getByRole('button',{name:'Preview calculations'}));
 const feedback=await screen.findByRole('status');
 expect(feedback).toHaveTextContent('Preview complete: 1 of 1 products');
 expect(feedback).toHaveTextContent('Results are unchanged');
 expect(screen.getByText(/does not activate the policy or create a purchase order/)).toBeVisible();
 expect(screen.getByRole('button',{name:'View product results'})).toBeEnabled();
 expect(screen.getByRole('button',{name:'Review policy confirmation'})).toBeEnabled();
 expect(vi.mocked(api).mock.calls.some(c=>c[0].endsWith('/policy'))).toBe(false);
});

test('preview has an explicit in-progress state',async()=>{
 setup();await screen.findByText('Fast widget');
 let finish!:(value:typeof report)=>void;
 vi.mocked(api).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 fireEvent.click(screen.getByRole('button',{name:'Preview calculations'}));
 expect(screen.getByRole('button',{name:'Calculating…'})).toBeDisabled();
 finish({...report,preview:true});
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('Preview complete'));
});

test('failed preview exposes its error instead of showing success',async()=>{
 setup();await screen.findByText('Fast widget');
 vi.mocked(api).mockRejectedValueOnce(new Error('Preview request timed out.'));
 fireEvent.click(screen.getByRole('button',{name:'Preview calculations'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Preview request timed out.');
 expect(screen.queryByText(/Preview complete:/)).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Preview calculations'})).toBeEnabled();
 fireEvent.click(screen.getByRole('checkbox'));
 expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeDisabled();
});

test('missing links have a clear next step and cannot be solved by blindly enabling the policy',async()=>{
 vi.mocked(api).mockResolvedValue({...report,products:[{...report.products[0],eligible:false,status:'relationship_review'}]});
 const navigate=vi.fn();
 render(<DemandPlanner root="/workspaces/test" state={state} busy="" perform={vi.fn()} navigate={navigate}/>);
 await screen.findByText('Fast widget');
 expect(screen.getByText(/Review sales dates and product relationships first/)).toBeVisible();
 fireEvent.click(screen.getByRole('checkbox'));
 expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Review sales data and links'}));
 expect(navigate).toHaveBeenCalledWith('/mapping#relationships');
});

test('changing the scenario clears an earlier snapshot acknowledgement',async()=>{
 setup();await screen.findByText('Fast widget');
 fireEvent.click(screen.getByRole('checkbox'));expect(screen.getByRole('checkbox')).toBeChecked();
 fireEvent.change(screen.getByLabelText('Stock snapshot / scenario date'),{target:{value:'2026-01-09'}});
 expect(screen.getByRole('checkbox')).not.toBeChecked();
 expect(screen.getByRole('button',{name:'Confirm sales-based planning policy'})).toBeDisabled();
});
