import {afterEach,expect,test,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {AgentWorkspace} from './AgentWorkspace';
import {api} from './api';
import type {Context,Run} from './types';
vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();vi.useRealTimers()});
const run={id:'saved',job_id:'job',request_id:'a'.repeat(32),task:'stock_review',created:'2026-11-04',title:'Stock risk priorities',status:'running',origin:'guided-tools',message:'Stock',summary:'',steps:[],action_ids:[],input_fingerprint:'current'} as Run;
function context(runs:Run[]){return {state:{runs,actions:[],tables:[],relationships:[],workbooks:[],next_steps:{fingerprint:'current',items:[]}},root:'/workspaces/test',busy:'',provider:{configured:false},navigate:vi.fn(),perform:async(_m:string,task:()=>Promise<unknown>)=>{await task()}} as unknown as Context}
test('reload reconnects to a persisted job without posting another generation',async()=>{
 vi.useFakeTimers();
 vi.mocked(api).mockImplementation(path=>Promise.resolve(path.endsWith('/readiness')?{ready:false,blockers:[]}:run) as ReturnType<typeof api>);
 render(<AgentWorkspace {...context([run])}/>);
 expect(screen.getByRole('region',{name:'Live job activity'})).toBeVisible();
 await act(async()=>{await vi.advanceTimersByTimeAsync(1200)});
 expect(vi.mocked(api).mock.calls.some(call=>call[1]==='POST')).toBe(false);
 expect(api).toHaveBeenCalledWith('/workspaces/test/agents/progress/'+'a'.repeat(32));
 vi.mocked(api).mockRejectedValueOnce(new Error('Offline'));
 await act(async()=>{await vi.advanceTimersByTimeAsync(1200)});
 expect(screen.getByRole('alert')).toHaveTextContent('The server job keeps its saved progress');
 expect(screen.getByRole('button',{name:'Cancel job'})).toBeEnabled();
});
test('explicit retry is separate from reconnect and blocked after context drift',async()=>{
 vi.mocked(api).mockResolvedValue({ready:false,blockers:[]});
 const view=render(<AgentWorkspace {...context([{...run,status:'interrupted',summary:'Server stopped.'}])}/>);
 expect(screen.getByRole('button',{name:'Retry job explicitly'})).toBeEnabled();
 view.rerender(<AgentWorkspace {...context([{...run,status:'interrupted',summary:'Server stopped.',input_fingerprint:'old'}])}/>);
 expect(screen.getByRole('button',{name:'Retry job explicitly'})).toBeDisabled();
 expect(screen.getByText('Source or reviews changed. Use a new job above after reviewing the current data.')).toBeVisible();
});
