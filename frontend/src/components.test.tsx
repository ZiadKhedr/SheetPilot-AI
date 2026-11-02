import { afterEach, expect, test } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Button, Modal } from './components';
import { Metrics } from './DashboardPage';
import type { Dashboard } from './types';
afterEach(cleanup);
test('unavailable financial metrics are not invented',()=>{
 const data={revenue:[],sales_records:0,units_sold:null,inventory_units:null,inventory_products:0,available_entities:[],low_stock_count:0} as unknown as Dashboard;
 render(<Metrics stats={data}/>);
 expect(screen.getByTestId('metric-sales-revenue')).toHaveTextContent('—');
 expect(screen.getByTestId('metric-needs-attention')).toHaveTextContent('—');
});
test('verified metrics use source currency and values',()=>{
 const data={revenue:[{currency:'USD',amount:'1258.00'}],sales_records:8,units_sold:'31',inventory_units:'34',inventory_products:4,available_entities:['sales','inventory'],low_stock_count:3} as unknown as Dashboard;
 render(<Metrics stats={data}/>);
 expect(screen.getByTestId('metric-sales-revenue')).toHaveTextContent('$1,258.00');
 expect(screen.getByTestId('metric-inventory-on-hand')).toHaveTextContent('34');
});
test('approval-style buttons prevent clicks while busy',()=>{
 let calls=0;render(<Button disabled onClick={()=>calls++}>Approve</Button>);
 fireEvent.click(screen.getByRole('button',{name:'Approve'}));expect(calls).toBe(0);
});
test('review dialog exposes an accessible title',()=>{
 render(<Modal open onOpenChange={()=>{}} title="Review purchase proposal" description="Inspect before approval."><p>Line items</p></Modal>);
 expect(screen.getByRole('dialog',{name:'Review purchase proposal'})).toBeInTheDocument();
});
