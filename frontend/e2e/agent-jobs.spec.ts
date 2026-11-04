import {expect,test} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

test('agents deliver a real business brief and downloadable source evidence without ordering',async({page,request})=>{
 const workspace=(await (await request.post('/api/demo/company_a')).json()).id;
 const base='/api/workspaces/'+workspace;
 const oracle=JSON.parse(await fs.readFile(path.resolve('../demo_data/manifest.json'),'utf8')).companies.company_a;
 for(const [entity,config] of Object.entries(oracle.files) as [string,any][]){
  const state=await (await request.get(base+'/state')).json();
  const workbook=state.workbooks.find((w:any)=>w.name===config.filename);
  const table=state.tables.find((t:any)=>t.workbook_id===workbook.id&&t.ref===config.ref);
  expect((await request.put(base+'/tables/'+table.id,{data:{entity,fields:config.columns,header_row:config.header_row,expected_revision:table.revision,confirm:true}})).ok()).toBe(true);
 }
 for(const link of await (await request.post(base+'/relationships/discover')).json()){
  if(link.overlap_count)expect((await request.put(base+'/relationships/'+link.id,{data:{decision:'approve'}})).ok()).toBe(true);
 }
 await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),workspace);
 await page.goto('/agents');
 await page.getByLabel('Job execution mode').selectOption('guided');
 await page.getByRole('article',{name:'Review the business',exact:true}).getByRole('button',{name:'Start job'}).click();
 const report=page.locator('.agent-work-report').first();
 await expect(report.getByLabel('Work completed for you')).toContainText('4 specialist checks');
 await expect(report).toContainText('$1,258.00');
 await expect(report.locator('.agent-deliverable')).toHaveCount(4);
 await expect(report).toContainText('No purchase draft created');
 let state=await (await request.get(base+'/state')).json();
 expect(state.actions).toEqual([]);expect(state.runs[0].origin).toBe('guided-tools');
 const output=page.waitForEvent('download');
 await report.getByRole('button',{name:'Download work report',exact:true}).click();
 const file=await output;expect(file.suggestedFilename()).toMatch(/^Agent-Work-.*\.txt$/);
 const saved=await file.path();expect(saved).toBeTruthy();
 const text=await fs.readFile(saved!,'utf8');
 expect(text).toContain('Guided data tools; no AI used');expect(text).toContain('USD 1258.00');expect(text).toContain('SHA256');
 await report.getByText('Example source cells',{exact:true}).first().click();
 await expect(report).toContainText('Sales.xlsx');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 state=await (await request.get(base+'/state')).json();expect(state.actions).toEqual([]);
 await page.screenshot({path:test.info().outputPath('agent-business-work-report.png'),fullPage:true});
});
