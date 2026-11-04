"""SQLite repository; all object queries are scoped to a workspace."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

SCHEMA_VERSION = 1


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid4().hex


class Problem(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


class Store:
    def __init__(self, root: Path):
        root = root.resolve()
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        (root / "originals").mkdir(exist_ok=True)
        (root / "outputs").mkdir(exist_ok=True)
        self.path = root / "sheetpilot.sqlite"
        with self.connection(create=True) as con:
            con.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,workspace TEXT NOT NULL,table_id TEXT NOT NULL,
                entity TEXT NOT NULL,product_id TEXT NOT NULL,data TEXT NOT NULL,source TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS records_scope ON records(workspace,entity,product_id);
            CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY, name TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS objects(
                id TEXT PRIMARY KEY, workspace TEXT NOT NULL REFERENCES workspaces(id),
                kind TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS objects_scope ON objects(workspace,kind);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,workspace TEXT NOT NULL,
                kind TEXT NOT NULL,message TEXT NOT NULL,details TEXT NOT NULL,created TEXT NOT NULL);
            """)
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise Problem("This installation needs a newer SheetPilot version to open its database.", 409)
            con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @contextmanager
    def connection(self, immediate=False, *, create=False):
        # Only startup may create a database. Losing storage during a running
        # session must never silently replace the workspace with an empty file.
        uri = self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw")
        con = sqlite3.connect(uri, uri=True, timeout=20)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            if immediate:
                con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def workspace(self, workspace):
        with self.connection() as con:
            row = con.execute("SELECT * FROM workspaces WHERE id=?", (workspace,)).fetchone()
        if row is None:
            raise Problem("Workspace not found.", 404)
        return dict(row)

    def create_workspace(self, name):
        identifier = uid()
        with self.connection() as con:
            con.execute("INSERT INTO workspaces VALUES(?,?,?)", (identifier, name, now()))
        self.event(identifier, "workspace.created", f"Created {name}.")
        return self.workspace(identifier)

    def workspaces(self):
        with self.connection() as con:
            return [dict(r) for r in con.execute("SELECT * FROM workspaces ORDER BY created DESC")]

    def put(self, workspace, kind, payload, con=None):
        if con is None:
            with self.connection() as connection:
                return self.put(workspace, kind, payload, connection)
        value = dict(payload)
        value.setdefault("id", uid())
        value.setdefault("created", now())
        con.execute("INSERT INTO objects VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                    (value["id"], workspace, kind, json.dumps(value, ensure_ascii=False, allow_nan=False), value["created"]))
        return value

    def get(self, workspace, kind, identifier, con=None):
        if con is None:
            with self.connection() as connection:
                return self.get(workspace, kind, identifier, connection)
        row = con.execute("SELECT payload FROM objects WHERE workspace=? AND kind=? AND id=?",
                          (workspace, kind, identifier)).fetchone()
        if row is None:
            raise Problem(f"{kind.title()} not found in this workspace.", 404)
        return json.loads(row[0])

    def list(self, workspace, kind, con=None):
        if con is None:
            with self.connection() as connection:
                return self.list(workspace, kind, connection)
        return [json.loads(r[0]) for r in con.execute(
            "SELECT payload FROM objects WHERE workspace=? AND kind=? ORDER BY created,rowid", (workspace, kind))]

    def event(self, workspace, kind, message, details=None, con=None):
        if con is None:
            with self.connection() as connection:
                return self.event(workspace, kind, message, details, connection)
        con.execute("INSERT INTO events(workspace,kind,message,details,created) VALUES(?,?,?,?,?)",
                    (workspace, kind, message, json.dumps(details or {}, ensure_ascii=False), now()))

    def events(self, workspace):
        with self.connection() as con:
            return [dict(r) | {"details": json.loads(r["details"])} for r in con.execute(
                "SELECT * FROM events WHERE workspace=? ORDER BY id DESC LIMIT 500", (workspace,))]
