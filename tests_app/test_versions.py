from io import BytesIO
from openpyxl import Workbook
import pytest
from fastapi.testclient import TestClient
from sheetpilot.actions import fingerprint, propose, review_action
from sheetpilot.agent_work import report_text
from sheetpilot.agents import run_agents
from sheetpilot.analytics import dashboard
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.ingestion import digest, ingest
from sheetpilot.mapping import review_mapping
from sheetpilot.models import MappingInput
from sheetpilot.store import Store, Problem
from sheetpilot.versions import (TablePair, VersionPreview, VersionReview, VersionActivation,
    activate_version, preview_version, review_version, version_context)
from .helpers import confirm_relationships


def inventory_bytes(rows):
    book=Workbook(); sheet=book.active; sheet.title='Stock'
    sheet.append(['SKU','On hand','Reorder point','Target stock','Currency'])
    for row in rows: sheet.append([*row,3,10,'USD'])
    output=BytesIO(); book.save(output); book.close(); return output.getvalue()


def setup(store):
    workspace=store.create_workspace('Fictional version business')['id']
    parent=ingest(store,workspace,'Stock.xlsx',inventory_bytes([('P1',2),('P2',2),('P4',2)]))
    table=next(t for t in store.list(workspace,'table') if t['workbook_id']==parent['id'])
    review_mapping(store,workspace,table['id'],MappingInput(entity='inventory',fields={'1':'product_id','2':'stock_quantity','3':'reorder_point','4':'target_stock','5':'currency'},header_row=1,expected_revision=0))
    return workspace,parent,store.get(workspace,'table',table['id'])


def updated(store,workspace,parent,rows=None):
    next_=ingest(store,workspace,'Stock-latest.xlsx',inventory_bytes(rows or [('P2',2),('P1',5),('P3',3)]),previous_id=parent['id'])
    table=next(t for t in store.list(workspace,'table') if t['workbook_id']==next_['id'])
    assert table['status']=='suggested' and table['origin']=='version-proposal'
    review_mapping(store,workspace,table['id'],MappingInput(entity='inventory',fields=table['fields'],header_row=1,expected_revision=table['revision']))
    return next_,store.get(workspace,'table',table['id'])


def body(store,workspace,candidate,old,new):
    return VersionReview(expected_fingerprint=version_context(store,workspace,candidate['id'])['fingerprint'],expected_revision=0,
                         pairs=[TablePair(previous_table_id=old['id'],table_id=new['id'],key_fields=['product_id'])],identifiers_confirmed=True)


def suppliers(store,workspace):
    book=Workbook();sheet=book.active;sheet.title='Quotes';sheet.append(['SKU','Supplier ID','Supplier','Unit cost','Currency'])
    for key in ['P1','P2','P3','P4']:sheet.append([key,'SUP','Fictional supplier',2,'USD'])
    stream=BytesIO();book.save(stream);book.close()
    source=ingest(store,workspace,'Quotes.xlsx',stream.getvalue())
    table=next(t for t in store.list(workspace,'table') if t['workbook_id']==source['id'])
    review_mapping(store,workspace,table['id'],MappingInput(entity='suppliers',fields={'1':'product_id','2':'supplier_id','3':'supplier_name','4':'unit_cost','5':'currency'},header_row=1,expected_revision=0))
    confirm_relationships(store,workspace)


