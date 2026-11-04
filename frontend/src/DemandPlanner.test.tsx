import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {DemandPlanner} from './DemandPlanner';
import {api} from './api';
import type {State} from './types';

vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const parameters={window_days:30,lead_time_days:2,safety_days:1,review_period_days:4,as_of:'2026-01-10'};
const report={parameters,policy:{enabled:false,revision:0,reviewed_at:null},preview:false,as_of:'2026-01-10',warnings:['Historical scenario.'],products:[{
 product_id:'A',product_name:'Fast widget',stock_quantity:'8',source_reorder_point:null,sales_units:'40',observed_days:10,daily_sales:'4.0000',days_remaining:'2.0000',estimated_stockout_date:'2026-01-12',
 reorder_point:'12',target_stock:'28',suggested_quantity:'20',eligible:true,needs_reorder:true,status:'reorder_soon',warnings:[],window_start:'2026-01-01',window_end:'2026-01-10',sales_records:3,active_days:3,
}]};
const state={tables:[],relationships:[]} as unknown as State;
function setup(value:unknown=report){
 vi.mocked(api).mockResolvedValue(value);
 const perform=vi.fn(async(_message:string,task:()=>Promise<unknown>)=>{await task()});
 const navigate=vi.fn();
 render(<DemandPlanner root="/workspaces/test" state={state} busy="" perform={perform} navigate={navigate}/>);
 return {perform,navigate};
}
async function openSettings(){await screen.findByText('Fast widget');fireEvent.click(screen.getByRole('button',{name:'Change settings'}))}
async function openOrdering(){await screen.findByText('Fast widget');fireEvent.click(screen.getByRole('button',{name:/Optional: use sales/}))}

