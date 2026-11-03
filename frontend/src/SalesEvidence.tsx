import { useEffect, useState } from 'react';
import { api, formatMoney } from './api';
import { Busy, Button, Modal } from './components';
import type { Context } from './types';

interface Sale {
  product_id: string;
  product_name: string | null;
  quantity: string;
  revenue: string;
  currency: string | null;
  sale_date: string | null;
  source: { workbook_id: string; sheet: string; row: number; cells: Record<string, string> };
}
interface EvidencePage {
  rows: Sale[];
  offset: number;
  total: number;
}
const pageSize = 12;

export function SalesEvidence({root, state, stats, close}: Pick<Context,'root'|'state'|'stats'> & {close:()=>void}) {
  const [query, setQuery] = useState('');
  const [product, setProduct] = useState('');
  const [currency, setCurrency] = useState('');
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<EvidencePage>();
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({offset:String(offset),limit:String(pageSize)});
    if (product) params.set('product_id', product);
    if (currency) params.set('currency', currency);
    setPage(undefined);
    setError('');
    api<EvidencePage>(root+'/sales/evidence?'+params)
      .then(result => { if (active) setPage(result); })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [root, offset, currency, product, attempt]);

  return <Modal open title="Reviewed sales rows" onOpenChange={open => { if (!open) close(); }}
    description="Trace a sale to its original workbook and worksheet. Revenue totals include only rows with a reviewed currency.">
    <form className="sales-filters" onSubmit={e => { e.preventDefault(); setProduct(query.trim()); setOffset(0); }}>
      <label>Product ID<input value={query} onChange={e=>setQuery(e.target.value)} maxLength={180} placeholder="All products"/></label>
      <label>Currency<select value={currency} onChange={e=>{setCurrency(e.target.value);setOffset(0);}}>
        <option value="">All currencies</option>{stats.revenue.map(r=><option key={r.currency}>{r.currency}</option>)}
      </select></label><Button type="submit" variant="secondary">Filter</Button>
    </form>
    {error ? <div role="alert">{error} <Button onClick={()=>setAttempt(n=>n+1)}>Retry</Button></div> :
      !page ? <Busy message="Reading reviewed sales…"/> :
      !page.total ? <p role="status">No reviewed sales match these filters.</p> : <>
        <div className="table-wrap"><table><thead><tr><th>Product</th><th>Units</th><th>Revenue</th><th>Original cells</th></tr></thead>
          <tbody>{page.rows.map(sale=>{
            const {source} = sale;
            const workbook = state.workbooks.find(w=>w.id===source.workbook_id);
            const basis = source.cells.revenue || [source.cells.quantity,source.cells.unit_price].filter(Boolean).join(' × ');
            return <tr key={source.workbook_id+'-'+source.sheet+'-'+source.row+'-'+basis}>
              <td><strong dir="auto">{sale.product_name || sale.product_id}</strong><small>{sale.product_id} · {sale.sale_date || 'Undated'}</small></td>
              <td>{sale.quantity}</td><td>{sale.currency ? formatMoney(sale.revenue,sale.currency) : sale.revenue+' · currency unknown'}</td>
              <td><strong dir="auto">{workbook?.name || source.workbook_id}</strong><small>{source.sheet} · row {source.row} · {basis}</small></td>
            </tr>;})}</tbody></table></div>
        <div className="sales-pager"><span role="status">Rows {offset+1}–{offset+page.rows.length} of {page.total}</span>
          <Button variant="ghost" disabled={!offset} onClick={()=>setOffset(offset-pageSize)}>Previous</Button>
          <Button variant="secondary" disabled={offset+pageSize>=page.total} onClick={()=>setOffset(offset+pageSize)}>Next</Button>
        </div>
      </>}
  </Modal>;
}
