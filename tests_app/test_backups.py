from io import BytesIO
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi.testclient import TestClient
import pytest

from sheetpilot.api import create_app
from sheetpilot.actions import propose, review_action
from sheetpilot.backups import create_backup, restore_backup
from sheetpilot.config import Settings
from sheetpilot.ingestion import digest
from sheetpilot.store import Store, Problem
from .helpers import load_company, confirm_relationships


def rewrite(content, name, value, refresh_hash=False):
    from hashlib import sha256
    output = BytesIO()
    with ZipFile(BytesIO(content)) as original:
        files = {n: original.read(n) for n in original.namelist()}
    files[name] = value
    if refresh_hash:
        manifest = json.loads(files['manifest.json'])
        manifest['files'][name] = {'sha256': sha256(value).hexdigest(), 'size': len(value)}
        files['manifest.json'] = json.dumps(manifest).encode()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for n, data in files.items(): archive.writestr(n, data)
    return output.getvalue()


def test_complete_round_trip_preserves_lineage_and_does_not_overwrite(tmp_path):
    store = Store(tmp_path / 'live')
    workspace, _ = load_company(store)
    confirm_relationships(store, workspace)
    action = review_action(store, workspace, propose(store, workspace)['id'], 'approve', 'test-owner')
    store.put(workspace, 'demand_policy', {'revision': 1, 'enabled': False})
    (store.root / '.env').write_text('MODEL_API_KEY=excluded')
    (store.root / 'provider-verification.json').write_text('excluded-fingerprint')
    (store.root / 'unrelated.txt').write_text('excluded')
    original_objects = store.list(workspace, 'workbook')
    original_events = store.events(workspace)
    archive = create_backup(store)
    with ZipFile(BytesIO(archive)) as zipped:
        assert not any('env' in name or 'verification' in name or 'unrelated' in name for name in zipped.namelist())
    result = restore_backup(store, archive)
    recovered = Store(Path(result['data_dir']))
    assert recovered.workspaces() == store.workspaces()
    for kind in ('workbook', 'table', 'relationship', 'action', 'demand_policy', 'quality'):
        assert recovered.list(workspace, kind) == store.list(workspace, kind)
    assert recovered.events(workspace) == original_events
    assert store.list(workspace, 'workbook') == original_objects
    assert store.events(workspace) == original_events
    assert digest(recovered.root / 'outputs' / f"{action['id']}.xlsx") == action['output']['sha256']
    for book in original_objects:
        assert digest(recovered.root / 'originals' / f"{book['id']}.xlsx") == book['sha256']
    assert restore_backup(store, archive)['data_dir'] != result['data_dir']
    client = TestClient(create_app(Settings(recovered.root)))
    assert client.get(f'/api/workspaces/{workspace}/dashboard').json()['revenue'] == [{'currency':'USD','amount':'1258.00'}]
    assert client.get(f"/api/workspaces/{workspace}/actions/{action['id']}/download").status_code == 200


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'C:/escape', 'originals/../../escape', '.env'])
def test_restore_rejects_unsafe_paths_before_publication(tmp_path, name):
    store = Store(tmp_path)
    store.create_workspace('safe')
    archive = rewrite(create_backup(store), name, b'bad')
    with pytest.raises(Problem): restore_backup(store, archive)
    assert not (tmp_path / 'restores').exists()


def test_hash_schema_and_reference_validation(tmp_path):
    store = Store(tmp_path / 'live')
    workspace, _ = load_company(store)
    archive = create_backup(store)
    with ZipFile(BytesIO(archive)) as zipped:
        manifest = json.loads(zipped.read('manifest.json'))
        binary = next(n for n in manifest['files'] if n.startswith('originals/'))
        database = zipped.read('sheetpilot.sqlite')
    with pytest.raises(Problem, match='hash'):
        restore_backup(store, rewrite(archive, binary, b'changed', refresh_hash=True))
    with pytest.raises(Problem):
        restore_backup(store, rewrite(archive, binary, b'changed'))
    path = tmp_path / 'tampered.sqlite'
    path.write_bytes(database)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE objects SET payload=json_set(payload,'$.workbook_id',?) WHERE kind='table'", ('f'*32,))
    con.close()
    with pytest.raises(Problem, match='reference'):
        restore_backup(store, rewrite(archive, 'sheetpilot.sqlite', path.read_bytes(), True))
    path.write_bytes(database)
    with sqlite3.connect(path) as con: con.execute('CREATE TABLE unexpected(secret TEXT)')
    con.close()
    with pytest.raises(Problem, match='schema'):
        restore_backup(store, rewrite(archive, 'sheetpilot.sqlite', path.read_bytes(), True))
    assert not (store.root / 'restores').exists()


def test_backup_routes_auth_and_roundtrip(tmp_path):
    app = create_app(Settings(tmp_path, 'owner', 'reader'))
    client = TestClient(app)
    assert client.post('/api/backups/export').status_code == 401
    assert client.post('/api/backups/export', headers={'Authorization':'Bearer reader'}).status_code == 403
    assert client.get('/api/backups/export', headers={'Authorization':'Bearer reader'}).status_code == 403
    headers = {'Authorization':'Bearer owner'}
    archive = client.post('/api/backups/export', headers=headers)
    assert archive.status_code == 200
    response = client.post('/api/backups/restore', files={'file':('backup.zip',archive.content)}, headers=headers)
    assert response.status_code == 200
    assert response.json()['counts']['workspaces'] == 0
    assert client.post('/api/backups/restore', files={'file':('bad.zip',b'bad')}, headers=headers).status_code == 422
