import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { SalesEvidence } from './SalesEvidence';
import { api } from './api';
import type { Dashboard, State } from './types';

vi.mock('./api', async importOriginal => ({...await importOriginal<typeof import('./api')>(), api:vi.fn()}));
afterEach(()=>{cleanup(); vi.clearAllMocks();});
const props = {root:'/workspaces/one', close:vi.fn(),
  state:{workbooks:[{id:'book',name:'Dispatch.xlsx'}]} as State,
  stats:{revenue:[{currency:'GBP',amount:'12.25'}]} as Dashboard};

test('revenue evidence exposes original cells and filters by exact product',async()=>{
  vi.mocked(api).mockResolvedValueOnce({total:1,offset:0,rows:[{
    product_id:'007',product_name:'Textile roll',quantity:'2',revenue:'12.25',currency:'GBP',
    source:{workbook_id:'book',sheet:'Dispatch',row:4,cells:{revenue:'E4'}}}]})
    .mockResolvedValueOnce({total:0,offset:0,rows:[]});
  render(<SalesEvidence {...props}/>);
  expect(await screen.findByText('Dispatch.xlsx')).toBeVisible();
  expect(screen.getByText('Dispatch · row 4 · E4')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Product ID'),{target:{value:'009'}});
  fireEvent.click(screen.getByRole('button',{name:'Filter'}));
  expect(await screen.findByText('No reviewed sales match these filters.')).toBeVisible();
  expect(api).toHaveBeenLastCalledWith('/workspaces/one/sales/evidence?offset=0&limit=12&product_id=009');
});

test('a failed page can be retried without closing the evidence',async()=>{
  vi.mocked(api).mockRejectedValueOnce(new Error('Connection unavailable'))
    .mockResolvedValueOnce({total:0,offset:0,rows:[]});
  render(<SalesEvidence {...props}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Connection unavailable');
  fireEvent.click(screen.getByRole('button',{name:'Retry'}));
  await waitFor(()=>expect(screen.queryByRole('alert')).toBeNull());
  expect(await screen.findByText('No reviewed sales match these filters.')).toBeVisible();
});
