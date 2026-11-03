"""Independent multi-sheet retail fixture; no provider or mapping is stubbed in product code."""
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest

from sheetpilot.analytics import dashboard, materialize, records
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.ingestion import ingest
from sheetpilot.mapping import discover_relationships, meta_mapping, review_mapping, suggest_labels
from sheetpilot.models import MappingInput, SemanticPlan
from sheetpilot.profiling import table_profile, arithmetic_evidence
from sheetpilot.provider import MetaError
from sheetpilot.semantics import infer_labels
from sheetpilot.store import Problem, Store


def retail_bytes():
    wb=Workbook();wb.remove(wb.active)
    for sheet,rows in {
        "Sales":[["order_id","product_id","quantity","list_unit_price_gbp","sale_unit_price_gbp","unit_discount_gbp","line_total_gbp"],
                 ["T01","SKU-01",2,12,10,2,20],["T01","SKU-02",1,8,7,1,7],["T02","SKU-01",3,12,9,3,27]],
        "Orders":[["order_id","order_date","customer_id","order_total_gbp"],["T01","2026-01-01","C01",27],["T02","2026-01-02","C02",27]],
        "Products":[["product_id","product_name","unit_cost_gbp","opening_stock","units_sold","stock_remaining"],
                    ["SKU-01","Widget",4,20,5,15],["SKU-02","Cable",3,10,1,9]],
        "Customers":[["customer_id","country"],["C01","United Kingdom"],["C02","Ireland"]],
    }.items():
        ws=wb.create_sheet(sheet)
        for row in rows: ws.append(row)
    data=BytesIO();wb.save(data);wb.close();return data.getvalue()


def retail_store(tmp_path):
    store=Store(tmp_path/"data");workspace=store.create_workspace("Retail benchmark")["id"]
    original=retail_bytes();workbook=ingest(store,workspace,"Retail.xlsx",original)
    return store,workspace,workbook,original


def confirm_suggestions(store,workspace):
    for table in store.list(workspace,"table"):
        review_mapping(store,workspace,table["id"],MappingInput(entity=table["entity"],fields=table["fields"],
            header_row=table["header_row"],expected_revision=table["revision"],constants=table.get("constants",{})))
    materialize(store,workspace)


def test_retail_meanings_and_same_workbook_relationships(tmp_path):
    store,workspace,workbook,original=retail_store(tmp_path)
    suggest_labels(store,workspace)
    tables={t["sheet"]:t for t in store.list(workspace,"table")}
    assert {s:t["entity"] for s,t in tables.items()}=={"Sales":"sales","Orders":"orders","Products":"inventory","Customers":"customers"}
    assert tables["Sales"]["fields"]=={"1":"order_id","2":"product_id","3":"quantity","4":"list_unit_price","5":"unit_price","6":"unit_discount","7":"revenue"}
    assert tables["Orders"]["fields"]["4"]=="order_total"
    assert tables["Products"]["fields"]["4"]=="opening_stock"
    assert tables["Products"]["fields"]["5"]=="units_sold"
    assert tables["Products"]["constants"]=={"currency":"GBP"}
    preview=discover_relationships(store,workspace)
    assert {r["field"] for r in preview}=={"product_id","order_id","customer_id"}
    assert all(r["status"]=="proposed" and r["blockers"] for r in preview)
    assert records(store,workspace)==[]
    confirm_suggestions(store,workspace)
    result=dashboard(store,workspace)
    assert result["revenue"]==[{"currency":"GBP","amount":"54.00"}] # Header totals excluded.
    assert result["inventory_units"]=="24" and result["low_stock_count"]==0
    assert len(records(store,workspace))==9
    assert all(not r["replenishment_configured"] for r in result["stock"])
    assert result["sales_trend"]==[] # Unreviewed links cannot enrich dates.
    app=create_app(Settings(store.root));client=TestClient(app);base=f"/api/workspaces/{workspace}"
    for r in client.post(base+"/relationships/discover").json():
        assert client.put(base+"/relationships/"+r["id"],json={"decision":"approve"}).status_code==200
    result=client.get(base+"/dashboard").json()
    assert result["sales_trend"]==[{"date":"2026-01-01","currency":"GBP","revenue":"27.00"},{"date":"2026-01-02","currency":"GBP","revenue":"27.00"}]
    assert {p["name"] for p in result["top_products"]}=={"SKU-01","SKU-02"} # Inventory is not a catalog join.
    sale=next(r for r in records(store,workspace) if r["entity"]=="sales")
    assert sale["data"]["customer_id"]=="C01"
    assert sale["source"]["joins"][0]["fields"]==["sale_date","customer_id"]
    assert (store.root/"originals"/(workbook["id"]+".xlsx")).read_bytes()==original
    assert list((store.root/"outputs").iterdir())==[]


