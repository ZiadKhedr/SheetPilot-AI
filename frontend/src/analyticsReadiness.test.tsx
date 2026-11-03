import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AnalyticsReadiness, Metrics } from './DashboardPage';
import type { Dashboard, State } from './types';

afterEach(cleanup);
const stats:Dashboard={revenue:[],sales_records:3,units_sold:'6',inventory_units:'24',inventory_products:2,low_stock_count:0,
 stock:['P1','P2'].map(product_id=>({product_id,stock_quantity:'12',reorder_point:null,target_stock:null,suggested_quantity:'0',low_stock:false,replenishment_configured:false,source:{sheet:'Products',row:2}})),
 low_stock:[],sales_trend:[],top_products:[],quality_issues:[],confirmed_tables:3,pending_actions:0,
 available_entities:['sales','inventory'],warnings:[],currency_review:[{table_id:'sales',sheet:'Sales',affected_rows:3,header_hint:'GBP'}]};
const state={tables:[{id:'inventory',entity:'inventory',status:'confirmed'}]} as State;
test('missing reorder rules are unassessed, not zero healthy products',()=>{
 render(<Metrics stats={stats}/>);
 expect(screen.getByTestId('metric-needs-attention')).toHaveTextContent('Not assessed');
 expect(screen.getByTestId('metric-sales-revenue')).toHaveTextContent('—');
});
test('currency review explains the omission and opens the specific table',()=>{
 const navigate=vi.fn();render(<AnalyticsReadiness stats={stats} state={state} navigate={navigate}/>);
 expect(screen.getByRole('region',{name:'Revenue currency review'})).toHaveTextContent('explicitly name GBP. It has not been applied.');
 fireEvent.click(screen.getByRole('button',{name:'Review Sales currency'}));
 expect(navigate).toHaveBeenCalledWith('/mapping#table-sales');
 expect(screen.getByRole('region',{name:'Reorder rules explanation'})).toHaveTextContent('minimum stock quantity');
});
