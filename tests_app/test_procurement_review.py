import json
import pytest
from fastapi.testclient import TestClient

from sheetpilot.actions import procurement_readiness, propose, ProcurementBlocked
from sheetpilot.agents import run_agents
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.mapping import discover_relationships, review_mapping
from sheetpilot.models import MappingInput
from sheetpilot.store import Store
from tests_app.helpers import load_company, confirm_relationships


def test_exact_restaurant_failure_explains_missing_review_without_writing(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    state_before=store.list(workspace,"relationship")
    result=procurement_readiness(store,workspace)
    assert result["ready"] is False
    assert result["low_stock_count"]==3
    assert {b["code"] for b in result["blockers"]}=={"relationship_review"}
    assert {b["product_id"] for b in result["blockers"]}=={"R01","R02","R04"}
    assert store.list(workspace,"relationship")==state_before==[]
    with pytest.raises(ProcurementBlocked):
        propose(store,workspace)
    assert not store.list(workspace,"action")
    assert not list((store.root/"outputs").glob("*.xlsx"))


def test_guided_run_is_needs_review_and_records_procurement_step(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    run=run_agents(store,workspace,"Check replenishment","guided",None)
    assert run["status"]=="needs_review"
    assert len(run["steps"])==3
    assert run["steps"][-1]["agent"]=="Procurement Agent"
    assert run["steps"][-1]["status"]=="needs_review"
    assert not run["action_ids"]
    assert any(e["kind"]=="agent.needs_review" for e in store.events(workspace))
    assert not any(e["kind"]=="agent.completed" for e in store.events(workspace))


def test_meta_gets_typed_blocker_then_cannot_override_it_in_summary(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    class PlanningProvider:
        calls=0
        def completion(self,messages,**kwargs):
            self.calls+=1
            if self.calls==1:
                return {"role":"assistant","content":None,"tool_calls":[
                    {"id":"draft","type":"function","function":{"name":"draft_purchase_orders","arguments":'{"product_ids":[]}'}}]}
            result=json.loads(messages[-1]["content"])
            assert result["draft_created"] is False
            assert result["status"]=="needs_review"
            return {"role":"assistant","content":"Draft created successfully."}
    run=run_agents(store,workspace,"Draft all low-stock orders","meta",PlanningProvider())
    assert run["status"]=="needs_review"
    assert "No purchase order was drafted" in run["summary"]
    assert "Draft created successfully" not in run["summary"]
    assert not store.list(workspace,"action")


def test_discovery_requires_explicit_confirmation_before_drafting(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    discover_relationships(store,workspace)
    assert not procurement_readiness(store,workspace)["ready"]
    confirm_relationships(store,workspace)
    assert procurement_readiness(store,workspace)["ready"]
    assert propose(store,workspace)["totals"]==[{"currency":"EGP","amount":"12630.00"}]


def test_stale_confirmed_link_is_not_trusted(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    confirm_relationships(store,workspace)
    relation=next(r for r in store.list(workspace,"relationship") if r["field"]=="product_id"
        and {store.get(workspace,"table",r[k])["entity"] for k in ["left_table","right_table"]}=={"inventory","suppliers"})
    relation["revisions"]=[-1,-1]
    store.put(workspace,"relationship",relation)
    assert {b["code"] for b in procurement_readiness(store,workspace)["blockers"]}=={"relationship_review"}


def test_missing_quote_and_currency_are_diagnosed_separately(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store,"company_b")
    confirm_relationships(store,workspace)
    with store.connection() as con:
        con.execute("DELETE FROM records WHERE workspace=? AND entity='suppliers' AND product_id='R01'",(workspace,))
        row=con.execute("SELECT id,data FROM records WHERE workspace=? AND entity='suppliers' AND product_id='R02'",(workspace,)).fetchone()
        data=json.loads(row["data"]);data["currency"]="USD"
        con.execute("UPDATE records SET data=? WHERE id=?",(json.dumps(data),row["id"]))
    result=procurement_readiness(store,workspace)
    assert {(b["product_id"],b["code"]) for b in result["blockers"]}=={("R01","missing_supplier_quote"),("R02","currency_mismatch")}


def test_readiness_api_is_read_only_and_workspace_scoped(tmp_path):
    app=create_app(Settings(tmp_path/"data","owner","reader"))
    workspace,_=load_company(app.state.store,"company_b")
    client=TestClient(app,headers={"Authorization":"Bearer reader"})
    response=client.get(f"/api/workspaces/{workspace}/procurement/readiness")
    assert response.status_code==200
    assert response.json()["blockers"]
    assert "lines" not in response.json()
    assert client.get("/api/workspaces/nonexistent/procurement/readiness").status_code==404
    assert not app.state.store.list(workspace,"relationship")
