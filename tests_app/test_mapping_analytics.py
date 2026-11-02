from decimal import Decimal
import json

import pytest

from sheetpilot.analytics import dashboard
from sheetpilot.mapping import discover_relationships, review_mapping, meta_mapping
from sheetpilot.models import MappingInput, SemanticPlan
from sheetpilot.provider import MetaError
from sheetpilot.store import Problem, Store
from tests_app.helpers import load_company


@pytest.mark.parametrize("company", ["company_a", "company_b"])
def test_reviewed_normalization_matches_independent_company_oracle(tmp_path, company):
    store = Store(tmp_path / "data")
    workspace, oracle = load_company(store, company)
    result = dashboard(store, workspace)
    expected = oracle["expected"]
    assert result["revenue"] == [{"currency":oracle["currency"], "amount":expected["revenue"]}]
    assert Decimal(result["units_sold"]) == expected["units_sold"]
    assert Decimal(result["inventory_units"]) == expected["inventory_quantity"]
    assert result["low_stock_count"] == expected["low_stock_count"]
    assert result["sales_records"] == expected["valid_sales_rows"]
    assert sum(i["code"] == "duplicate" for i in result["quality_issues"]) == 1
    assert sum(i["code"] == "invalid" for i in result["quality_issues"]) == 1
    links = discover_relationships(store, workspace)
    product_links = [r for r in links if r["field"] == "product_id"]
    assert len(product_links) == 3
    assert all(r["overlap_count"] == 4 and r["coverage"] == 1 for r in product_links)
    assert all(r["status"] == "proposed" for r in links)


def test_bad_mapping_and_stale_revision_rejected(tmp_path):
    store = Store(tmp_path / "data")
    workspace, _ = load_company(store)
    table = next(t for t in store.list(workspace,"table") if t["status"] == "confirmed")
    with pytest.raises(Problem, match="changed"):
        review_mapping(store,workspace,table["id"],MappingInput(
            entity=table["entity"],fields=table["fields"],header_row=table["header_row"],expected_revision=0))
    invalid = dict(table["fields"]) | {"999":"product_id"}
    with pytest.raises(Problem, match="outside"):
        review_mapping(store,workspace,table["id"],MappingInput(
            entity=table["entity"],fields=invalid,header_row=table["header_row"],expected_revision=table["revision"]))


def test_meta_cannot_reference_unprovided_tables(tmp_path):
    store = Store(tmp_path/"data")
    workspace=store.create_workspace("unmapped")["id"]
    from pathlib import Path
    from sheetpilot.ingestion import ingest
    ingest(store,workspace,"sales.xlsx",Path("demo_data/company_a/Sales.xlsx").read_bytes())
    class InvalidProvider:
        model="test"
        def structured(self,*args):
            return SemanticPlan.model_validate({"tables":[{"table_id":"not-a-source","entity":"sales","confidence":.9,"fields":[],"warnings":[]}],"summary":"invalid"})
    with pytest.raises(MetaError,match="unknown"):
        meta_mapping(store,workspace,InvalidProvider())
    assert all(t["status"] == "unreviewed" for t in store.list(workspace,"table"))