@pytest.mark.parametrize("labels,expected",[
    (["كود الصنف","الْمَخْزُون الحالي","حد إعادة الطلب"],["product_id","stock_quantity","reorder_point"]),
    (["StockCode","InvoiceNo","CustomerID"],["product_id","order_id","customer_id"]),
    (["sale_unit_price_gbp","list_unit_price_gbp","order_total_gbp","line_total_gbp"],["unit_price","list_unit_price","order_total","revenue"]),
    (["supplier_id","supplier_name","lead time","MOQ"],["supplier_id","supplier_name","lead_time_days","min_order_quantity"]),
])
def test_multilingual_and_specific_meanings(labels,expected):
    mapping,_,_=infer_labels([{"index":i+1,"label":v} for i,v in enumerate(labels)])
    assert list(mapping.values())==expected


def test_profiles_keep_aligned_rows_and_verify_price_choice(tmp_path):
    store,workspace,_,_=retail_store(tmp_path)
    table=next(t for t in store.list(workspace,"table") if t["sheet"]=="Sales")
    profile=table_profile(store,workspace,table)
    assert profile["columns"][0]["profile"]["distinct"]==2
    assert profile["sample_rows"][0]["values"]["7"]=="20"
    checks=arithmetic_evidence(profile)
    assert any("unit_price column 5" in x and "3/3" in x for x in checks)
    assert any("list_unit_price column 4" in x and "0/3" in x for x in checks)


def test_missing_threshold_is_needs_review_not_a_healthy_stock_claim(tmp_path):
    from sheetpilot.actions import procurement_readiness, draft_lines, ProcurementBlocked
    from sheetpilot.agents import run_agents
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    ready=procurement_readiness(store,workspace)
    assert ready["low_stock_count"]==0
    assert {b["code"] for b in ready["blockers"]}=={"reorder_threshold_missing"}
    with pytest.raises(ProcurementBlocked): draft_lines(store,workspace)
    run=run_agents(store,workspace,"Check replenishment","guided",None)
    assert run["status"]=="needs_review" and run["action_ids"]==[]


def test_units_sold_is_contextual_not_always_stock_summary():
    cols=lambda labels:[{"index":i+1,"label":h} for i,h in enumerate(labels)]
    fields,entity,_=infer_labels(cols(["SKU","order_id","Units Sold","unit_price"]))
    assert entity=="sales" and fields["3"]=="quantity"
    fields,entity,_=infer_labels(cols(["SKU","stock_remaining","Units Sold","unit_cost"]))
    assert entity=="inventory" and fields["3"]=="units_sold"


def proposal_for(table,**overrides):
    fields,entity,_=infer_labels(table["columns"])
    return dict(table_id=table["id"],entity=entity,confidence=.9,
        fields=[dict(column_index=int(c),field=f,confidence=.9,evidence="Fixture header evidence") for c,f in fields.items()],
        warnings=[],header_row=table["header_row"],currency="GBP" if table["sheet"]!="Customers" else None,**overrides)


