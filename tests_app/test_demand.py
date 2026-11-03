from io import BytesIO
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from sheetpilot.actions import propose, review_action
from sheetpilot.analytics import inventory_tool, materialize, records
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.demand import demand_analysis, policy_for, save_policy
from sheetpilot.ingestion import columns_for, ingest
from sheetpilot.mapping import discover_relationships, review_mapping, suggest_labels
from sheetpilot.models import DemandParameters, DemandPolicyInput, MappingInput
from sheetpilot.store import Problem, Store
from sheetpilot.semantics import infer_labels


PARAMS=dict(window_days=30,lead_time_days=2,safety_days=1,review_period_days=4,as_of="2026-01-10")


def demand_bytes(source_thresholds=False,stock="8",unit_mismatch=False,undated=False,zero_only=False):
    wb=Workbook();sales=wb.active;sales.title="Sales"
    sales.append(["product_id","quantity","sale_date","unit_price","currency","unit_of_measure"])
    for product,quantities in (("A",[10,20,10]),("B",[1,1,3])):
        for day,quantity in zip((1,6,10),quantities):
            sales.append([product,0 if zero_only else quantity,f"2026-01-{day:02}",10,"GBP","case" if unit_mismatch else "each"])
    if undated:sales.append(["A",4,None,10,"GBP","each"])
    inv=wb.create_sheet("Inventory")
    inv.append(["product_id","product_name","stock_quantity","supplier_id","currency","unit_of_measure"]+(["reorder_point","target_stock"] if source_thresholds else []))
    for product,name,count in (("A","Fast widget",stock),("B","Slow cable",10),("C","Unobserved item",20)):
        inv.append([product,name,count,"V1","GBP","each"]+([2,6] if source_thresholds else []))
    quotes=wb.create_sheet("Quotes");quotes.append(["product_id","supplier_id","supplier_name","unit_cost","currency"])
    for product in ("A","B","C"):quotes.append([product,"V1","Quote Co",3,"GBP"])
    out=BytesIO();wb.save(out);wb.close();return out.getvalue()


def prepared(tmp_path,**kwargs):
    store=Store(tmp_path/"data");workspace=store.create_workspace("Demand benchmark")["id"]
    original=demand_bytes(**kwargs);workbook=ingest(store,workspace,"Demand-Benchmark.xlsx",original)
    suggest_labels(store,workspace)
    for table in store.list(workspace,"table"):
        # The fixture's reviewed oracle uses row 1, even if mixed numeric text makes structure provisional.
        fields,entity,_=infer_labels(columns_for(workbook["report"],table["sheet"],table["ref"],1))
        review_mapping(store,workspace,table["id"],MappingInput(entity=entity,fields=fields,header_row=1,expected_revision=table["revision"]))
    for link in discover_relationships(store,workspace):
        link["status"]="confirmed";store.put(workspace,"relationship",link)
    materialize(store,workspace)
    return store,workspace,workbook,original


def enable(store,workspace,**changes):
    previous=policy_for(store,workspace)
    return save_policy(store,workspace,DemandPolicyInput(**(PARAMS|changes),expected_revision=previous["revision"] if previous else 0,
        stock_snapshot_confirmed=True),"test-human")


def test_calendar_velocity_depletion_and_order_are_derived_not_source_facts(tmp_path):
    store,workspace,workbook,original=prepared(tmp_path)
    result=demand_analysis(store,workspace,DemandParameters(**PARAMS))
    a,b,c=result["products"]
    assert a["product_id"]=="A" and a["sales_units"]=="40" and a["observed_days"]==10
    assert Decimal(a["daily_sales"])==4 and Decimal(a["days_remaining"])==2
    assert a["estimated_stockout_date"]=="2026-01-12"
    assert a["reorder_point"]=="12" and a["target_stock"]=="28" and a["suggested_quantity"]=="20"
    assert a["eligible"] and a["needs_reorder"]
    assert Decimal(b["daily_sales"])==Decimal("0.5") and Decimal(b["days_remaining"])==20
    assert b["suggested_quantity"]=="0" and b["eligible"]
    assert c["status"]=="no_sales_history" and c["daily_sales"] is None
    assert any("Historical scenario" in w for w in result["warnings"])
    assert policy_for(store,workspace) is None
    assert not any(r["replenishment_configured"] for r in inventory_tool(store,workspace))
    assert (store.root/"originals"/(workbook["id"]+".xlsx")).read_bytes()==original


