import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

test('sales velocity predicts depletion and only a confirmed policy drives purchase drafts',async({page,request})=>{
 const python=process.env.SHEETPILOT_PYTHON||path.resolve(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python');
 const buffer=execFileSync(python,['-c',"import sys; sys.path.insert(0,'.'); from tests_app.test_demand import demand_bytes; sys.stdout.buffer.write(demand_bytes())"],{cwd:path.resolve('..')});
 const ws=await request.post('/api/workspaces',{data:{name:'Synthetic demand planning '+Date.now()}});
 const workspace=(await ws.json()).id,base='/api/workspaces/'+workspace;
 expect((await request.post(base+'/uploads',{multipart:{file:{name:'Demand-Benchmark.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer}}})).ok()).toBeTruthy();
 const state=await (await request.get(base+'/state')).json();
 const oracle:Record<string,{entity:string;fields:Record<string,string>}>= {
  Sales:{entity:'sales',fields:{1:'product_id',2:'quantity',3:'sale_date',4:'unit_price',5:'currency',6:'unit_of_measure'}},
  Inventory:{entity:'inventory',fields:{1:'product_id',2:'product_name',3:'stock_quantity',4:'supplier_id',5:'currency',6:'unit_of_measure'}},
  Quotes:{entity:'suppliers',fields:{1:'product_id',2:'supplier_id',3:'supplier_name',4:'unit_cost',5:'currency'}},
 };
 for(const table of state.tables){
  const config=oracle[table.sheet];
  expect((await request.put(base+'/tables/'+table.id,{data:{...config,header_row:1,expected_revision:table.revision,confirm:true}})).ok()).toBeTruthy();
 }
 for(const link of await (await request.post(base+'/relationships/discover')).json())
  expect((await request.put(base+'/relationships/'+link.id,{data:{decision:'approve'}})).ok()).toBeTruthy();
 await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),workspace);await page.goto('/analytics');
 const planner=page.getByRole('region',{name:'Sales-based stock planning'});
 await expect(planner.getByText('Fast widget',{exact:true})).toBeVisible();
 await expect(planner.getByRole('button',{name:'Confirm sales-based planning policy',exact:true})).toBeDisabled();
 await planner.getByRole('spinbutton',{name:'Delivery lead time (days)',exact:true}).fill('2');
 await planner.getByRole('spinbutton',{name:'Safety buffer (days)',exact:true}).fill('1');
 await planner.getByRole('spinbutton',{name:'Extra coverage after delivery (days)',exact:true}).fill('4');
 await planner.getByRole('button',{name:'Preview calculations',exact:true}).click();
 const row=planner.getByRole('row').filter({hasText:'Fast widget'});
 await expect(row).toContainText('Reorder at 12 · target 28');
 await expect(row).toContainText('2026-01-12');
 let report=await (await request.get(base+'/demand')).json();expect(report.policy.enabled).toBe(false);
 expect((await (await request.get(base+'/state')).json()).actions).toEqual([]);
 await planner.getByRole('checkbox').check();
 await planner.getByRole('button',{name:'Confirm sales-based planning policy',exact:true}).click();
 await expect(planner.getByText('Reviewed policy enabled',{exact:true})).toBeVisible();
 report=await (await request.get(base+'/demand')).json();expect(report.policy.enabled).toBe(true);
 const stats=await (await request.get(base+'/dashboard')).json();
 expect(stats.stock.find((p:any)=>p.product_id==='A').suggested_quantity).toBe('20');
 expect(stats.stock.find((p:any)=>p.product_id==='A').threshold_source).toBe('sales_policy');
 const draft=await request.post(base+'/actions/draft',{data:{product_ids:['A']}});expect(draft.ok()).toBeTruthy();
 const action=await draft.json();expect(action.status).toBe('pending');expect(action.output).toBeNull();
 expect(action.totals).toEqual([{currency:'GBP',amount:'60.00'}]);
 expect(action.lines[0].planning.policy_revision).toBe(1);
 await planner.scrollIntoViewIfNeeded();await page.screenshot({path:'../work/demand-planning-browser.png',fullPage:true});
});
