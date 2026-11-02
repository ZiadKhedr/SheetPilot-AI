from pathlib import Path

from fastapi.testclient import TestClient

from sheetpilot.api import create_app
from sheetpilot.config import Settings


def test_upload_inspects_real_workbook_without_modifying_it(tmp_path):
    client = TestClient(create_app(Settings(tmp_path / "data")))
    workspace = client.post("/api/workspaces", json={"name": "Test business"}).json()["id"]
    path = Path("examples/synthetic.xlsx")
    before = path.read_bytes()
    response = client.post(f"/api/workspaces/{workspace}/uploads",
                           files={"file": ("sales.xlsx", before, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 200, response.text
    state = client.get(f"/api/workspaces/{workspace}/state").json()
    assert len(state["workbooks"]) == 1
    assert state["workbooks"][0]["report"]["sheet_count"] == 2
    assert state["tables"][0]["header_row"] == 5
    assert path.read_bytes() == before
    downloaded = client.get(f"/api/workspaces/{workspace}/workbooks/{response.json()['id']}/download")
    assert downloaded.content == before


def test_upload_errors_and_authorization(tmp_path):
    client = TestClient(create_app(Settings(tmp_path / "data", "owner", "reader")))
    assert client.get("/api/workspaces").status_code == 401
    assert client.post("/api/workspaces", json={"name": "No"}, headers={"Authorization": "Bearer reader"}).status_code == 403
    owner = {"Authorization": "Bearer owner"}
    workspace = client.post("/api/workspaces", json={"name": "Yes"}, headers=owner).json()["id"]
    assert client.post(f"/api/workspaces/{workspace}/uploads", headers=owner, files={"file": ("bad.xls", b"bad")}).status_code == 422
    assert client.post(f"/api/workspaces/{workspace}/uploads", headers=owner, files={"file": ("bad.xlsx", b"bad")}).status_code == 422
