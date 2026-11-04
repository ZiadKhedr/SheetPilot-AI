import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {AgentWorkspace} from './AgentPages';
import {api} from './api';
import type {Context,Run} from './types';

vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const result={id:'fresh-check',status:'completed',summary:'Workbook was already generated after approval. No duplicate was created.',action_ids:['existing-order']} as Run;
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
 expect(screen.getByRole('status')).toHaveTextContent('Checking reviewed sales');
 finish(result);
 expect(await screen.findByRole('region',{name:'Latest guided check'})).toHaveTextContent('No duplicate was created');
 expect(screen.getByRole('status')).toHaveTextContent('Check completed. No AI was used.');
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/agents','POST',{message:'Guided replenishment check',mode:'guided'});
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
 expect(await screen.findByRole('alert')).toHaveTextContent('Guided check failed: Workspace storage is unavailable.');
 expect(screen.getByRole('button',{name:'Run guided check'})).toBeEnabled();
 expect(screen.queryByRole('region',{name:'Latest guided check'})).toBeNull();
});
