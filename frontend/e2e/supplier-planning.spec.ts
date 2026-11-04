import {expect,test} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
test('review supplier terms and incoming records before a deterministic purchase draft',async({page,request})=>{
 const python=process.env.SHEETPILOT_PYTHON||path.resolve('../.venv/Scripts/python.exe');
 const bytes=(sheet:string,headers:string,rows:string)=>execFileSync(python,['-c',`from openpyxl import Workbook; from io import BytesIO; import sys; b=Workbook();s=b.active;s.title='${sheet}';s.append(${headers});[s.append(r) for r in ${rows}];o=BytesIO();b.save(o);sys.stdout.buffer.write(o.getvalue())`]);
 const workspace=(await (await request.post('/api/workspaces',{data:{name:'Fictional supplier browser'}})).json()).id;const base='/api/workspaces/'+workspace;
 for(const [name,sheet,headers,rows,entity,fields] of [
  ['Stock.xlsx','Stock',"['SKU','On hand','Reorder','Target','Currency','Unit']","[['P1',2,10,30,'USD','units']]",'inventory',{'1':'product_id','2':'stock_quantity','3':'reorder_point','4':'target_stock','5':'currency','6':'unit_of_measure'}],
  ['Quotes.xlsx','Quotes',"['SKU','Supplier ID','Supplier','Cost','Currency','Unit']","[['P1','SUP','Fictional supplier','0.333333','USD','units']]",'suppliers',{'1':'product_id','2':'supplier_id','3':'supplier_name','4':'unit_cost','5':'currency','6':'unit_of_measure'}]
 ] as const){const book=await (await request.post(base+'/uploads',{multipart:{file:{name,mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:bytes(sheet,headers,rows)}}})).json();const table=(await (await request.get(base+'/state')).json()).tables.find((t:any)=>t.workbook_id===book.id);expect((await request.put(base+'/tables/'+table.id,{data:{entity,fields,header_row:1,expected_revision:0}})).ok()).toBe(true)}
 for(const link of await (await request.post(base+'/relationships/discover')).json())expect((await request.put(base+'/relationships/'+link.id,{data:{decision:'approve'}})).ok()).toBe(true);
 await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),workspace);await page.goto('/purchasing');
 await page.getByLabel('Supplier planning date').fill('2026-11-04');await page.getByLabel('Receipt horizon days').fill('7');await page.getByRole('button',{name:'Add product rule'}).click();
 const state=await (await request.get(base+'/state')).json();const inv=state.tables.find((t:any)=>t.entity==='inventory'),quote=state.tables.find((t:any)=>t.entity==='suppliers');
 await page.getByLabel('Inventory product 0',{exact:true}).selectOption(inv.id+'|P1');await page.getByLabel('Supplier quote 0',{exact:true}).selectOption(quote.id+'|2');
 for(const [key,value] of Object.entries({lead_time_days:'5',pack_size:'6',min_order_quantity:'15',unit_of_measure:'units'}))await page.getByLabel(key+' 0',{exact:true}).fill(value);
 await page.getByRole('button',{name:'Preview supplier planning'}).click();await expect(page.getByLabel('Supplier planning preview')).toContainText('P1: 30 units');
 await page.getByLabel('I reviewed the stock date, base units, per-base-unit prices, supplier terms and incoming-order eligibility.').check();await page.getByRole('button',{name:'Save reviewed supplier policy'}).click();
 await page.getByLabel('Incoming product',{exact:true}).selectOption(inv.id+'|P1');await page.getByLabel('Incoming supplier',{exact:true}).selectOption('SUP');
 for(const [key,value] of Object.entries({order_reference:'CONFIRMED-001',ordered_quantity:'10',received_quantity:'6',ordered_date:'2026-11-03',expected_date:'2026-11-06'}))await page.getByLabel(key,{exact:true}).fill(value);
 await page.getByLabel('Incoming order status').selectOption('partially_received');await page.getByLabel('I reviewed this actual order, its remaining quantity, units, dates and status against the stock snapshot.').check();await page.getByRole('button',{name:'Record incoming order',exact:true}).click();
 await expect(page.getByText(/CONFIRMED-001 · P1/)).toBeVisible();
 const action=await (await request.post(base+'/actions/draft',{data:{product_ids:[]}})).json();expect(action.lines[0].quantity).toBe('24');expect(action.lines[0].line_total).toBe('8.00');
 expect((await request.put(base+'/actions/'+action.id+'/review',{data:{decision:'approve'}})).ok()).toBe(true);
 const current=await (await request.get(base+'/commercial')).json();expect(current.incoming).toHaveLength(1);expect(current.stock[0].stock_quantity).toBe('2');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
