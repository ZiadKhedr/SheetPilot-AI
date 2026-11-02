from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from openpyxl import load_workbook
import pytest

from sheetpilot.actions import propose, review_action
from sheetpilot.ingestion import digest
from sheetpilot.store import Problem, Store
from tests_app.helpers import load_company, confirm_relationships


@pytest.mark.parametrize("company", ["company_a", "company_b"])
def test_approval_generates_real_output_and_preserves_all_originals(tmp_path, company):
    store = Store(tmp_path / "data")
    workspace, oracle = load_company(store, company)
    originals = {p.name:digest(p) for p in (store.root/"originals").glob("*.xlsx")}
    with pytest.raises(Problem, match="reviewed"):
        propose(store,workspace)
    confirm_relationships(store, workspace)
    action = propose(store, workspace)
    assert action["status"] == "pending"
    assert action["totals"] == [{"currency":oracle["currency"],"amount":oracle["expected"]["replenishment_total"]}]
    assert sum(Decimal(l["quantity"]) for l in action["lines"]) == oracle["expected"]["replenishment_quantity"]
    assert not list((store.root/"outputs").glob("*.xlsx"))
    executed = review_action(store, workspace, action["id"], "approve", "human-test")
    assert executed["status"] == "executed"
    assert review_action(store,workspace,action["id"],"approve","human-test")["output"] == executed["output"]
    assert len(list((store.root/"outputs").glob("*.xlsx"))) == 1
    wb=load_workbook(store.root/"outputs"/f"{action['id']}.xlsx",data_only=False)
    assert wb.sheetnames == ["Purchase Orders","Source Trace","Execution"]
    assert wb["Purchase Orders"].max_row == 4
    assert all(c.data_type != "f" for row in wb["Purchase Orders"] for c in row)
    wb.close()
    assert originals == {p.name:digest(p) for p in (store.root/"originals").glob("*.xlsx")}


def test_rejection_produces_no_workbook(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    confirm_relationships(store,workspace)
    action=propose(store,workspace)
    rejected=review_action(store,workspace,action["id"],"reject","human")
    assert rejected["status"] == "rejected"
    assert not list((store.root/"outputs").glob("*.xlsx"))
    with pytest.raises(Problem):
        review_action(store,workspace,action["id"],"approve","human")


def test_source_conflict_is_audited_and_blocks_output(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    confirm_relationships(store,workspace)
    action=propose(store,workspace)
    source=store.root/"originals"/f"{action['source_versions'][0]['workbook_id']}.xlsx"
    source.write_bytes(source.read_bytes()+b"changed")
    with pytest.raises(Problem,match="changed"):
        review_action(store,workspace,action["id"],"approve","human")
    assert store.get(workspace,"action",action["id"])["status"] == "conflicted"
    assert any(e["kind"]=="action.conflicted" for e in store.events(workspace))
    assert not list((store.root/"outputs").glob("*.xlsx"))


def test_repeated_concurrent_approval_is_idempotent(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    confirm_relationships(store,workspace)
    action=propose(store,workspace)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:review_action(store,workspace,action["id"],"approve","human"),range(2)))
    assert all(r["status"]=="executed" for r in results)
    assert len(list((store.root/"outputs").glob("*.xlsx"))) == 1


def test_output_escapes_formula_injection(tmp_path):
    from sheetpilot.actions import safe_cell
    assert safe_cell("=HYPERLINK(\"https://example.test\")").startswith("'")
    assert safe_cell("  +malicious").startswith("'")
