import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MappingEditor, MappingPage } from './MappingPage';
import type { Context, TableInfo, WorkbookInfo } from './types';
import { api } from './api';

vi.mock('./api',async()=>({...await vi.importActual('./api'),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const table:TableInfo={id:'t',workbook_id:'w',sheet:'Products',ref:'A1:C4',header_row:1,
 columns:[{index:1,label:'SKU',coordinate:'A1',samples:['P01']},{index:2,label:'Stock remaining',coordinate:'B1',samples:[4]},
 {index:3,label:'Opening stock',coordinate:'C1',samples:[10]}],
 entity:'inventory',fields:{'1':'product_id','2':'stock_quantity','3':'opening_stock'},constants:{currency:'GBP'},
 confidence:.9,origin:'meta',status:'suggested',revision:1,evidence:[],structure_warnings:[],
 field_details:{'2':{confidence:.7,evidence:'Current balance, distinct from opening balance.',alternatives:['stock_available']}}};
const workbook={id:'w',name:'Retail.xlsx'} as WorkbookInfo;
const fields=['product_id','stock_quantity','opening_stock','reorder_point','currency'];
function setup(){
 vi.mocked(api).mockResolvedValue({columns:table.columns,row_count:3,header_candidates:[],arithmetic_evidence:[]});
 const save=vi.fn().mockResolvedValue(undefined);
 render(<MappingEditor table={table} workbook={workbook} fields={fields} root="/workspaces/test" busy={false} save={save} reanalyze={()=>{}}/>);
 return save;
}
test('inventory without a reorder threshold can be confirmed, with explicit limitation and reviewed currency',async()=>{
 const save=setup();await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm mapping'})).toBeEnabled());
 expect(screen.getByText(/Replenishment stays disabled/)).toBeVisible();
 expect(screen.getByRole('option',{name:'Customers'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Confirm mapping'}));
 expect(save).toHaveBeenCalledWith(expect.objectContaining({entity:'inventory',constants:{currency:'GBP'},confirm:true}));
});
test('duplicate meanings block confirmation; draft remains available',async()=>{
 setup();await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm mapping'})).toBeEnabled());
 fireEvent.change(screen.getByRole('combobox',{name:'Meaning of Opening stock A1:C4'}),{target:{value:'stock_quantity'}});
 expect(screen.getByRole('button',{name:'Confirm mapping'})).toBeDisabled();
 expect(screen.getByText('Each meaning can be used only once.')).toBeVisible();
 expect(screen.getByRole('button',{name:'Save draft'})).toBeEnabled();
});
test('header change reloads source columns and clears old assignments',async()=>{
 setup();await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm mapping'})).toBeEnabled());
 vi.mocked(api).mockResolvedValue({columns:[{index:1,label:'New SKU',coordinate:'A2',samples:['N01']}],row_count:2,header_candidates:[],arithmetic_evidence:[]});
 fireEvent.change(screen.getByRole('spinbutton',{name:'Header row for Products'}),{target:{value:'2'}});
 await waitFor(()=>expect(screen.getByText('New SKU')).toBeVisible());
 expect(screen.getByRole('combobox',{name:'Meaning of New SKU A1:C4'})).toHaveValue('');
 expect(screen.getByRole('button',{name:'Confirm mapping'})).toBeDisabled();
 expect(api).toHaveBeenLastCalledWith('/workspaces/test/tables/t/preview?header_row=2');
});

test('legacy stale links offer an enabled refresh action and explain the actual blocker',async()=>{
 vi.mocked(api).mockResolvedValue([]);
 const left={...table,id:'left',status:'confirmed',revision:3};
 const right={...table,id:'right',status:'confirmed',revision:4,sheet:'Sales',entity:'sales' as const};
 const context={state:{tables:[left,right],workbooks:[workbook],relationships:[{
  id:'r',left_table:'left',right_table:'right',field:'product_id',left_column:'1',right_column:'1',
  status:'stale',revisions:[1,2],coverage:1,overlap_count:2,strength:'strong',matching_examples:['P01'],evidence:'Shared IDs',
  blockers:['Confirm both source mappings with these identifier columns first.'],
 }],relationship_report:{message:'Old cached message',notes:[],compared_identifier_pairs:1}},
 provider:{configured:false},root:'/workspaces/test',fields,busy:'',perform:async(_message:string,task:()=>Promise<unknown>)=>{await task()}} as unknown as Context;
 render(<MappingPage {...context}/>);
 expect(screen.getByText('Source mappings are confirmed. Refresh relationship evidence before confirming these links.')).toBeVisible();
 expect(screen.queryByText('Confirm both source mappings with these identifier columns first.')).not.toBeInTheDocument();
 const refresh=screen.getByRole('button',{name:'Refresh relationship evidence'});
 expect(refresh).toBeEnabled();expect(screen.getByRole('button',{name:'Confirm relationship'})).toBeDisabled();
 fireEvent.click(refresh);
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/workspaces/test/relationships/discover','POST'));
});
