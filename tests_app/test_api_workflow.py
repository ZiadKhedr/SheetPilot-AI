from io import BytesIO
from pathlib import Path
import json

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pytest

from sheetpilot.api import create_app
from sheetpilot.config import Settings


def ingested_client(tmp_path, company):
    app=create_app(Settings(tmp_path/"data", "owner", "viewer"))
    client=TestClient(app,headers={"Authorization":"Bearer owner"})
    workspace=client.post("/api/workspaces",json={"name":company}).json()["id"]
    base=f"/api/workspaces/{workspace}"
    oracle=json.loads(Path("demo_data/manifest.json").read_text(encoding="utf-8"))["companies"][company]
    hashes={}
    for entity,config in oracle["files"].items():
        path=Path("demo_data")/company/config["filename"]
        original=path.read_bytes()
        response=client.post(base+"/uploads",files={"file":(path.name,original)})
        assert response.status_code==200,response.text
        hashes[response.json()["id"]]=original
        table=next(t for t in client.get(base+"/state").json()["tables"] if t["workbook_id"]==response.json()["id"] and t["ref"]==config["ref"])
        result=client.put(base+"/tables/"+table["id"],json={"entity":entity,"fields":config["columns"],
            "header_row":config["header_row"],"expected_revision":0,"confirm":True})
        assert result.status_code==200,result.text
    relations=client.post(base+"/relationships/discover").json()
    for relation in relations:
        if relation["field"]=="product_id":
            result=client.put(base+"/relationships/"+relation["id"],json={"decision":"approve"})
            assert result.status_code==200,result.text
    return app,client,workspace,base,oracle,hashes


@pytest.mark.parametrize("company", ["company_a","company_b"])
def test_complete_api_workflow_approval_and_download(tmp_path,company):
    app,client,workspace,base,oracle,originals=ingested_client(tmp_path,company)
    dashboard=client.get(base+"/dashboard").json()
    assert dashboard["revenue"]==[{"currency":oracle["currency"],"amount":oracle["expected"]["revenue"]}]
    run=client.post(base+"/agents",json={"message":"Guided replenishment","mode":"guided"})
    assert run.status_code==200,run.text
    action_id=run.json()["action_ids"][0]
    assert client.get(base+"/actions/"+action_id+"/download").status_code==404
    result=client.put(base+"/actions/"+action_id+"/review",json={"decision":"approve"})
    assert result.status_code==200,result.text
    second=client.put(base+"/actions/"+action_id+"/review",json={"decision":"approve"})
    assert second.json()["output"]==result.json()["output"]
    output=client.get(base+"/actions/"+action_id+"/download")
    assert output.status_code==200
    wb=load_workbook(BytesIO(output.content))
    assert wb["Purchase Orders"].max_row==4
    wb.close()
    for identifier,original in originals.items():
        assert client.get(base+"/workbooks/"+identifier+"/download").content==original
    events=client.get(base+"/state").json()["events"]
    assert len([e for e in events if e["kind"]=="action.executed"])==1
    assert len(list((app.state.store.root/"outputs").glob("*.xlsx")))==1


def test_unauthorized_and_cross_workspace_actions_are_blocked(tmp_path):
    app,client,workspace,base,oracle,_=ingested_client(tmp_path,"company_a")
    action=client.post(base+"/actions/draft",json={"product_ids":[]}).json()
    viewer=TestClient(app,headers={"Authorization":"Bearer viewer"})
    assert viewer.put(base+"/actions/"+action["id"]+"/review",json={"decision":"approve"}).status_code==403
    stranger=TestClient(app,headers={"Authorization":"Bearer invalid"})
    assert stranger.put(base+"/actions/"+action["id"]+"/review",json={"decision":"approve"}).status_code==401
    other=client.post("/api/workspaces",json={"name":"Other"}).json()["id"]
    assert client.put(f"/api/workspaces/{other}/actions/{action['id']}/review",json={"decision":"approve"}).status_code==404
    assert not list((app.state.store.root/"outputs").glob("*.xlsx"))


def test_api_rejection_and_mapping_version_conflicts(tmp_path):
    app,client,workspace,base,oracle,_=ingested_client(tmp_path,"company_a")
    action=client.post(base+"/actions/draft",json={"product_ids":["A001"]}).json()
    assert client.put(base+"/actions/"+action["id"]+"/review",json={"decision":"reject"}).json()["status"]=="rejected"
    assert client.put(base+"/actions/"+action["id"]+"/review",json={"decision":"approve"}).status_code==409
    next_action=client.post(base+"/actions/draft",json={"product_ids":["A002"]}).json()
    table=next(t for t in client.get(base+"/state").json()["tables"] if t["entity"]=="inventory")
    body={"entity":table["entity"],"fields":table["fields"],"header_row":table["header_row"],"expected_revision":table["revision"],"confirm":True}
    assert client.put(base+"/tables/"+table["id"],json=body).status_code==200
    assert client.put(base+"/actions/"+next_action["id"]+"/review",json={"decision":"approve"}).status_code==409
    assert not list((app.state.store.root/"outputs").glob("*.xlsx"))


def test_manual_region_and_exclusion(tmp_path):
    client=TestClient(create_app(Settings(tmp_path/"data")))
    workspace=client.post("/api/demo/company_a").json()["id"]
    base="/api/workspaces/"+workspace
    state=client.get(base+"/state").json()
    wb=state["workbooks"][0]
    bad=client.post(base+"/workbooks/"+wb["id"]+"/regions",json={"sheet":wb["report"]["worksheets"][0]["title"],"ref":"A1:XFD1000000","header_row":1})
    assert bad.status_code==422
    table=state["tables"][0]
    result=client.put(base+"/tables/"+table["id"],json={"entity":"unknown","fields":{},"header_row":table["header_row"],"expected_revision":0,"confirm":False,"ignore":True})
    assert result.json()["status"]=="ignored"