def test_meta_gets_vocabulary_context_arithmetic_and_atomic_retry(tmp_path):
    store,workspace,_,_=retail_store(tmp_path)
    tables=store.list(workspace,"table")
    class Provider:
        model="contract-test";calls=0
        def structured(self,messages,schema):
            self.calls+=1
            context=json.loads(messages[1]["content"])
            assert "customer_id" in context["catalog"]["fields"] and "orders" in context["catalog"]["entities"]
            assert context["relationship_candidates"]
            assert any(t["arithmetic_evidence"] for t in context["requested_tables"])
            # First response omits one table; one bounded repair must supply all four.
            chosen=tables[:-1] if self.calls==1 else tables
            return schema.model_validate({"tables":[proposal_for(t) for t in chosen],"summary":"Retail proposal"})
    provider=Provider();meta_mapping(store,workspace,provider)
    assert provider.calls==2
    assert all(t["origin"]=="meta" and t["status"]=="suggested" for t in store.list(workspace,"table"))
    assert all(t["revision"]==1 for t in store.list(workspace,"table"))
    assert records(store,workspace)==[]


def test_invalid_meta_currency_never_writes_partial_proposals(tmp_path):
    store,workspace,_,_=retail_store(tmp_path)
    class Provider:
        model="invalid-test"
        def structured(self,messages,schema):
            proposals=[proposal_for(t) for t in store.list(workspace,"table")]
            proposals[-1]["currency"]="USD"
            return schema.model_validate({"tables":proposals,"summary":"Invalid currency"})
    with pytest.raises(MetaError,match="currency"):
        meta_mapping(store,workspace,Provider())
    assert all(t["revision"]==0 for t in store.list(workspace,"table"))


