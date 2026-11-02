import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { api, formatMoney } from './api';
beforeEach(()=>sessionStorage.clear());
afterEach(()=>vi.unstubAllGlobals());
test('API errors are surfaced rather than converted to success',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:409,json:async()=>({detail:'Source version changed'})}));
 await expect(api('/anything','POST',{})).rejects.toThrow('Source version changed');
});
test('only workspace token is sent in browser authorization',async()=>{
 sessionStorage.setItem('sheetpilot-token','workspace-owner');
 const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({status:'ok'})});vi.stubGlobal('fetch',fetch);
 await api('/health');expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer workspace-owner');
});
test('money formatting preserves currency',()=>{
 expect(formatMoney('11890.00','EGP')).toContain('11,890.00');
 expect(formatMoney('1258.00','USD')).toBe('$1,258.00');
});
