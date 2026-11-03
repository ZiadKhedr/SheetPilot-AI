import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

test('four sheets map at their business grain and discover reviewed order/customer/product links',async({page,request})=>{
 const python=process.env.SHEETPILOT_PYTHON||path.resolve(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python');
 const buffer=execFileSync(python,['-c',"import sys; sys.path.insert(0,'.'); from tests_app.test_advanced_mapping import retail_bytes; sys.stdout.buffer.write(retail_bytes())"],{cwd:path.resolve('..')});
 const ws=await request.post('/api/workspaces',{data:{name:'Synthetic multi-sheet retail '+Date.now()}});
 const workspace=(await ws.json()).id,base='/api/workspaces/'+workspace;
 expect((await request.post(base+'/uploads',{multipart:{file:{name:'Retail-Benchmark.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer}}})).ok()).toBeTruthy();
 await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),workspace);
 await page.goto('/mapping');
 await page.getByRole('button',{name:'Label suggestions · no AI',exact:true}).click();
 await expect(page.getByTestId('mapping-customers')).toBeVisible();
 await expect(page.getByTestId('mapping-orders')).toBeVisible();
 await expect(page.getByTestId('mapping-sales').getByRole('combobox',{name:'Meaning of list_unit_price_gbp A1:G4'})).toHaveValue('list_unit_price');
 await expect(page.getByTestId('mapping-sales').getByRole('combobox',{name:'Meaning of sale_unit_price_gbp A1:G4'})).toHaveValue('unit_price');
 await expect(page.getByTestId('mapping-orders').getByRole('combobox',{name:'Meaning of order_total_gbp A1:D3'})).toHaveValue('order_total');
 await expect(page.getByTestId('mapping-inventory').getByText(/Replenishment stays disabled/)).toBeVisible();
 await expect(page.locator('#relationships .relationship')).toHaveCount(3);
 expect(await page.locator('#relationships').getByRole('button',{name:'Confirm relationship',exact:true}).first().isDisabled()).toBe(true);
 for(const entity of ['sales','orders','inventory','customers']){
  const card=page.getByTestId('mapping-'+entity);
  await card.getByRole('button',{name:'Confirm mapping',exact:true}).click();
  await expect(card).toHaveAttribute('data-status','confirmed');
 }
 let stats=await (await request.get(base+'/dashboard')).json();
 expect(stats.revenue).toEqual([{currency:'GBP',amount:'54.00'}]);
 expect(stats.inventory_units).toBe('24');expect(stats.low_stock_count).toBe(0);expect(stats.sales_trend).toEqual([]);
 await page.getByRole('button',{name:'Discover relationships',exact:true}).click();
 const orderLink=page.locator('.relationship').filter({has:page.locator('.relationship-join strong').filter({hasText:'Order id'})});
 await expect(orderLink).toContainText('many-to-one');
 await expect(orderLink).toContainText('Retail-Benchmark.xlsx / Orders');
 await orderLink.getByRole('button',{name:'Confirm relationship',exact:true}).click();
 await expect(orderLink.getByText('confirmed',{exact:true})).toBeVisible();
 stats=await (await request.get(base+'/dashboard')).json();
 expect(stats.sales_trend).toHaveLength(2);expect(stats.revenue).toEqual([{currency:'GBP',amount:'54.00'}]);
 const state=await (await request.get(base+'/state')).json();expect(state.actions).toEqual([]);
 await page.screenshot({path:'../work/retail-mapping-browser.png',fullPage:true});
});