def test_reanalysis_requires_explicit_selection_and_preserves_others(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    table=next(t for t in store.list(workspace,"table") if t["sheet"]=="Orders")
    class Provider:
        model="reanalysis-test"
        def structured(self,messages,schema):
            context=json.loads(messages[1]["content"])
            assert len(context["requested_tables"])==1
            assert len(context["workspace_context"])==4
            return schema.model_validate({"tables":[proposal_for(table)],"summary":"Recheck"})
    with pytest.raises(Problem,match="Select specific"):
        meta_mapping(store,workspace,Provider(),include_confirmed=True)
    meta_mapping(store,workspace,Provider(),[table["id"]],True);materialize(store,workspace)
    assert store.get(workspace,"table",table["id"])["status"]=="suggested"
    assert sum(t["status"]=="confirmed" for t in store.list(workspace,"table"))==3
    assert not any(r["entity"]=="orders" for r in records(store,workspace))


def test_unreviewed_links_cannot_be_approved_and_discovery_explains_zero_matches(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace)
    client=TestClient(create_app(Settings(store.root)));base=f"/api/workspaces/{workspace}"
    relations=client.post(base+"/relationships/discover").json()
    assert client.put(base+"/relationships/"+relations[0]["id"],json={"decision":"approve"}).status_code==409
    assert client.put(base+"/relationships/"+relations[0]["id"],json={"decision":"reject"}).status_code==200
    table=next(t for t in store.list(workspace,"table") if t["sheet"]=="Sales")
    assert client.get(base+"/tables/"+table["id"]+"/preview?header_row=9999").status_code==422
    assert client.get(base+"/tables/not-in-workspace/preview").status_code==404
    assert client.get("/api/catalog").json()["entity_catalog"]["customers"]["required"]==["customer_id"]


def test_normalized_only_links_are_preview_and_do_not_collapse_leading_zeroes(tmp_path):
    wb=Workbook();a=wb.active;a.title="Products";a.append(["product_id","product_name"]);a.append([" sku-A ","A"]);a.append(["001","Zeroes"])
    b=wb.create_sheet("Orders");b.append(["product_id","quantity","unit_price"]);b.append(["SKU-a",1,10]);b.append(["1",1,20])
    data=BytesIO();wb.save(data);wb.close()
    store=Store(tmp_path/"data");workspace=store.create_workspace("Formatting")["id"];ingest(store,workspace,"mixed.xlsx",data.getvalue())
    suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    links=discover_relationships(store,workspace)
    assert len(links)==1 and links[0]["match_mode"]=="normalized-preview"
    assert links[0]["overlap_count"]==1
    client=TestClient(create_app(Settings(store.root)))
    assert client.put(f"/api/workspaces/{workspace}/relationships/"+links[0]["id"],json={"decision":"approve"}).status_code==422


def test_changed_mapping_invalidates_join_and_inherited_context(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    order=next(t for t in store.list(workspace,"table") if t["entity"]=="orders")
    link=next(r for r in discover_relationships(store,workspace) if r["field"]=="order_id")
    link["status"]="confirmed";store.put(workspace,"relationship",link);materialize(store,workspace)
    assert len(dashboard(store,workspace)["sales_trend"])==2
    review_mapping(store,workspace,order["id"],MappingInput(entity=order["entity"],fields=order["fields"],header_row=1,
        expected_revision=order["revision"],constants=order["constants"]))
    materialize(store,workspace)
    assert store.get(workspace,"relationship",link["id"])["status"]=="stale"
    assert dashboard(store,workspace)["sales_trend"]==[]
    assert next(r for r in discover_relationships(store,workspace) if r["field"]=="order_id")["status"]=="proposed"


def test_ambiguous_order_master_does_not_multiply_sales_or_inherit_dates(tmp_path):
    original=retail_bytes()
    from openpyxl import load_workbook
    wb=load_workbook(BytesIO(original));wb["Orders"].append(["T01","2026-02-01","C99",27])
    data=BytesIO();wb.save(data);wb.close()
    store=Store(tmp_path/"data");workspace=store.create_workspace("Ambiguous orders")["id"]
    ingest(store,workspace,"ambiguous.xlsx",data.getvalue());suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    link=next(r for r in discover_relationships(store,workspace) if r["field"]=="order_id")
    assert link["cardinality"]=="many-to-many" and link["strength"]=="weak"
    link["status"]="confirmed";store.put(workspace,"relationship",link);materialize(store,workspace)
    stats=dashboard(store,workspace)
    assert stats["sales_records"]==3 and stats["revenue"]==[{"currency":"GBP","amount":"54.00"}]
    assert stats["sales_trend"]==[{"date":"2026-01-02","currency":"GBP","revenue":"27.00"}]
    assert sum(q["code"]=="join_ambiguous" for q in stats["quality_issues"])==2


def test_meta_concurrent_review_is_preserved(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);tables=store.list(workspace,"table")
    first=tables[0]
    class Provider:
        model="race-test"
        def structured(self,messages,schema):
            fields,entity,_=infer_labels(first["columns"])
            review_mapping(store,workspace,first["id"],MappingInput(entity=entity,fields=fields,header_row=1,
                expected_revision=0,constants={"currency":"GBP"}))
            return schema.model_validate({"tables":[proposal_for(t) for t in tables],"summary":"Concurrent proposal"})
    with pytest.raises(Problem,match="changed while Meta"):
        meta_mapping(store,workspace,Provider())
    assert store.get(workspace,"table",first["id"])["status"]=="confirmed"
    assert all(t["revision"]==0 for t in store.list(workspace,"table") if t["id"]!=first["id"])


def test_meta_batches_are_atomic_when_last_batch_is_invalid(tmp_path):
    store,workspace,_,_=retail_store(tmp_path)
    # Extra, disjoint source region makes a second provider batch without changing the first fixture's oracle.
    first=store.list(workspace,"table")[0]
    extra=dict(first,id="extra",sheet="Sales",ref="A1:F4",columns=first["columns"][:6]);store.put(workspace,"table",extra)
    class Provider:
        model="batch-test";calls=0
        def structured(self,messages,schema):
            self.calls+=1
            ids=[t["table_id"] for t in json.loads(messages[1]["content"])["requested_tables"]]
            chosen=[t for t in store.list(workspace,"table") if t["id"] in ids]
            proposals=[proposal_for(t) for t in chosen]
            if len(chosen)==1: proposals[0]["table_id"]="not-provided"
            return schema.model_validate({"tables":proposals,"summary":"Batch test"})
    provider=Provider()
    with pytest.raises(MetaError,match="unknown"):
        meta_mapping(store,workspace,provider)
    assert provider.calls==3 # First batch + second batch + one bounded repair.
    assert all(t["revision"]==0 for t in store.list(workspace,"table"))


def test_currency_requires_explicit_monetary_header_or_human_setting():
    from sheetpilot.semantics import currency_hint
    assert currency_hint([{"label":"country_gbp"}]) is None
    assert currency_hint([{"label":"unit_price_usd"},{"label":"unit_cost_eur"}]) is None
    assert currency_hint([{"label":"unit_price ($)"}]) is None
    assert currency_hint([{"label":"SaleUnitPriceGBP"}])=="GBP"
    assert currency_hint([{"label":"UnitPrice_GBP"}])=="GBP"


def test_discovery_diagnostics_for_nonmatching_keys(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace)
    for table in store.list(workspace,"table"):
        # Mapping distinct columns to product_id produces zero overlapping values.
        if table["sheet"]=="Sales": table["fields"]={"1":"product_id"}
        elif table["sheet"]=="Customers": table["fields"]={"1":"product_id","2":"ignore"}
        else: table["status"]="ignored"
        store.put(workspace,"table",table)
    assert discover_relationships(store,workspace)==[]
    report=store.list(workspace,"relationship_report")[0]
    assert report["compared_identifier_pairs"]==1
    assert any("no shared values" in n for n in report["notes"])


def test_provider_connection_errors_are_not_reprompted(tmp_path):
    store,workspace,_,_=retail_store(tmp_path)
    class Provider:
        model="offline";calls=0
        def structured(self,*args):
            self.calls+=1;raise MetaError("Could not reach the official Meta API.")
    provider=Provider()
    with pytest.raises(MetaError,match="reach"):
        meta_mapping(store,workspace,provider)
    assert provider.calls==1


def test_additional_entity_records_are_retained_without_becoming_sales(tmp_path):
    wb=Workbook();wb.remove(wb.active)
    rows={"Products":[["product_id","product_name","category"],["SKU-1","Lamp","Lighting"]],
          "Suppliers":[["supplier_id","supplier_name","phone"],["V1","Supply Co","0012345"]],
          "Purchases":[["purchase_order_id","product_id","quantity","unit_cost"],["PO1","SKU-1",5,8]],
          "Payments":[["payment_id","order_id","payment_amount"],["PAY1","SO1",40]]}
    for name,data in rows.items():
        ws=wb.create_sheet(name)
        for row in data:ws.append(row)
    data=BytesIO();wb.save(data);wb.close()
    store=Store(tmp_path/"data");workspace=store.create_workspace("Other meanings")["id"]
    ingest(store,workspace,"Masters.xlsx",data.getvalue());suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    assert {r["entity"] for r in records(store,workspace)}=={"products","supplier_directory","purchases","payments"}
    supplier=next(r for r in records(store,workspace) if r["entity"]=="supplier_directory")
    assert supplier["data"]["phone"]=="0012345"
    assert dashboard(store,workspace)["revenue"]==[]


def test_multiple_reviewed_master_tables_remain_ambiguous(tmp_path):
    store,workspace,_,_=retail_store(tmp_path);suggest_labels(store,workspace);confirm_suggestions(store,workspace)
    wb=Workbook();ws=wb.active;ws.title="Other Orders"
    ws.append(["order_id","order_date","customer_id","order_total_gbp"])
    ws.append(["T01","2026-02-01","C99",27]);data=BytesIO();wb.save(data);wb.close()
    ingest(store,workspace,"Second-Orders.xlsx",data.getvalue());suggest_labels(store,workspace)
    table=next(t for t in store.list(workspace,"table") if t["sheet"]=="Other Orders")
    review_mapping(store,workspace,table["id"],MappingInput(entity="orders",fields=table["fields"],header_row=1,
        expected_revision=table["revision"],constants=table["constants"]))
    for r in discover_relationships(store,workspace):
        if r["field"]=="order_id":r["status"]="confirmed";store.put(workspace,"relationship",r)
    materialize(store,workspace)
    result=dashboard(store,workspace)
    assert result["sales_trend"]==[{"date":"2026-01-02","currency":"GBP","revenue":"27.00"}]
    assert sum(q["code"]=="join_ambiguous" for q in result["quality_issues"])==2
