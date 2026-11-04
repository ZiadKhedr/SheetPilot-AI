import { expect, test } from '@playwright/test';
import path from 'node:path';

for(const company of [
 {key:'company_a',name:'Electronics',files:['Sales.xlsx','Inventory.xlsx','Suppliers.xlsx'],revenue:'$1,258.00',total:'$1,809.00'},
 {key:'company_b',name:'Restaurant',files:['Orders.xlsx','Stock.xlsx','Vendors.xlsx'],revenue:'EGP',total:'12,630.00'},
]){
 test('real Meta upload-to-Excel workflow · '+company.name,async({page})=>{
  test.skip(process.env.SHEETPILOT_E2E_META!=='1','Set SHEETPILOT_E2E_META=1 to authorize live Meta API calls.');
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:/Meta ready to verify|Meta connected/}).click();
  await page.getByRole('button',{name:'Verify Meta connection',exact:true}).click();
  await expect(page.getByText('Live generation verified',{exact:true})).toBeVisible({timeout:90000});
  await page.getByRole('button',{name:'Close dialog',exact:true}).click();
  await page.getByRole('button',{name:'New workspace',exact:true}).click();
  await page.getByLabel('Workspace name').fill('Browser '+company.name+' '+Date.now());
  await page.getByRole('button',{name:'Create workspace',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Excel file manager',exact:true})).toBeVisible();
  await page.getByTestId('file-upload').setInputFiles(company.files.map(file=>path.resolve('../demo_data',company.key,file)));
  for(const file of company.files)await expect(page.getByRole('heading',{name:file,exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Review mappings',exact:true}).click();
  await page.getByRole('button',{name:'Analyze with Meta',exact:true}).click();
  await expect(page.getByText('Meta suggestions are ready for your review.',{exact:true})).toBeVisible({timeout:150000});
  for(const entity of ['sales','inventory','suppliers']){
   const card=page.getByTestId('mapping-'+entity);
   if(entity==='sales'){
    await card.getByText('Preview mapped rows',{exact:true}).click();
    await expect(card.getByRole('table',{name:'Preview mapped rows'})).toContainText('Product id');
   }
   await card.getByRole('button',{name:'Confirm mapping',exact:true}).click();
   await expect(card).toHaveAttribute('data-status','confirmed');
  }
  await page.getByRole('button',{name:'Discover relationships',exact:true}).click();
  const confirmations=page.getByRole('button',{name:'Confirm relationship',exact:true});
  await expect(confirmations.first()).toBeVisible();
  const count=await confirmations.count();
  for(let i=0;i<count;i++){await confirmations.first().click();await expect(confirmations).toHaveCount(count-i-1)}
  await page.screenshot({path:test.info().outputPath('browser-'+company.key+'-mapping.png'),fullPage:true});
  await page.getByRole('link',{name:'Overview',exact:true}).click();
  if(company.key==='company_a')await expect(page.getByTestId('metric-sales-revenue')).toHaveText(company.revenue);
  else await expect(page.getByTestId('metric-sales-revenue')).toContainText('11,890.00');
  await expect(page.getByTestId('metric-needs-attention')).toHaveText('3');
  await page.getByRole('button',{name:'Inspect sales rows'}).click();
  const evidence=page.getByRole('dialog',{name:'Reviewed sales rows'});
  await expect(evidence).toContainText(company.files[0]);
  await evidence.getByLabel('Product ID').fill(company.key==='company_a'?'A001':'R01');
  await evidence.getByRole('button',{name:'Filter',exact:true}).click();
  await expect(evidence.getByText(company.key==='company_a'?'A001':'R01',{exact:false}).first()).toBeVisible();
  await evidence.getByRole('button',{name:'Close dialog'}).click();
  await page.screenshot({path:test.info().outputPath('browser-'+company.key+'-dashboard.png'),fullPage:true});
  await page.getByRole('link',{name:'Agent workspace',exact:true}).click();
  await page.getByText('Ask a custom question or run the full guided check',{exact:true}).click();
  await page.getByRole('button',{name:'Ask Meta',exact:true}).click();
  await expect(page.getByRole('region',{name:'Latest guided check'})).toContainText('Meta planned the tool calls.',{timeout:150000});
  await expect(page.locator('.agent-deliverable').getByText('Procurement Agent',{exact:true})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('browser-'+company.key+'-agents.png'),fullPage:true});
  await page.getByRole('link',{name:/^Approval center/}).click();
  await expect(page.locator('.approval-total')).toContainText(company.total);
  await page.getByRole('button',{name:'Review details',exact:true}).click();
  await expect(page.getByRole('dialog').getByText('Affected source versions',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close dialog',exact:true}).click();
  await page.getByRole('button',{name:'Approve & generate Excel',exact:true}).click();
  await expect(page.getByText('Excel output generated. Your original workbooks are unchanged.',{exact:true})).toBeVisible();
  const wait=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download Excel',exact:true}).click();
  const output=await wait;await output.saveAs(test.info().outputPath('browser-'+company.key+'-purchase-orders.xlsx'));
  await page.screenshot({path:test.info().outputPath('browser-'+company.key+'-approval.png'),fullPage:true});
  await page.getByRole('link',{name:'Activity timeline',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Approved purchase orders generated; originals preserved.',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
 });
}
test('mobile navigation and layout',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await expect(page.getByRole('heading',{name:'A clear view of your business.',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.getByRole('button',{name:'Toggle navigation',exact:true}).click();
 await page.getByRole('link',{name:'Excel files',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Excel file manager',exact:true})).toBeVisible();
 await page.screenshot({path:test.info().outputPath('browser-mobile.png'),fullPage:true});
});