def test_version_roundtrip_keys_no_double_count_and_historical_outputs(tmp_path):
    store=Store(tmp_path); workspace,parent,old=setup(store);suppliers(store,workspace)
    executed=review_action(store,workspace,propose(store,workspace,['P1'])['id'],'approve','owner')
    pending=propose(store,workspace,['P2'])
    run=run_agents(store,workspace,'Stock review','guided',None,'stock_review')
    historical_report=report_text(store,workspace,run)
    initial=fingerprint(store,workspace)
    candidate,new=updated(store,workspace,parent)
    assert fingerprint(store,workspace)==initial
    assert dashboard(store,workspace)['inventory_units']=='6'
    review_input=body(store,workspace,candidate,old,new)
    compared=preview_version(store,workspace,candidate['id'],review_input)
    assert compared['changes'][0]['counts']=={'added':1,'removed':1,'changed':1,'unchanged':1}
    assert not compared['blocker_count']
    reviewed=review_version(store,workspace,candidate['id'],review_input,'owner')
    activation=VersionActivation(expected_revision=reviewed['revision'],expected_fingerprint=reviewed['fingerprint'])
    active=activate_version(store,workspace,candidate['id'],activation,'owner')
    assert active['active']
    assert activate_version(store,workspace,candidate['id'],activation,'owner')==active
    assert dashboard(store,workspace)['inventory_units']=='10'
    assert not store.get(workspace,'workbook',parent['id'])['active']
    assert store.get(workspace,'action',pending['id'])['status']=='conflicted'
    assert store.get(workspace,'run',run['id'])['stale']
    assert report_text(store,workspace,store.get(workspace,'run',run['id']))==historical_report
    assert store.get(workspace,'action',executed['id'])==executed
    assert digest(store.root/'outputs'/f"{executed['id']}.xlsx")==executed['output']['sha256']
    assert digest(store.root/'originals'/f"{parent['id']}.xlsx")==parent['sha256']
    assert digest(store.root/'originals'/f"{candidate['id']}.xlsx")==candidate['sha256']
    with pytest.raises(Problem,match='historical'):
        review_mapping(store,workspace,old['id'],MappingInput(entity='inventory',fields=old['fields'],header_row=1,expected_revision=old['revision']))
    assert all(link['status']!='confirmed' for link in store.list(workspace,'relationship') if old['id'] in {link['left_table'],link['right_table']})


@pytest.mark.parametrize('rows',[[('P1',5),('P1',7)],[('',5),('P2',7)]])
def test_ambiguous_and_missing_keys_block_review(tmp_path,rows):
    store=Store(tmp_path);workspace,parent,old=setup(store);candidate,new=updated(store,workspace,parent,rows)
    request=body(store,workspace,candidate,old,new)
    result=preview_version(store,workspace,candidate['id'],request)
    assert result['blocker_count'] and not result['can_review']
    with pytest.raises(Problem,match='Ambiguous'):review_version(store,workspace,candidate['id'],request,'owner')
    assert store.get(workspace,'workbook',parent['id']).get('active',True)


def test_stale_reviews_and_changed_original_refuse_activation(tmp_path):
    store=Store(tmp_path);workspace,parent,old=setup(store);candidate,new=updated(store,workspace,parent)
    reviewed=review_version(store,workspace,candidate['id'],body(store,workspace,candidate,old,new),'owner')
    review_mapping(store,workspace,new['id'],MappingInput(entity='inventory',fields=new['fields'],header_row=1,expected_revision=new['revision']))
    with pytest.raises(Problem,match='changed'):
        activate_version(store,workspace,candidate['id'],VersionActivation(expected_revision=1,expected_fingerprint=reviewed['fingerprint']),'owner')
    request=body(store,workspace,candidate,old,new);request.expected_revision=1
    reviewed=review_version(store,workspace,candidate['id'],request,'owner')
    (store.root/'originals'/f"{candidate['id']}.xlsx").write_bytes(b'changed')
    with pytest.raises(Problem,match='hash'):
        activate_version(store,workspace,candidate['id'],VersionActivation(expected_revision=2,expected_fingerprint=reviewed['fingerprint']),'owner')


def test_version_api_scope_review_boundary_and_approval(tmp_path):
    app=create_app(Settings(tmp_path,'owner','reader'));store=app.state.store
    workspace,parent,old=setup(store);client=TestClient(app);headers={'Authorization':'Bearer owner'}
    endpoint=f'/api/workspaces/{workspace}/workbooks/{parent["id"]}/versions'
    content=inventory_bytes([('P2',2),('P1',4)])
    assert client.post(endpoint,files={'file':('new.xlsx',content)},headers={'Authorization':'Bearer reader'}).status_code==403
    candidate=client.post(endpoint,files={'file':('new.xlsx',content)},headers=headers).json()
    route=f'/api/workspaces/{workspace}/versions/{candidate["id"]}'
    assert client.post(route+'/activate',json={'expected_revision':1,'expected_fingerprint':'a'*64},headers=headers).status_code==409
    assert client.get(f'/api/workspaces/{store.create_workspace("other")["id"]}/versions/{candidate["id"]}',headers=headers).status_code==404