test('first view shows what needs attention without a form or policy jargon',async()=>{
 const {navigate}=setup();
 expect(await screen.findByRole('heading',{name:'1 product needs attention'})).toBeVisible();
 expect(screen.getByText('Could run out around 12 Jan 2026')).toBeVisible();
 expect(screen.queryByRole('spinbutton')).toBeNull();
 expect(screen.queryByRole('checkbox')).toBeNull();
 expect(screen.queryByRole('button',{name:'Save ordering settings'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Review restocking'}));
 expect(navigate).toHaveBeenCalledWith('/agents');expect(api).toHaveBeenCalledTimes(1);
});

test('delivery risk and cards are ordered by days of stock, with calculations available on request',async()=>{
 const fast={...report.products[0],product_id:'B',product_name:'Urgent item',days_remaining:'1'};
 setup({...report,products:[report.products[0],fast]});
 await screen.findByText('Urgent item');
 expect(screen.getAllByRole('article')[0]).toHaveAccessibleName('Urgent item stock estimate');
 expect(screen.getByText(/1 product may run out before a 2-day delivery/)).toBeVisible();
 const card=within(screen.getByRole('article',{name:'Fast widget stock estimate'}));
 fireEvent.click(card.getByText('Why these numbers?'));
 expect(card.getByText(/40 units sold over 10 calendar days/)).toBeVisible();
 expect(card.getByText(/8 in stock ÷ 4 sold per day = about 2 days/)).toBeVisible();
 expect(card.getByText(/Test top-up: 20 units/)).toBeVisible();
});

test('editing settings requires updating the estimate before saving and does not write a policy',async()=>{
 setup();await openSettings();await openOrdering();
 fireEvent.change(screen.getByRole('spinbutton',{name:'Supplier delivery days'}),{target:{value:'4'}});
 fireEvent.click(screen.getByRole('checkbox'));
 expect(screen.getByRole('button',{name:'Save ordering settings'})).toBeDisabled();
 vi.mocked(api).mockResolvedValue({...report,parameters:{...parameters,lead_time_days:4},preview:true});
 fireEvent.click(screen.getByRole('button',{name:'Update estimate'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Save ordering settings'})).toBeEnabled());
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/demand/preview','POST',{...parameters,lead_time_days:4});
 expect(vi.mocked(api).mock.calls.some(c=>c[0].endsWith('/policy'))).toBe(false);
});

test('saving an ordering rule still requires date and unit acknowledgement plus the current revision',async()=>{
 const {perform}=setup();await openOrdering();
 expect(screen.getByRole('button',{name:'Save ordering settings'})).toBeDisabled();
 fireEvent.click(screen.getByRole('checkbox'));
 fireEvent.click(screen.getByRole('button',{name:'Save ordering settings'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/workspaces/test/demand/policy','PUT',{...parameters,enabled:true,expected_revision:0,stock_snapshot_confirmed:true}));
 expect(perform).toHaveBeenCalledOnce();
});

test('an unchanged estimate reports completion instead of appearing unresponsive',async()=>{
 setup();await openSettings();vi.mocked(api).mockResolvedValue({...report,preview:true});
 fireEvent.click(screen.getByRole('button',{name:'Update estimate'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Results are unchanged');
 expect(vi.mocked(api).mock.calls.some(c=>c[0].endsWith('/policy'))).toBe(false);
});

test('updating an estimate has a visible busy state and prevents another update',async()=>{
 setup();await openSettings();let finish!:(value:unknown)=>void;
 vi.mocked(api).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 fireEvent.click(screen.getByRole('button',{name:'Update estimate'}));
 expect(screen.getByRole('button',{name:'Updating…'})).toBeDisabled();
 expect(screen.getByRole('spinbutton',{name:'Supplier delivery days'})).toBeDisabled();
 finish({...report,preview:true});await screen.findByRole('status');
});

test('a failed update exposes the error and keeps saving disabled',async()=>{
 setup();await openSettings();await openOrdering();
 vi.mocked(api).mockRejectedValueOnce(new Error('Preview request timed out.'));
 fireEvent.click(screen.getByRole('button',{name:'Update estimate'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Preview request timed out.');
 fireEvent.click(screen.getByRole('checkbox'));
 expect(screen.getByRole('button',{name:'Save ordering settings'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Update estimate'})).toBeEnabled();
});

test('products with missing sales links have a clear review action and cannot enable ordering',async()=>{
 const {navigate}=setup({...report,products:[{...report.products[0],eligible:false,status:'relationship_review',daily_sales:null,days_remaining:null}]});
 await screen.findByText('Fast widget');
 expect(screen.getByRole('heading',{name:'We need more sales data to estimate stock'})).toBeVisible();
 fireEvent.click(screen.getByText('Why these numbers?'));
 fireEvent.click(screen.getByRole('button',{name:'Review sales data and links'}));
 expect(navigate).toHaveBeenCalledWith('/mapping#relationships');
 await openOrdering();expect(screen.queryByRole('checkbox')).toBeNull();
 expect(screen.queryByRole('button',{name:'Save ordering settings'})).toBeNull();
});

test('changing the stock date clears a prior acknowledgement',async()=>{
 setup();await openSettings();await openOrdering();
 fireEvent.click(screen.getByRole('checkbox'));
 fireEvent.change(screen.getByLabelText('Stock count date'),{target:{value:'2026-01-09'}});
 expect(screen.getByRole('checkbox')).not.toBeChecked();
 expect(screen.getByRole('button',{name:'Save ordering settings'})).toBeDisabled();
});

test('Excel purchase quantities are shown separately from a test top-up',async()=>{
 const value={...report,policy:{enabled:true,revision:1,reviewed_at:'2026-01-10'},products:[{...report.products[0],source_reorder_point:'10'}]};
 vi.mocked(api).mockResolvedValue(value);
 render(<DemandPlanner root="/workspaces/test" state={state} busy="" perform={vi.fn()} navigate={vi.fn()} stats={{stock:[{product_id:'A',stock_quantity:'8',reorder_point:'10',target_stock:'30',suggested_quantity:'22',low_stock:true,replenishment_configured:true,threshold_source:'source',source:{sheet:'Stock',row:2}}]}}/>);
 await screen.findByText('Fast widget');
 expect(screen.getByText('Top-up to review: 22 units')).toBeVisible();
 expect(screen.getByText(/From your Excel target of 30 units/)).toBeVisible();
 expect(screen.getByRole('note',{name:'Where order amounts come from'})).toHaveTextContent('You don’t need to save an extra ordering rule');
 fireEvent.click(screen.getByText('Why these numbers?'));expect(screen.getByText(/Test top-up: 20 units/)).toBeVisible();
 await openOrdering();expect(screen.queryByRole('button',{name:'Save ordering settings'})).toBeNull();
 expect(api).toHaveBeenCalledTimes(1);
});

test('resetting an experiment restores saved settings with a read request only',async()=>{
 setup();await openSettings();
 fireEvent.change(screen.getByRole('spinbutton',{name:'Supplier delivery days'}),{target:{value:'14'}});
 fireEvent.click(screen.getByRole('button',{name:'Reset to saved settings'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Saved settings restored');
 expect(screen.getByRole('spinbutton',{name:'Supplier delivery days'})).toHaveValue(2);
 expect(vi.mocked(api).mock.calls.every(call=>!call[1])).toBe(true);
});

test('invalid delivery values cannot trigger an estimate request',async()=>{
 setup();await openSettings();
 fireEvent.change(screen.getByRole('spinbutton',{name:'Supplier delivery days'}),{target:{value:'0'}});
 expect(screen.getByRole('button',{name:'Update estimate'})).toBeDisabled();
 expect(api).toHaveBeenCalledTimes(1);
});

test('small positive selling rates remain visible instead of rounding to zero',async()=>{
 setup({...report,products:[{...report.products[0],daily_sales:'0.0001'}]});
 await screen.findByText('Fast widget');
 expect(within(screen.getByRole('article',{name:'Fast widget stock estimate'})).getByText('0.0001')).toBeVisible();
});
