import pytest
from sheetpilot.agents import run_agents
from sheetpilot.actions import review_action
from sheetpilot.provider import MetaError
from sheetpilot.store import Store
from tests_app.helpers import load_company, confirm_relationships


def test_guided_mode_is_honest_and_creates_only_pending_action(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    confirm_relationships(store,workspace)
    run=run_agents(store,workspace,"Guided replenishment","guided",None)
    assert run["origin"] == "guided-tools"
    assert [s["agent"] for s in run["steps"]] == ["Sales Agent","Inventory Agent","Procurement Agent"]
    assert store.get(workspace,"action",run["action_ids"][0])["status"] == "pending"
    assert not list((store.root/"outputs").glob("*.xlsx"))


def test_unsafe_model_tool_is_rejected_and_logged(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    class Unsafe:
        def completion(self,*a,**k):
            return {"tool_calls":[{"id":"call","function":{"name":"execute_python","arguments":"{}"}}]}
    with pytest.raises(MetaError,match="not permitted"):
        run_agents(store,workspace,"do something","meta",Unsafe())
    assert store.list(workspace,"run")[0]["status"] == "failed"
    assert not store.list(workspace,"action")


def test_repeated_guided_check_explains_existing_output_without_reexecuting(tmp_path):
    store = Store(tmp_path / "data")
    workspace, _ = load_company(store)
    confirm_relationships(store, workspace)
    first = run_agents(store, workspace, "Check", "guided", None)
    action_id = first["action_ids"][0]
    assert "Sales (all reviewed sales)" in first["summary"]
    assert "Inventory:" in first["summary"]
    second = run_agents(store, workspace, "Check", "guided", None)
    assert second["id"] != first["id"]
    assert second["action_ids"] == [action_id]
    assert len(store.list(workspace, "action")) == 1
    assert not list((store.root / "outputs").glob("*.xlsx"))
    review_action(store, workspace, action_id, "approve", "test-human")
    output = (store.root / "outputs" / f"{action_id}.xlsx").read_bytes()
    originals = {p.name: p.read_bytes() for p in (store.root / "originals").glob("*.xlsx")}
    repeated = run_agents(store, workspace, "Check", "guided", None)
    assert repeated["status"] == "completed"
    assert repeated["action_ids"] == [action_id]
    assert "was already generated after approval" in repeated["summary"]
    assert "No duplicate proposal or workbook was created" in repeated["summary"]
    assert len(store.list(workspace, "action")) == 1
    assert len([e for e in store.events(workspace) if e["kind"] == "action.executed"]) == 1
    assert (store.root / "outputs" / f"{action_id}.xlsx").read_bytes() == output
    assert {p.name: p.read_bytes() for p in (store.root / "originals").glob("*.xlsx")} == originals


def test_empty_workspace_guided_check_finishes_with_mapping_advice(tmp_path):
    store = Store(tmp_path / "data")
    workspace = store.create_workspace("Empty")["id"]
    run = run_agents(store, workspace, "Check", "guided", None)
    assert run["status"] == "completed"
    assert run["steps"][-1]["result"]["status"] == "no_action"
    assert "Confirm an inventory mapping" in run["summary"]
    assert run["action_ids"] == []
    assert not store.list(workspace, "action")
