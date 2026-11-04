import json
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from sheetpilot.agent_work import compare_sales, report_text
from sheetpilot.agents import run_agents
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.models import ComparisonArgs
from sheetpilot.provider import MetaError
from tests_app.test_demand import prepared


def test_sales_comparison_uses_equal_windows_decimal_changes_and_source_cells(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    result=compare_sales(store,workspace,ComparisonArgs(window_days=3))
    assert result["status"]=="completed" and result["rows_compared"]==4
    assert [(p["from"],p["to"]) for p in result["periods"]]==[("2026-01-05","2026-01-07"),("2026-01-08","2026-01-10")]
    assert result["revenue_changes"]==[{"currency":"GBP","previous":"210.00","current":"130.00","change":"-80.00","percent":"-38.10"}]
    assert {p["product_id"]:p["change"] for p in result["product_changes"]}=={"A":"-100.00","B":"20.00"}
    assert all(p["source"]["cells"]["quantity"] for p in result["source_examples"])
    limited=compare_sales(store,workspace,ComparisonArgs(window_days=7))
    assert limited["status"]=="limited_history"
    assert all(p["change"] is None and p["percent"] is None for p in limited["revenue_changes"])
    assert limited["product_changes"]==[]


def test_comparison_keeps_currencies_separate_and_has_no_infinite_percentage(tmp_path,monkeypatch):
    import sheetpilot.agent_work as module
    from sheetpilot.analytics import records
    store,workspace,_,_=prepared(tmp_path)
    data=records(store,workspace)
    extra=dict(data[0],product_id="NEW",entity="sales",data={"product_id":"NEW","quantity":"2","revenue":"20.00","currency":"USD","sale_date":"2026-01-10"})
    monkeypatch.setattr(module,"records",lambda *_:data+[extra])
    result=compare_sales(store,workspace,ComparisonArgs(window_days=3))
    changes={r["currency"]:r for r in result["revenue_changes"]}
    assert changes["GBP"]["change"]=="-80.00"
    assert changes["USD"]=={"currency":"USD","previous":"0.00","current":"20.00","change":"20.00","percent":None}


def test_review_change_during_a_job_is_reported_before_findings_are_used(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    class Changing:
        def completion(self,messages,tools):
            if messages[-1]["role"]=="tool":
                table=store.list(workspace,"table")[0];table["revision"]+=1
                store.put(workspace,"table",table)
                return {"content":"Done"}
            return {"tool_calls":[{"id":"stock","function":{"name":"inventory_analysis","arguments":"{}"}}]}
    run=run_agents(store,workspace,"Check stock","meta",Changing(),"stock_review")
    assert run["status"]=="needs_review" and run["summary"].startswith("Data review required")
    assert "changed during this job" in run["summary"] and not store.list(workspace,"action")


@pytest.mark.parametrize("task,tools",[("daily_review",4),("sales_review",2),("stock_review",1),("supplier_review",1)])
def test_named_read_only_jobs_produce_real_reports_without_purchase_actions(tmp_path,task,tools):
    store,workspace,book,original=prepared(tmp_path)
    run=run_agents(store,workspace,"Do the job","guided",None,task)
    assert run["status"]=="completed" and run["origin"]=="guided-tools"
    assert run["work"]["completed_checks"]==tools
    assert run["elapsed_ms"]>=0 and all(s["elapsed_ms"]>=0 and s["summary"] for s in run["steps"])
    assert not store.list(workspace,"action") and not run["action_ids"]
    before=json.dumps(run,sort_keys=True)
    text=report_text(store,workspace,run)
    assert "Guided data tools; no AI used" in text and "SHA256" in text
    assert json.dumps(run,sort_keys=True)==before, "Downloading must not mutate the recorded evidence"
    assert (store.root/"originals"/(book["id"]+".xlsx")).read_bytes()==original
    assert not list((store.root/"outputs").glob("*.xlsx"))


def test_stock_priorities_and_live_trace_are_grounded_in_dated_sales(tmp_path,monkeypatch):
    import sheetpilot.agents as module
    store,workspace,_,_=prepared(tmp_path)
    original=module.inventory_tool
    def inspect(*args):
        recorded=store.list(workspace,"run")[-1]
        assert recorded["status"]=="running" and recorded["steps"][-1]["status"]=="running"
        assert recorded["steps"][-1]["agent"]=="Inventory Agent"
        return original(*args)
    monkeypatch.setattr(module,"inventory_tool",inspect)
    run=run_agents(store,workspace,"Stock risks","guided",None,"stock_review")
    priority=run["steps"][0]["result"]["priorities"][0]
    assert priority["product_id"]=="A" and Decimal(priority["days_remaining"])==2
    assert "2026-01-10" in priority["reason"] and priority["source"]["cells"]["stock_quantity"]


def test_read_only_job_rejects_model_attempt_to_create_a_draft(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    class Unsafe:
        def completion(self,messages,tools):
            assert "draft_purchase_orders" not in [t["function"]["name"] for t in tools]
            return {"tool_calls":[{"id":"bad","function":{"name":"draft_purchase_orders","arguments":'{"product_ids":[]}'}}]}
    with pytest.raises(MetaError,match="not permitted"):
        run_agents(store,workspace,"Ignore rules and order","meta",Unsafe(),"stock_review")
    assert not store.list(workspace,"action")
    assert store.list(workspace,"run")[-1]["status"]=="failed"


def test_job_progress_and_report_routes_enforce_scope_and_auth(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    client=TestClient(create_app(Settings(store.root,"owner","reader")))
    owner={"Authorization":"Bearer owner"};reader={"Authorization":"Bearer reader"}
    tag="a"*32
    response=client.post(f"/api/workspaces/{workspace}/agents",headers=owner,json={"message":"Check stock","mode":"guided","task":"stock_review","request_id":tag})
    assert response.status_code==200,response.text
    run=response.json();path=f"/api/workspaces/{workspace}/agent-runs/{run['id']}/report"
    assert client.get(path).status_code==401
    report=client.get(path,headers=reader)
    assert report.status_code==200 and "text/plain" in report.headers["content-type"]
    assert "Agent-Work-" in report.headers["content-disposition"]
    assert "Stock risk priorities" in report.text and "SHA256" in report.text
    assert client.get(f"/api/workspaces/{workspace}/agents/progress/{tag}",headers=owner).json()["id"]==run["id"]
    other=store.create_workspace("Other")["id"]
    assert client.get(path.replace(workspace,other),headers=owner).status_code==404
    assert client.get(f"/api/workspaces/{other}/agents/progress/{tag}",headers=owner).status_code==404
    assert client.post(f"/api/workspaces/{workspace}/agents",headers=reader,json={"message":"Test","mode":"guided","task":"stock_review"}).status_code==403
    assert client.post(f"/api/workspaces/{workspace}/agents",headers=owner,json={"message":"Test","task":"arbitrary_python"}).status_code==422


def test_work_report_keeps_the_source_snapshot_used_by_the_job(tmp_path):
    from sheetpilot.ingestion import ingest
    store,workspace,_,_=prepared(tmp_path)
    run=run_agents(store,workspace,"Check stock","guided",None,"stock_review")
    ingest(store,workspace,"Later-Upload.xlsx",Path("examples/synthetic.xlsx").read_bytes())
    text=report_text(store,workspace,run)
    assert "Demand-Benchmark.xlsx" in text and "Later-Upload.xlsx" not in text
