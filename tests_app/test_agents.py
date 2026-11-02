import pytest
from sheetpilot.agents import run_agents
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
