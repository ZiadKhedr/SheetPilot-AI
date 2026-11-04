from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
from openpyxl import Workbook, load_workbook
import pytest
from fastapi.testclient import TestClient

from sheetpilot.actions import fingerprint, propose, procurement_readiness, review_action
from sheetpilot.analytics import inventory_tool
from sheetpilot.api import create_app
from sheetpilot.commercial import (SupplierTerm, CommercialInput, IncomingInput, preview_policy, save_policy, save_incoming)
from sheetpilot.config import Settings
from sheetpilot.ingestion import digest, ingest
from sheetpilot.mapping import review_mapping
from sheetpilot.models import MappingInput
from sheetpilot.store import Store, Problem
from .helpers import confirm_relationships


def workbook(sheet,headers,rows):
    book=Workbook();ws=book.active;ws.title=sheet;ws.append(headers)
    for row in rows:ws.append(row)
    stream=BytesIO();book.save(stream);book.close();return stream.getvalue()


def setup(store,duplicate_quote=False):
    workspace=store.create_workspace('Fictional commercial planning')['id']
    stock=ingest(store,workspace,'Stock.xlsx',workbook('Stock',['SKU','On hand','Reorder','Target','Currency','Unit'],[['P1',2,10,30,'USD','units']]))
    table=next(t for t in store.list(workspace,'table') if t['workbook_id']==stock['id'])
    review_mapping(store,workspace,table['id'],MappingInput(entity='inventory',fields={'1':'product_id','2':'stock_quantity','3':'reorder_point','4':'target_stock','5':'currency','6':'unit_of_measure'},header_row=1,expected_revision=0))
    quotes=[['P1','SUP','Fictional supplier','0.333333','USD','units']]
    if duplicate_quote:quotes.append(['P1','SUP','Fictional supplier',1,'USD','units'])
    source=ingest(store,workspace,'Quotes.xlsx',workbook('Quotes',['SKU','Supplier ID','Supplier','Cost','Currency','Unit'],quotes))
    quote=next(t for t in store.list(workspace,'table') if t['workbook_id']==source['id'])
    review_mapping(store,workspace,quote['id'],MappingInput(entity='suppliers',fields={'1':'product_id','2':'supplier_id','3':'supplier_name','4':'unit_cost','5':'currency','6':'unit_of_measure'},header_row=1,expected_revision=0))
    confirm_relationships(store,workspace)
    return workspace,stock,table,quote


def policy_request(store,workspace,table,quote,**changes):
    body=CommercialInput(expected_revision=0,expected_fingerprint=fingerprint(store,workspace),planning_date='2026-11-04',horizon_days=7,
        terms=[SupplierTerm(inventory_table_id=table['id'],product_id='P1',quote_table_id=quote['id'],quote_row=2,
            lead_time_days=5,pack_size='6',min_order_quantity='15',unit_of_measure='units',currency='USD',price_basis='per_base_unit')])
    for key,value in changes.items():setattr(body,key,value)
    return body


def approve_policy(store,workspace,body):
    preview=preview_policy(store,workspace,body)
    body.approved=True;body.preview_hash=preview['preview_hash']
    return save_policy(store,workspace,body,'owner')


def incoming(store,workspace,table,**changes):
    value=dict(expected_revision=0,expected_fingerprint=fingerprint(store,workspace),request_id=uuid4().hex,order_reference='CONFIRMED-001',
        inventory_table_id=table['id'],product_id='P1',supplier_id='SUP',ordered_quantity='10',received_quantity='6',
        unit_of_measure='units',currency='USD',ordered_date='2026-11-03',expected_date='2026-11-06',status='partially_received',approved=True)
    value.update(changes);return IncomingInput(**value)


