import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {VersionUploads} from './WorkbookVersions';
import {api} from './api';
import type {Context} from './types';
vi.mock('./api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
test('only active snapshots accept uploads and new versions navigate to review',async()=>{
 vi.mocked(api).mockResolvedValue({id:'candidate'});
 const navigate=vi.fn();
 const context={state:{workbooks:[{id:'active',name:'Stock.xlsx',version:2,active:true},{id:'old',name:'Prior.xlsx',version:1,active:false,superseded_by:'active'}]},busy:'',root:'/workspaces/test',navigate,perform:async(_m:string,task:()=>Promise<unknown>)=>{await task()}} as unknown as Context;
 render(<VersionUploads {...context}/>);
 expect(screen.queryByLabelText('New snapshot for Prior.xlsx')).toBeNull();
 fireEvent.change(screen.getByLabelText('New snapshot for Stock.xlsx'),{target:{files:[new File(['data'],'New.xlsx')]}});
 await vi.waitFor(()=>expect(navigate).toHaveBeenCalledWith('/versions?workbook=candidate'));
 expect(api).toHaveBeenCalledWith('/workspaces/test/workbooks/active/versions','POST',expect.any(FormData));
 expect(screen.getByText('Historical')).toBeVisible();
});
