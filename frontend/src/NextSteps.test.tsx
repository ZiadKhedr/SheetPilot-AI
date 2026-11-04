import { afterEach, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NextSteps } from './NextSteps';
afterEach(cleanup);
test('renders backend explanations and links without inferring completion',()=>{
 render(<MemoryRouter><NextSteps steps={{fingerprint:'current',items:[{id:'mappings',title:'Review mappings',status:'ready',explanation:'One table needs human review.',targets:[{label:'Stock range',href:'/mapping#table-stock'}]},{id:'analysis',title:'Run analysis',status:'blocked',explanation:'Confirm a mapping first.',targets:[{label:'Choose job',href:'/agents'}]}]}}/></MemoryRouter>);
 expect(screen.getByText('One table needs human review.')).toBeVisible();
 expect(screen.getByRole('link',{name:'Stock range'})).toHaveAttribute('href','/mapping#table-stock');
 expect(screen.getByText('Waiting')).toBeVisible();
 expect(screen.queryByText('Reviewed / complete')).toBeNull();
});