def test_pack_moq_incoming_decimal_output_and_generation_not_receipt(tmp_path):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store)
    original=digest(store.root/'originals'/f"{stock['id']}.xlsx")
    request=policy_request(store,workspace,table,quote);events=store.events(workspace)
    preview=preview_policy(store,workspace,request)
    assert preview['readiness']['lines'][0]['quantity']=='30'
    assert not store.list(workspace,'commercial_policy') and events==store.events(workspace)
    approve_policy(store,workspace,request)
    before=propose(store,workspace)
    recorded=save_incoming(store,workspace,incoming(store,workspace,table),'owner')
    assert store.get(workspace,'action',before['id'])['status']=='conflicted'
    lines=procurement_readiness(store,workspace)['lines'];assert len(lines)==1
    line=lines[0];assert line['quantity']=='24' and line['line_total']=='8.00' and line['unit_cost']=='0.333333'
    basis=line['commercial']
    assert basis['eligible_incoming']=='4' and basis['inventory_position']=='6' and basis['net_requirement']=='24'
    assert basis['pack_count']=='4' and basis['minimum_order_quantity']=='15' and basis['lead_time_days']==5
    action=propose(store,workspace);assert propose(store,workspace)['id']==action['id']
    executed=review_action(store,workspace,action['id'],'approve','owner')
    assert store.list(workspace,'incoming_order')==[recorded]
    assert inventory_tool(store,workspace)[0]['stock_quantity']=='2'
    book=load_workbook(store.root/'outputs'/f"{executed['id']}.xlsx")
    meta={r[0].value:r[1].value for r in book['Execution'].iter_rows(min_row=2)}
    assert json.loads(meta['Supplier/incoming basis: P1'])==basis
    assert 'eligible incoming 4' in meta['Quantity calculation: P1']
    book.close()
    assert digest(store.root/'originals'/f"{stock['id']}.xlsx")==original
    assert any(e['kind']=='action.proposed' and e['details']['lines'][0].get('commercial')==basis for e in store.events(workspace))


@pytest.mark.parametrize('changes,eligible',[
    ({'status':'draft','received_quantity':'0'},'0'),
    ({'status':'cancelled'},'0'),
    ({'status':'received','received_quantity':'10'},'0'),
    ({'expected_date':'2026-11-15'},'0'),
    ({'ordered_date':'2026-11-01','expected_date':'2026-11-03'},'0'),
    ({'status':'confirmed','received_quantity':'0','ordered_quantity':'4','expected_date':'2026-11-11'},'4'),
])
def test_incoming_eligibility_is_explicit_and_horizon_bounded(tmp_path,changes,eligible):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store);approve_policy(store,workspace,policy_request(store,workspace,table,quote))
    save_incoming(store,workspace,incoming(store,workspace,table,**changes),'owner')
    basis=inventory_tool(store,workspace)[0]['commercial']
    assert basis['eligible_incoming']==eligible
    if eligible=='0':assert basis['incoming_orders'][0]['exclusion_reasons']


def test_supplier_selection_is_human_reviewed_and_stale_terms_block(tmp_path):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store,True)
    assert procurement_readiness(store,workspace)['blockers'][0]['code']=='ambiguous_supplier_quote'
    approve_policy(store,workspace,policy_request(store,workspace,table,quote))
    line=procurement_readiness(store,workspace)['lines'][0];assert line['unit_cost']=='0.333333'
    current=store.get(workspace,'table',quote['id'])
    review_mapping(store,workspace,quote['id'],MappingInput(entity='suppliers',fields=current['fields'],header_row=1,expected_revision=current['revision']))
    confirm_relationships(store,workspace)
    ready=procurement_readiness(store,workspace)
    assert not ready['lines'] and ready['blockers'][0]['code']=='commercial_terms_review'


def test_incoming_duplicate_requests_units_status_and_revision_guards(tmp_path):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store);approve_policy(store,workspace,policy_request(store,workspace,table,quote))
    request=incoming(store,workspace,table);first=save_incoming(store,workspace,request,'owner')
    assert save_incoming(store,workspace,request,'owner')==first
    with pytest.raises(Problem,match='already exist'):save_incoming(store,workspace,incoming(store,workspace,table),'owner')
    with pytest.raises(Problem,match='units'):save_incoming(store,workspace,incoming(store,workspace,table,order_reference='bad-unit',unit_of_measure='boxes'),'owner')
    with pytest.raises(Problem,match='disagree'):save_incoming(store,workspace,incoming(store,workspace,table,order_reference='bad-status',status='confirmed'),'owner')
    update=incoming(store,workspace,table,expected_revision=1,received_quantity='10',status='received')
    revised=save_incoming(store,workspace,update,'owner',first['id']);assert revised['revision']==2
    assert inventory_tool(store,workspace)[0]['commercial']['eligible_incoming']=='0'
    with pytest.raises(Problem,match='revision'):save_incoming(store,workspace,update.model_copy(update={'request_id':uuid4().hex}),'owner',first['id'])


