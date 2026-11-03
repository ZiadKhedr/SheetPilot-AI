import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';

test('a bad upload does not block later files and a failed switch hides the prior business',async({page,request})=>{
  const create = async(name:string)=>(await (await request.post('/api/workspaces',{data:{name}})).json()).id;
  const first=await create('Recovery hardware');
  const second=await create('Recovery textile');
  await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),first);
  await page.goto('/files');
  const mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  await page.getByTestId('file-upload').setInputFiles([
    {name:'Unreadable.xlsx',mimeType,buffer:Buffer.from('invalid zip')},
    {name:'Sales.xlsx',mimeType,buffer:readFileSync(path.resolve('../demo_data/company_a/Sales.xlsx'))}
  ]);
  await expect(page.getByRole('alert')).toContainText('1 of 2 workbooks imported');
  await expect(page.getByRole('heading',{name:'Sales.xlsx'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Review mappings'})).toBeVisible();
  await page.route('**/workspaces/'+second+'/state',route=>route.fulfill({
    status:503,contentType:'application/json',body:JSON.stringify({detail:'Test workspace temporarily unavailable'})
  }));
  await page.getByLabel('Select workspace').selectOption(second);
  await expect(page.getByRole('alert')).toContainText('Test workspace temporarily unavailable');
  await expect(page.getByRole('heading',{name:'Sales.xlsx'})).toHaveCount(0);
  await page.getByLabel('Select workspace').selectOption(first);
  await expect(page.getByRole('heading',{name:'Sales.xlsx'})).toBeVisible();
});
