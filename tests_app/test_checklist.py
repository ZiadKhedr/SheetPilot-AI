from fastapi.testclient import TestClient
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.checklist import next_steps
from sheetpilot.models import MappingInput
from sheetpilot.mapping import review_mapping, discover_relationships
from sheetpilot.agents import run_agents
from .helpers import load_company, confirm_relationships


def statuses(value): return {i['id']:i for i in value['items']}


def test_empty_checklist_is_backend_state_and_read_only(tmp_path):
    app=create_app(Settings(tmp_path))
    store=app.state.store
    workspace=store.create_workspace('Empty')['id']
    before=store.events(workspace)
    state=TestClient(app).get(f'/api/workspaces/{workspace}/state').json()
    steps=statuses(state['next_steps'])
    assert steps['upload']['status']=='ready'
    assert all(steps[k]['status']=='blocked' for k in ['mappings','relationships','quality','analysis','proposals'])
    assert before==store.events(workspace)


def test_review_links_analysis_fingerprint_and_pending_approval(tmp_path):
    from sheetpilot.store import Store
    from sheetpilot.actions import propose
    store=Store(tmp_path)
    workspace,_=load_company(store)
    for table in store.list(workspace,'table'):
        if table['status']!='confirmed':
            review_mapping(store,workspace,table['id'],MappingInput(entity='unknown',fields={},header_row=table['header_row'],expected_revision=table['revision'],ignore=True))
    discover_relationships(store,workspace)
    initial=statuses(next_steps(store,workspace))
    assert initial['mappings']['status']=='done'
    assert initial['relationships']['status']=='ready'
    assert initial['relationships']['targets'][0]['href'].startswith('/mapping#relationship-')
    confirm_relationships(store,workspace)
    run=run_agents(store,workspace,'Review business','guided',None,'daily_review')
    current=statuses(next_steps(store,workspace))
    assert current['analysis']['status']=='done'
    assert current['analysis']['targets'][0]['href']=='/agents#run-'+run['id']
    action=propose(store,workspace)
    assert statuses(next_steps(store,workspace))['proposals']['targets'][0]['href']=='/approvals#action-'+action['id']
    table=next(t for t in store.list(workspace,'table') if t['status']=='confirmed')
    review_mapping(store,workspace,table['id'],MappingInput(entity=table['entity'],fields=table['fields'],header_row=table['header_row'],expected_revision=table['revision']))
    changed=statuses(next_steps(store,workspace))
    assert changed['analysis']['status']=='ready'
    assert changed['relationships']['status']=='ready'
    assert changed['proposals']['status']=='ready'
