from io import BytesIO
from openpyxl import Workbook
import pytest
from fastapi.testclient import TestClient
from sheetpilot.actions import fingerprint
from sheetpilot.analytics import dashboard, records
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.ingestion import digest, ingest
from sheetpilot.mapping import review_mapping
from sheetpilot.models import MappingInput
from sheetpilot.repairs import (CellRepair, RepairPreview, RepairApproval, RepairReversal,
    preview_repairs, approve_repairs, preview_reversal, reverse_correction, repair_workspace)
from sheetpilot.store import Store, Problem


def setup_sales(store):
    workspace=store.create_workspace('Fictional repair data')['id']
    book=Workbook();sheet=book.active;sheet.title='Sales'
    sheet.append(['Order ID','SKU','Quantity','Unit price','Date','Currency'])
    for row in [('O1','A','1,200',2,'04/11/2026','USD'),('O2','A',3,2,'2026-11-04','USD'),('O3','A',4,2,'bad','USD')]:sheet.append(row)
    stream=BytesIO();book.save(stream);book.close()
    workbook=ingest(store,workspace,'Ambiguous.xlsx',stream.getvalue())
    table=store.list(workspace,'table')[0]
    review_mapping(store,workspace,table['id'],MappingInput(entity='sales',fields={'1':'order_id','2':'product_id','3':'quantity','4':'unit_price','5':'sale_date','6':'currency'},header_row=1,expected_revision=0))
    return workspace,workbook,table


def request(store,workspace,table,row=2,column=3,mode='thousands_comma'):
    state=repair_workspace(store,workspace)
    return RepairPreview(expected_revision=state['revision'],expected_fingerprint=state['fingerprint'],
                         repairs=[CellRepair(table_id=table['id'],row=row,column=column,interpretation=mode)])


def approve(store,workspace,body):
    preview=preview_repairs(store,workspace,body)
    return approve_repairs(store,workspace,RepairApproval(**body.model_dump(),preview_hash=preview['preview_hash'],approved=True),'owner')


def test_numeric_preview_approval_reversal_and_original_preservation(tmp_path):
    store=Store(tmp_path);workspace,book,table=setup_sales(store)
    original_records=records(store,workspace);original_events=store.events(workspace)
    body=request(store,workspace,table)
    preview=preview_repairs(store,workspace,body)
    assert preview['before']['revenue']==[{'currency':'USD','amount':'14.00'}]
    assert preview['after']['revenue']==[{'currency':'USD','amount':'2414.00'}]
    assert preview['affected_count']==1
    assert records(store,workspace)==original_records and store.events(workspace)==original_events
    assert store.list(workspace,'correction')==[]
    saved=approve(store,workspace,body);correction=saved['corrections'][0]
    assert correction['before']=='1,200' and correction['after']=='1200'
    assert correction['approved_by']=='owner' and correction['source_hash']==book['sha256']
    assert dashboard(store,workspace)['revenue']==preview['after']['revenue']
    derived=next(r for r in records(store,workspace) if r['source']['row']==2)
    assert derived['source']['corrections'][0]['revision']==1
    assert digest(store.root/'originals'/f"{book['id']}.xlsx")==book['sha256']
    with pytest.raises(Problem,match='revision'):approve(store,workspace,body)
    reversal=RepairReversal(expected_revision=1,expected_fingerprint=fingerprint(store,workspace))
    reversal_preview=preview_reversal(store,workspace,correction['id'],reversal)
    assert reversal_preview['after']['revenue']==preview['before']['revenue']
    reversal.approved=True;reversal.preview_hash=reversal_preview['preview_hash']
    undone=reverse_correction(store,workspace,correction['id'],reversal,'owner')
    assert undone['revision']==2 and undone['reverses']==correction['id']
    assert dashboard(store,workspace)['revenue']==preview['before']['revenue']
    assert len(store.list(workspace,'correction'))==2
    assert digest(store.root/'originals'/f"{book['id']}.xlsx")==book['sha256']


