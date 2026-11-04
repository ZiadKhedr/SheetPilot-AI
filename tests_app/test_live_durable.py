"""Opt-in actual official Meta check; fictional inputs only, never a fixture provider."""
import os
import pytest
from fastapi.testclient import TestClient
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.provider import MetaProvider
from .helpers import load_company, confirm_relationships
from .test_durable_jobs import body, wait_run


@pytest.mark.skipif(os.getenv('SHEETPILOT_LIVE_META')!='1',reason='Opt-in real Meta durable job check')
def test_live_official_meta_durable_stock_job(tmp_path):
    if not MetaProvider().status()['configured']:pytest.skip('Official Meta key not configured')
    app=create_app(Settings(tmp_path));workspace,oracle=load_company(app.state.store);confirm_relationships(app.state.store,workspace)
    with TestClient(app) as client:
        response=client.post(f'/api/workspaces/{workspace}/agents',json=body('stock_review','meta').model_dump())
        assert response.status_code==202
        run=wait_run(app.state.store,workspace,response.json(),timeout=100)
        assert run['status']=='completed',run['summary']
        assert run['origin']=='meta' and run['steps'] and {s['tool'] for s in run['steps']}=={'inventory_analysis'}
        assert run['steps'][0]['result']['total_products']==oracle['expected']['product_count']
        assert not run['action_ids'] and not app.state.store.list(workspace,'action')