def test_approved_policy_supplies_only_missing_thresholds_and_preserves_audit(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    enable(store,workspace)
    stock=inventory_tool(store,workspace)
    a=next(r for r in stock if r["product_id"]=="A")
    assert a["threshold_source"]=="sales_policy" and a["reorder_point"]=="12" and a["suggested_quantity"]=="20"
    assert a["planning"]["policy_revision"]==1
    assert next(r for r in records(store,workspace) if r["entity"]=="inventory")["data"]["reorder_point"] is None
    action=propose(store,workspace,["A"])
    assert action["totals"]==[{"currency":"GBP","amount":"60.00"}]
    assert action["lines"][0]["planning"]["observed_days"]==10
    assert len(action["lines"][0]["sources"])==5
    assert list((store.root/"outputs").iterdir())==[]
    output=review_action(store,workspace,action["id"],"approve","test-human")
    wb=load_workbook(store.root/"outputs"/(action["id"]+".xlsx"))
    assert wb["Purchase Orders"]["F2"].value==20
    assert output["status"]=="executed";wb.close()


def test_policy_change_invalidates_pending_purchase_proposal(tmp_path):
    store,workspace,_,_=prepared(tmp_path);enable(store,workspace)
    action=propose(store,workspace,["A"])
    enable(store,workspace,safety_days=4)
    with pytest.raises(Problem,match="changed"):
        review_action(store,workspace,action["id"],"approve","test-human")
    assert store.get(workspace,"action",action["id"])["status"]=="conflicted"
    assert not list((store.root/"outputs").iterdir())


def test_source_thresholds_take_precedence_and_fractional_stock_rounds_safely(tmp_path):
    store,workspace,_,_=prepared(tmp_path,source_thresholds=True);enable(store,workspace)
    a=next(r for r in inventory_tool(store,workspace) if r["product_id"]=="A")
    assert a["threshold_source"]=="source" and a["reorder_point"]=="2" and not a["low_stock"]
    other,other_ws,_,_=prepared(tmp_path/"fractional",stock="8.5");enable(other,other_ws)
    a=next(r for r in inventory_tool(other,other_ws) if r["product_id"]=="A")
    assert a["suggested_quantity"]=="20"


@pytest.mark.parametrize("variant,status",[(dict(unit_mismatch=True),"unit_mismatch"),(dict(undated=True),"limited_history"),(dict(zero_only=True),"no_recent_sales")])
def test_unsafe_or_uninformative_histories_never_drive_policy(tmp_path,variant,status):
    store,workspace,_,_=prepared(tmp_path,**variant);enable(store,workspace)
    a=demand_analysis(store,workspace)["products"][0]
    assert a["status"]==status and not a["eligible"]
    assert not inventory_tool(store,workspace)[0]["replenishment_configured"]


def test_short_window_and_stale_links_are_explicitly_provisional(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    short=demand_analysis(store,workspace,DemandParameters(**(PARAMS|{"as_of":"2026-01-06"})))
    assert short["products"][0]["status"]=="limited_history"
    relation=next(r for r in store.list(workspace,"relationship") if r["field"]=="product_id" and
                  {store.get(workspace,"table",r[k])["entity"] for k in ("left_table","right_table")}=={"sales","inventory"})
    relation["revisions"][0]-=1;store.put(workspace,"relationship",relation)
    assert demand_analysis(store,workspace)["products"][0]["status"]=="relationship_review"


def test_explicit_snapshot_confirmation_policy_concurrency_and_read_only_api(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    app=create_app(Settings(store.root,"owner","reader"));owner=TestClient(app,headers={"Authorization":"Bearer owner"})
    viewer=TestClient(app,headers={"Authorization":"Bearer reader"});base=f"/api/workspaces/{workspace}"
    assert viewer.get(base+"/demand").status_code==200
    body=PARAMS|{"expected_revision":0,"enabled":True,"stock_snapshot_confirmed":False}
    assert owner.put(base+"/demand/policy",json=body).status_code==422
    assert policy_for(store,workspace) is None
    assert viewer.put(base+"/demand/policy",json=body|{"stock_snapshot_confirmed":True}).status_code==403
    assert owner.post(base+"/demand/preview",json=PARAMS).status_code==200
    assert policy_for(store,workspace) is None
    assert owner.put(base+"/demand/policy",json=body|{"stock_snapshot_confirmed":True}).status_code==200
    assert owner.put(base+"/demand/policy",json=body|{"stock_snapshot_confirmed":True}).status_code==409
    assert owner.put(base+"/demand/policy",json=body|{"expected_revision":1,"enabled":False}).status_code==200
    assert not any(r["replenishment_configured"] for r in inventory_tool(store,workspace))
    assert viewer.get("/api/workspaces/not-this-workspace/demand").status_code==404


@pytest.mark.parametrize("value",["2099-01-01","2026-99-99","bad","0001-01-01"])
def test_invalid_or_future_scenario_dates_are_rejected(tmp_path,value):
    store,workspace,_,_=prepared(tmp_path)
    with pytest.raises(Problem): demand_analysis(store,workspace,DemandParameters(as_of=value))


def test_zero_stock_and_no_recent_sales_do_not_produce_infinity(tmp_path):
    store,workspace,_,_=prepared(tmp_path,stock="0")
    a=demand_analysis(store,workspace,DemandParameters(**PARAMS))["products"][0]
    assert a["status"]=="out_of_stock" and Decimal(a["days_remaining"])==0
    assert a["estimated_stockout_date"]=="2026-01-10"
    quiet=demand_analysis(store,workspace,DemandParameters(**(PARAMS|{"as_of":"2026-03-01"})))
    assert quiet["products"][0]["status"]=="no_recent_sales"
    assert quiet["products"][0]["estimated_stockout_date"] is None


def test_duplicate_source_views_do_not_double_count_velocity(tmp_path):
    store,workspace,_,_=prepared(tmp_path)
    source=next(t for t in store.list(workspace,"table") if t["entity"]=="sales")
    store.put(workspace,"table",source|{"id":"second-sales-view"})
    existing=next(r for r in store.list(workspace,"relationship") if
                  {store.get(workspace,"table",r[k])["entity"] for k in ("left_table","right_table")}=={"sales","inventory"})
    replacement=dict(existing,id="second-sales-link")
    for key in ("left_table","right_table"):
        if replacement[key]==source["id"]:replacement[key]="second-sales-view"
    store.put(workspace,"relationship",replacement);materialize(store,workspace)
    a=demand_analysis(store,workspace,DemandParameters(**PARAMS))["products"][0]
    assert Decimal(a["daily_sales"])==4 and a["sales_units"]=="40"
    assert any("duplicate source-cell" in w for w in a["warnings"])
