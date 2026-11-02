from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from sheetpilot.analytics import decimal_value, dashboard, materialize
from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.store import Store
from tests_app.helpers import load_company


@pytest.mark.parametrize("value", ["1,50", "-2", "NaN", "Infinity", "1e999999", True, None])
def test_ambiguous_or_unsafe_numeric_values_are_rejected(value):
    with pytest.raises(ValueError):
        decimal_value(value, "quantity")


def test_numeric_text_is_supported_without_locale_guessing():
    assert decimal_value("12.50","cost") == Decimal("12.50")


def test_source_cell_lineage_is_present(tmp_path):
    store=Store(tmp_path/"data")
    workspace,_=load_company(store)
    from sheetpilot.analytics import records
    row=next(r for r in records(store,workspace) if r["entity"]=="sales")
    assert row["source"]["cells"]["product_id"]=="B6"
    assert row["source"]["cells"]["revenue"]=="F6"


def test_preparse_body_limits_cover_declared_and_chunked_requests(tmp_path):
    client=TestClient(create_app(Settings(tmp_path/"data")))
    declared=client.post("/api/workspaces",content=b"x",headers={"content-length":"1000001"})
    assert declared.status_code==413
    chunked=client.post("/api/workspaces",content=iter([b"x"*600_000,b"x"*600_000]),headers={"Content-Type":"application/json"})
    assert chunked.status_code==413


def test_browser_origin_is_checked_in_local_mode(tmp_path):
    client=TestClient(create_app(Settings(tmp_path/"data")))
    response=client.post("/api/workspaces",json={"name":"Bad origin"},headers={"Origin":"https://untrusted.example"})
    assert response.status_code==403


def test_duplicate_upload_is_rejected(tmp_path):
    client=TestClient(create_app(Settings(tmp_path/"data")))
    workspace=client.post("/api/workspaces",json={"name":"Duplicate"}).json()["id"]
    data=Path("examples/synthetic.xlsx").read_bytes()
    path=f"/api/workspaces/{workspace}/uploads"
    assert client.post(path,files={"file":("one.xlsx",data)}).status_code==200
    assert client.post(path,files={"file":("two.xlsx",data)}).status_code==409


def test_nonlocal_host_header_is_rejected(tmp_path):
    client=TestClient(create_app(Settings(tmp_path/"data")))
    assert client.get("/api/health",headers={"Host":"untrusted.example"}).status_code==400