def test_explicit_date_interpretation_and_approval_boundaries(tmp_path):
    store=Store(tmp_path);workspace,book,table=setup_sales(store)
    body=request(store,workspace,table,row=2,column=5,mode='date_dmy')
    preview=preview_repairs(store,workspace,body)
    assert preview['proposals'][0]['after']=='2026-11-04'
    with pytest.raises(Problem,match='approval'):
        approve_repairs(store,workspace,RepairApproval(**body.model_dump(),preview_hash=preview['preview_hash']),'owner')
    with pytest.raises(Problem,match='preview changed'):
        approve_repairs(store,workspace,RepairApproval(**body.model_dump(),preview_hash='a'*64,approved=True),'owner')
    approve(store,workspace,body)
    assert store.list(workspace,'correction')[0]['after']=='2026-11-04'
    wrong=request(store,workspace,table,row=3,column=2,mode='decimal_dot')
    with pytest.raises(Problem,match='numeric meaning'):preview_repairs(store,workspace,wrong)
    assert len(store.list(workspace,'correction'))==1


def test_identifier_reconciliation_needs_unique_reference_and_invalidates_links(tmp_path):
    from sheetpilot.actions import propose
    from sheetpilot.agents import run_agents
    from sheetpilot.agent_work import report_text
    from .test_versions import setup, suppliers
    from .helpers import confirm_relationships
    from sheetpilot.mapping import source_rows
    store=Store(tmp_path);workspace,book,table=setup(store);suppliers(store,workspace)
    supplier=next(t for t in store.list(workspace,'table') if t['entity']=='suppliers')
    pending=propose(store,workspace,['P1'])
    run=run_agents(store,workspace,'Stock checks','guided',None,'stock_review')
    report=report_text(store,workspace,run)
    body=RepairPreview(expected_revision=0,expected_fingerprint=fingerprint(store,workspace),repairs=[CellRepair(
        table_id=table['id'],row=2,column=1,interpretation='identifier_exact',replacement='P2',reference_table_id=supplier['id'])])
    result=preview_repairs(store,workspace,body)
    assert result['relationships_need_review']
    approve(store,workspace,body)
    assert store.get(workspace,'action',pending['id'])['status']=='conflicted'
    assert store.get(workspace,'run',run['id'])['stale']
    assert report_text(store,workspace,store.get(workspace,'run',run['id']))==report
    assert source_rows(store,workspace,table)[0]['values']['1']['value']=='P2'
    assert any(r['status']=='stale' for r in store.list(workspace,'relationship'))
    assert any(q['code']=='conflict' for q in dashboard(store,workspace)['quality_issues'])
    # Identifier reconciliation never pretends duplicate inventory becomes usable.
    assert len(dashboard(store,workspace)['stock'])==1


def test_repaired_workspace_backup_preserves_derived_layer_and_audit(tmp_path):
    from pathlib import Path
    from sheetpilot.backups import create_backup, restore_backup
    store=Store(tmp_path/'live');workspace,book,table=setup_sales(store)
    approve(store,workspace,request(store,workspace,table))
    restored=Store(Path(restore_backup(store,create_backup(store))['data_dir']))
    assert restored.list(workspace,'correction')==store.list(workspace,'correction')
    assert restored.events(workspace)==store.events(workspace)
    assert dashboard(restored,workspace)['revenue']==[{'currency':'USD','amount':'2414.00'}]


def test_repair_api_scope_and_original_hash_conflict(tmp_path):
    app=create_app(Settings(tmp_path,'owner','reader'));store=app.state.store
    workspace,book,table=setup_sales(store);client=TestClient(app)
    route=f'/api/workspaces/{workspace}/quality/repairs'
    body=request(store,workspace,table)
    assert client.post(route+'/preview',json=body.model_dump(),headers={'Authorization':'Bearer reader'}).status_code==403
    assert client.get(route,headers={'Authorization':'Bearer reader'}).status_code==200
    (store.root/'originals'/f"{book['id']}.xlsx").write_bytes(b'changed')
    assert client.post(route+'/preview',json=body.model_dump(),headers={'Authorization':'Bearer owner'}).status_code==409
    assert not store.list(workspace,'correction')
