"""Opt-in real-network verification. Mock transport tests are separate."""
import os
import pytest
from pathlib import Path

from sheetpilot.provider import MetaProvider
from sheetpilot.store import Store
from sheetpilot.ingestion import ingest
from sheetpilot.mapping import meta_mapping, review_mapping, discover_relationships
from sheetpilot.models import MappingInput
from sheetpilot.analytics import materialize, dashboard
from sheetpilot.agents import run_agents
from sheetpilot.actions import review_action

pytestmark = pytest.mark.skipif(os.getenv("SHEETPILOT_LIVE_META_TEST") != "1", reason="Explicit opt-in required for real Meta calls.")


def test_real_meta_mapping_agents_and_excel_output(tmp_path):
    provider=MetaProvider()
    assert provider.verify()["generation_verified"]
    store=Store(tmp_path/"data")
    workspace=store.create_workspace("Live Meta verification")["id"]
    for path in Path("demo_data/company_a").glob("*.xlsx"):
        ingest(store,workspace,path.name,path.read_bytes())
    meta_mapping(store,workspace,provider)
    business=[t for t in store.list(workspace,"table") if t["entity"] != "unknown"]
    assert len(business)==3, [(t["sheet"],t["entity"]) for t in business]
    for table in business:
        review_mapping(store,workspace,table["id"],MappingInput(entity=table["entity"],fields=table["fields"],
            header_row=table["header_row"],expected_revision=table["revision"]))
    materialize(store,workspace)
    assert dashboard(store,workspace)["revenue"] == [{"currency":"USD","amount":"1258.00"}]
    for relation in discover_relationships(store,workspace):
        if relation["field"]=="product_id" and relation["overlap_count"]==4:
            relation["status"]="confirmed";store.put(workspace,"relationship",relation)
    run=run_agents(store,workspace,"Analyze our sales and inventory. Prepare purchase order drafts for ALL low-stock products. Do not approve anything.","meta",provider)
    assert run["status"]=="completed"
    assert run["action_ids"]
    action=store.get(workspace,"action",run["action_ids"][0])
    assert action["totals"]==[{"currency":"USD","amount":"1809.00"}]
    assert review_action(store,workspace,action["id"],"approve","live-test-human")["status"]=="executed"
