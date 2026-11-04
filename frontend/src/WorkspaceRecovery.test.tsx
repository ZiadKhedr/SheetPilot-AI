import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { WorkspaceRecovery } from './WorkspaceRecovery';
import { api, downloadBackup } from './api';
import type { Context } from './types';
vi.mock('./api',()=>({api:vi.fn(),downloadBackup:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const context={busy:'',perform:async(_message:string,task:()=>Promise<unknown>)=>{await task()}} as Context;
test('restore requires an archive and shows verified isolated storage counts',async()=>{
 vi.mocked(api).mockResolvedValue({status:'restored',data_dir:'D:\\safe\\restores\\copy',message:'Existing workspaces unchanged.',counts:{workspaces:2,objects:15,files:6}});
 render(<WorkspaceRecovery {...context}/>);
 expect(screen.getByRole('button',{name:'Validate and restore'})).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Backup archive'),{target:{files:[new File(['zip'],'backup.zip')]}});
 fireEvent.click(screen.getByRole('button',{name:'Validate and restore'}));
 expect(await screen.findByRole('status')).toHaveTextContent('2 workspaces · 6 Excel files · 15 saved objects');
 expect(screen.getByLabelText('Restored data folder')).toHaveValue('D:\\safe\\restores\\copy');
 expect(api).toHaveBeenCalledWith('/backups/restore','POST',expect.any(FormData));
});
test('backup uses an authenticated POST download and disables controls while working',async()=>{
 const view=render(<WorkspaceRecovery {...context}/>);
 fireEvent.click(screen.getByRole('button',{name:'Download backup'}));
 expect(downloadBackup).toHaveBeenCalledOnce();
 view.rerender(<WorkspaceRecovery {...context} busy="Validating…"/>);
 expect(screen.getByRole('button',{name:'Download backup'})).toBeDisabled();
 expect(screen.getByLabelText('Backup archive')).toBeDisabled();
});
