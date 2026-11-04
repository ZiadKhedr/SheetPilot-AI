from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from sheetpilot.api import create_app
from sheetpilot.config import Settings
from sheetpilot.store import Store


@pytest.mark.parametrize("remove_folder", [False, True])
def test_storage_loss_returns_actionable_503_and_restoring_preserves_workspace(tmp_path, remove_folder):
    root = tmp_path / "data"
    app = create_app(Settings(root))
    client = TestClient(app)
    workspace = client.post("/api/workspaces", json={"name": "Existing business"}).json()
    original = root if remove_folder else app.state.store.path
    backup = tmp_path / "storage-backup"
    original.rename(backup)
    try:
        for endpoint in ("/api/workspaces", "/api/health"):
            response = client.get(endpoint)
            assert response.status_code == 503
            assert "Workspace storage is unavailable" in response.json()["detail"]
            assert str(tmp_path) not in response.text
        assert client.post("/api/workspaces", json={"name": "Must not create"}).status_code == 503
        assert not original.exists()
    finally:
        backup.rename(original)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/workspaces").json() == [workspace]


def test_relative_store_path_survives_working_directory_change(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(Path("data"))
    workspace = store.create_workspace("Stable storage")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert store.workspaces() == [workspace]
    assert not (other / "data").exists()
