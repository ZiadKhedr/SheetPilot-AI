import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('backup download restores a verified separate installation and rejects a bad archive',async({page,request})=>{
 const workspace=await (await request.post('/api/demo/company_a')).json();
 const direct=await request.post('/api/backups/export',{data:{},timeout:10000});
 expect(direct.status()).toBe(200);
 await page.addInitScript(id=>localStorage.setItem('sheetpilot-workspace',id),workspace.id);
 await page.goto('/recovery');
 const event=page.waitForEvent('download',{timeout:20000});
 await page.getByRole('button',{name:'Download backup',exact:true}).click();
 const downloaded=await event;
 const archive=readFileSync((await downloaded.path())!);
 expect(archive.length).toBeGreaterThan(1000);
 await page.getByLabel('Backup archive').setInputFiles({name:'backup.zip',mimeType:'application/zip',buffer:archive});
 await page.getByRole('button',{name:'Validate and restore'}).click();
 await expect(page.getByText('Restore verified',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Restored data folder')).toHaveValue(/restores/);
 const after=await (await request.get('/api/workspaces/'+workspace.id+'/state')).json();
 expect(after.workbooks).toHaveLength(3);
 await page.getByLabel('Backup archive').setInputFiles({name:'invalid.zip',mimeType:'application/zip',buffer:Buffer.from('bad')});
 await page.getByRole('button',{name:'Validate and restore'}).click();
 await expect(page.getByRole('alert')).toContainText('Invalid or unreadable backup');
});