def test_covering_incoming_removes_purchase_need_and_moq_rounds_up(tmp_path):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store)
    body=policy_request(store,workspace,table,quote);body.terms[0].min_order_quantity='40'
    approve_policy(store,workspace,body)
    assert procurement_readiness(store,workspace)['lines'][0]['quantity']=='42'
    save_incoming(store,workspace,incoming(store,workspace,table,ordered_quantity='8',received_quantity='0',status='confirmed'),'owner')
    readiness=procurement_readiness(store,workspace)
    assert readiness['covered_by_incoming_count']==1 and not readiness['lines']
    assert inventory_tool(store,workspace)[0]['commercial']['final_quantity']=='0'


def test_commercial_api_approval_currency_source_and_reader_boundaries(tmp_path):
    app=create_app(Settings(tmp_path,'owner','reader'));store=app.state.store;workspace,stock,table,quote=setup(store)
    body=policy_request(store,workspace,table,quote);client=TestClient(app);base=f'/api/workspaces/{workspace}/commercial'
    assert client.get(base,headers={'Authorization':'Bearer reader'}).status_code==200
    assert client.post(base+'/preview',json=body.model_dump(),headers={'Authorization':'Bearer reader'}).status_code==403
    assert client.put(base+'/policy',json=body.model_dump(),headers={'Authorization':'Bearer owner'}).status_code==422
    body.terms[0].currency='EUR'
    with pytest.raises(Problem,match='currency'):preview_policy(store,workspace,body)
    body.terms[0].currency='USD';body.terms[0].pack_size='0'
    with pytest.raises(Problem,match='Pack size'):preview_policy(store,workspace,body)


@pytest.mark.parametrize('source_rules',[False,True])
def test_supplier_lead_time_changes_only_reviewed_fallback_thresholds(tmp_path,source_rules):
    from .test_demand import prepared, enable
    store,workspace,_,_=prepared(tmp_path,source_thresholds=source_rules);enable(store,workspace)
    inv=next(t for t in store.list(workspace,'table') if t['entity']=='inventory')
    quote=next(t for t in store.list(workspace,'table') if t['entity']=='suppliers')
    body=CommercialInput(expected_revision=0,expected_fingerprint=fingerprint(store,workspace),planning_date='2026-01-10',horizon_days=7,
        terms=[SupplierTerm(inventory_table_id=inv['id'],product_id='A',quote_table_id=quote['id'],quote_row=2,
            lead_time_days=5,pack_size='1',min_order_quantity='0',unit_of_measure='each',currency='GBP',price_basis='per_base_unit')])
    approve_policy(store,workspace,body)
    row=next(r for r in inventory_tool(store,workspace) if r['product_id']=='A')
    assert row['reorder_point']==('2' if source_rules else '24')
    assert row['target_stock']==('6' if source_rules else '40')
    assert row['suggested_quantity']==('0' if source_rules else '32')


def test_reviewed_source_change_excludes_old_incoming_until_reanchored(tmp_path):
    store=Store(tmp_path);workspace,stock,table,quote=setup(store);approve_policy(store,workspace,policy_request(store,workspace,table,quote))
    save_incoming(store,workspace,incoming(store,workspace,table),'owner')
    current=store.get(workspace,'table',table['id'])
    review_mapping(store,workspace,table['id'],MappingInput(entity='inventory',fields=current['fields'],header_row=1,expected_revision=current['revision']))
    confirm_relationships(store,workspace)
    approve_policy(store,workspace,policy_request(store,workspace,table,quote,expected_revision=1))
    basis=inventory_tool(store,workspace)[0]['commercial']
    assert basis['eligible_incoming']=='0'
    assert 'review' in basis['incoming_orders'][0]['exclusion_reasons'][0]
