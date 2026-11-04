import {afterEach,expect,test,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {AgentWorkspace} from './AgentPages';
import {AgentWorkReport} from './AgentWork';
import {api} from './api';
import type {Context,Run} from './types';

vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();vi.useRealTimers()});
const result={id:'fresh-check',created:'2026-11-04T12:00:00Z',message:'Check stock',origin:'guided-tools',steps:[],status:'completed',summary:'Workbook was already generated after approval. No duplicate was created.',action_ids:['existing-order']} as Run;
function setup(){
 const perform=vi.fn(async(_message:string,task:()=>Promise<unknown>)=>{try{await task()}catch{}});
 const navigate=vi.fn();
 const context={state:{tables:[],relationships:[],runs:[],actions:[]},provider:{configured:true},root:'/workspaces/test',busy:'',perform,navigate} as unknown as Context;
 vi.mocked(api).mockResolvedValue({ready:true,blockers:[],low_stock_count:1,ready_count:1});
 render(<AgentWorkspace {...context}/>);
 return {perform,navigate};
}

test('guided check shows immediate progress and explains an existing approved output on every click',async()=>{
 const {navigate}=setup();
 await waitFor(()=>expect(api).toHaveBeenCalledTimes(1));
 let finish!:(run:Run)=>void;
 vi.mocked(api).mockImplementationOnce(()=>new Promise<Run>(resolve=>{finish=resolve}) as ReturnType<typeof api>);
 fireEvent.click(screen.getByRole('button',{name:'Run guided check'}));
 expect(screen.getByRole('button',{name:'Checking…'})).toBeDisabled();
 expect(screen.getByRole('status')).toHaveTextContent('Starting the reviewed-data checks');
 finish(result);
 expect(await screen.findByRole('region',{name:'Latest guided check'})).toHaveTextContent('No duplicate was created');
 expect(screen.getByRole('status')).toHaveTextContent('Check completed. No AI was used.');
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/agents','POST',expect.objectContaining({message:'Guided replenishment check',mode:'guided',task:'custom'}));
 fireEvent.click(screen.getByRole('button',{name:'Open Approval Center'}));
 expect(navigate).toHaveBeenCalledWith('/approvals');
 vi.mocked(api).mockResolvedValueOnce({...result,id:'another-check'});
 fireEvent.click(screen.getByRole('button',{name:'Run guided check'}));
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('Check completed.'));
 expect(vi.mocked(api).mock.calls.filter(call=>call[1]==='POST')).toHaveLength(2);
});

test('failed guided checks show an error next to the button and allow retry',async()=>{
 setup();await waitFor(()=>expect(api).toHaveBeenCalledTimes(1));
 vi.mocked(api).mockRejectedValueOnce(new Error('Workspace storage is unavailable.'));
 fireEvent.click(screen.getByRole('button',{name:'Run guided check'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Job failed: Workspace storage is unavailable.');
 expect(screen.getByRole('button',{name:'Run guided check'})).toBeEnabled();
 expect(screen.queryByRole('region',{name:'Latest guided check'})).toBeNull();
});

test('named jobs send the selected read-only task and show measured work counts',async()=>{
 setup();await waitFor(()=>expect(api).toHaveBeenCalledTimes(1));
 fireEvent.change(screen.getByLabelText('Job execution mode'),{target:{value:'guided'}});
 vi.mocked(api).mockResolvedValueOnce({...result,title:'Stock risk priorities',task:'stock_review',action_ids:[],elapsed_ms:1530,work:{completed_checks:1,sales_rows_in_largest_check:0,stock_products_checked:6,supplier_lines_ready:0}});
 fireEvent.click(within(screen.getByRole('article',{name:'Prioritize stock risks'})).getByRole('button',{name:'Start job'}));
 await screen.findByLabelText('Work completed for you');
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/agents','POST',expect.objectContaining({task:'stock_review',mode:'guided',request_id:expect.stringMatching(/^[a-f0-9]{32}$/)}));
 expect(screen.getByLabelText('Work completed for you')).toHaveTextContent('6 stock products checked');
 expect(screen.getByLabelText('Work completed for you')).toHaveTextContent('1.5 sec elapsed');
 expect(screen.getByText('No AI was used.',{exact:false})).toBeVisible();
});

test('live job activity uses the backend progress response',async()=>{
 setup();await waitFor(()=>expect(api).toHaveBeenCalledTimes(1));
 vi.useFakeTimers();
 let finish!:(run:Run)=>void;
 vi.mocked(api).mockImplementation((path,method)=>method==='POST'?new Promise<Run>(resolve=>{finish=resolve}) as ReturnType<typeof api>:Promise.resolve({...result,status:'running',steps:[{agent:'Inventory Agent',tool:'inventory_analysis',status:'running',result:{}}]}) as ReturnType<typeof api>);
 fireEvent.click(within(screen.getByRole('article',{name:'Prioritize stock risks'})).getByRole('button',{name:'Start job'}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(1200)});
 expect(screen.getByRole('region',{name:'Live job activity'})).toHaveTextContent('Inventory Agent');
 expect(screen.getByRole('region',{name:'Live job activity'})).toHaveTextContent('Running inventory analysis');
 await act(async()=>{finish({...result,action_ids:[]})});
 expect(screen.queryByRole('region',{name:'Live job activity'})).toBeNull();
});

test('an older inventory check does not claim a missing priority list was empty',()=>{
 const run={...result,action_ids:[],steps:[{agent:'Inventory Agent',tool:'inventory_analysis',status:'completed',result:{total_products:6,low_stock_count:3}}]};
 render(<AgentWorkReport run={run} state={{workbooks:[],actions:[]} as unknown as Context['state']} root="/workspaces/test" busy="" perform={vi.fn()} navigate={vi.fn()} onReview={vi.fn()}/>);
 expect(screen.getByText('Priority rankings were not recorded for this older check.')).toBeVisible();
 expect(screen.queryByText('No stock priorities were identified from the reviewed data.')).toBeNull();
});

test('purchase work products show the current execution status of a historical draft',()=>{
 const run={...result,steps:[{agent:'Procurement Agent',tool:'draft_purchase_orders',status:'completed',result:{action_id:'existing-order',status:'pending',lines:[]}}]};
 render(<AgentWorkReport run={run} state={{workbooks:[],actions:[{id:'existing-order',status:'executed'}]} as unknown as Context['state']} root="/workspaces/test" busy="" perform={vi.fn()} navigate={vi.fn()} onReview={vi.fn()}/>);
 expect(screen.getByText('This output already exists. No duplicate was generated.')).toBeVisible();
 expect(screen.queryByText('A purchase draft is waiting for your approval.')).toBeNull();
});
