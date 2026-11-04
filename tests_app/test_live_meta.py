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


def test_real_meta_answers_a_scoped_sales_question_without_a_purchase_action(tmp_path):
    from tests_app.helpers import load_company
    store = Store(tmp_path/"sales-question")
    workspace, _ = load_company(store)
    run = run_agents(store, workspace,
        "What is the reviewed sales revenue for product ID A001 alone, across all dates? Show the source rows.",
        "meta", MetaProvider())
    assert run["status"] == "completed" and not store.list(workspace,"action")
    matching = [s["result"] for s in run["steps"] if s["tool"]=="sales_analysis" and s["result"]["scope"]=={"product_id":"A001"}]
    assert matching and matching[0]["revenue"] == [{"currency":"USD","amount":"270.00"}]
    assert all(r["product_id"]=="A001" and r["source"]["cells"]["revenue"] for r in matching[0]["rows"])
    assert "USD 270.00" in run["summary"]


def test_real_meta_business_review_completes_required_checks_without_purchase_actions(tmp_path):
    from tests_app.helpers import load_company, confirm_relationships
    store=Store(tmp_path/"business-review")
    workspace,_=load_company(store)
    confirm_relationships(store,workspace)
    run=run_agents(store,workspace,"Prepare a complete business review, including sales totals, a 7-day comparison, stock risks and supplier readiness. Do not draft any purchase order.","meta",MetaProvider(),"daily_review")
    assert run["status"]=="completed" and run["origin"]=="meta"
    assert {s["tool"] for s in run["steps"]}=={"sales_analysis","sales_comparison","inventory_analysis","procurement_review"}
    assert "USD 1258.00" in run["summary"]
    assert run["work"]["completed_checks"]>=4 and run["elapsed_ms"]>0
    assert not run["action_ids"] and not store.list(workspace,"action")
