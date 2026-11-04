import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {SupplierPlanning} from './SupplierPlanning';
import {api} from './api';
import type {Context} from './types';
vi.mock('./api',()=>({api:vi.fn()}));afterEach(()=>{cleanup();vi.clearAllMocks()});
test('missing commercial terms are blank and recording incoming stock requires explicit review',async()=>{
 vi.mocked(api).mockResolvedValue({policy:null,fingerprint:'current',stock:[],quotes:[],incoming:[],readiness:{lines:[],blockers:[]}});
 render(<SupplierPlanning {...{root:'/workspaces/test',busy:'',perform:vi.fn()} as unknown as Context}/>);
 expect(await screen.findByText('Enable a reviewed supplier policy first.')).toBeVisible();
 expect(screen.getByLabelText('Supplier planning date')).toHaveValue('');
 expect(screen.getByLabelText('Receipt horizon days')).toHaveValue(null);
 expect(screen.getByRole('button',{name:'Record incoming order'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Preview supplier planning'})).toBeDisabled();
 expect(screen.getByText(/Purchase workbooks never imply incoming stock/)).toBeVisible();
});
