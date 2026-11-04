"""Allowlisted installation snapshots and validated, isolated restores.

Never extract an archive into live storage or execute SQL supplied by an archive.
The write reservation covers the SQLite snapshot and immutable binary collection.
"""
from hashlib import sha256
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import sqlite3
import stat
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

from .ingestion import digest
from .store import Problem, SCHEMA_VERSION, Store, now, uid

ARCHIVE_LIMIT = 64 * 1024 * 1024
EXPANDED_LIMIT = 256 * 1024 * 1024
MEMBER_LIMIT = 128 * 1024 * 1024
FILE_LIMIT = 2048
KINDS = {"workbook", "table", "relationship", "relationship_report", "quality", "action", "run",
         "demand_policy", "version_review", "correction", "correction_state", "commercial_policy", "incoming_order", "job"}
ID = re.compile(r"^[a-f0-9]{32}$")
MEMBER = re.compile(r"^(?:sheetpilot\.sqlite|manifest\.json|(?:originals|outputs)/[a-f0-9]{32}\.xlsx)$")


def _binary_references(con):
    files = {}
    for row in con.execute("SELECT id,kind,payload FROM objects WHERE kind IN ('workbook','action')"):
        value = json.loads(row["payload"])
        if row["kind"] == "workbook":
            files[f"originals/{row['id']}.xlsx"] = value["sha256"]
        elif value.get("status") == "executed":
            files[f"outputs/{row['id']}.xlsx"] = value["output"]["sha256"]
    return files


def create_backup(store):
    """Return a bounded ZIP; only database-referenced files are included."""
    with TemporaryDirectory(prefix="sheetpilot-backup-") as temporary:
        database = Path(temporary) / "sheetpilot.sqlite"
        with store.connection(immediate=True) as locked:
            with closing(sqlite3.connect(store.path.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(database)) as destination:
                    source.backup(destination)
                    destination.execute("PRAGMA journal_mode=DELETE")
            files = _binary_references(locked)
            if len(files) + 2 > FILE_LIMIT:
                raise Problem("This installation exceeds the local backup file limit.", 413)
            entries = {"sheetpilot.sqlite": database, **{name: store.root / name for name in files}}
            metadata, total = {}, 0
            for name, path in entries.items():
                if not path.is_file() or path.is_symlink():
                    raise Problem("A referenced workbook is missing; restore storage access before backing up.", 409)
                size = path.stat().st_size
                total += size
                if size > MEMBER_LIMIT or total > EXPANDED_LIMIT:
                    raise Problem("This installation exceeds the local backup size limit.", 413)
                checksum = digest(path)
                if name in files and checksum != files[name]:
                    raise Problem("A referenced workbook hash changed; backup refused.", 409)
                metadata[name] = {"sha256": checksum, "size": size}
            manifest = {"format": "sheetpilot-backup", "version": 1, "schema_version": SCHEMA_VERSION,
                        "created": now(), "files": metadata,
                        "workspaces": [dict(r) for r in locked.execute("SELECT * FROM workspaces ORDER BY created")]}
            output = BytesIO()
            with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
                for name, path in entries.items():
                    archive.write(path, name)
            result = output.getvalue()
            if len(result) > ARCHIVE_LIMIT:
                raise Problem("Backup exceeds the 64 MiB archive limit.", 413)
        return result


def _validate_database(path, expected_files, schema_version, temporary):
    # Compare executable schema against one made by this application. No triggers,
    # views, virtual tables, expression indexes, or unknown schema are accepted.
    template = Store(Path(temporary) / "schema")
    def schema(con):
        return {r[0]: (r[1], " ".join((r[2] or "").split())) for r in con.execute(
            "SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex_%'")}
    with template.connection() as known:
        expected_schema = schema(known)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as con:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA trusted_schema=OFF")
        con.execute("PRAGMA query_only=ON")
        if (schema(con) != expected_schema or con.execute("PRAGMA user_version").fetchone()[0] != schema_version
                or con.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                or con.execute("PRAGMA foreign_key_check").fetchone()):
            raise Problem("Backup database schema or integrity is incompatible.")
        workspaces = {r["id"] for r in con.execute("SELECT * FROM workspaces")}
        if any(not ID.fullmatch(w) for w in workspaces):
            raise Problem("Backup contains an invalid workspace identifier.")
        objects, workbook_ids, table_ids = [], set(), set()
        for row in con.execute("SELECT * FROM objects"):
            if len(objects) >= 100_000 or row["workspace"] not in workspaces or row["kind"] not in KINDS or not ID.fullmatch(row["id"]):
                raise Problem("Backup contains unsupported objects or workspace references.")
            value = json.loads(row["payload"])
            if not isinstance(value, dict) or value.get("id") != row["id"]:
                raise Problem("Backup object identifiers are inconsistent.")
            objects.append((row["workspace"], row["kind"], value))
            if row["kind"] == "workbook": workbook_ids.add((row["workspace"], row["id"]))
            if row["kind"] == "table": table_ids.add((row["workspace"], row["id"]))
        def references(value, workspace):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"workbook_id", "parent_workbook_id", "previous_workbook_id"} and item is not None and (workspace, item) not in workbook_ids:
                        raise Problem("Backup contains a missing workbook reference.")
                    if key in {"table_id", "left_table", "right_table", "inventory_table_id"} and item and (workspace, item) not in table_ids:
                        raise Problem("Backup contains a missing table reference.")
                    references(item, workspace)
            elif isinstance(value, list):
                for item in value: references(item, workspace)
        for workspace, kind, value in objects:
            references(value, workspace)
        for row in con.execute("SELECT workspace,table_id,data,source FROM records"):
            if (row["workspace"], row["table_id"]) not in table_ids:
                raise Problem("Backup records reference a missing source table.")
            json.loads(row["data"])
            references(json.loads(row["source"]), row["workspace"])
        for row in con.execute("SELECT workspace,details FROM events"):
            if row["workspace"] not in workspaces:
                raise Problem("Backup audit history references a missing workspace.")
            json.loads(row["details"])
        references_by_path = _binary_references(con)
        if set(expected_files) != {"sheetpilot.sqlite", *references_by_path}:
            raise Problem("Backup files do not match database references.")
        for name, checksum in references_by_path.items():
            if checksum != expected_files[name]["sha256"]:
                raise Problem("Backup source/output hashes disagree with database references.")
        return {"workspaces": len(workspaces), "objects": len(objects), "files": len(references_by_path)}


def restore_backup(store, content):
    if len(content) > ARCHIVE_LIMIT:
        raise Problem("Restore archive exceeds 64 MiB.", 413)
    try:
        with ZipFile(BytesIO(content)) as archive, TemporaryDirectory(prefix="sheetpilot-restore-") as temporary:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > FILE_LIMIT or len(set(names)) != len(names) or "manifest.json" not in names:
                raise Problem("Backup has missing, duplicate, or too many entries.")
            if sum(entry.file_size for entry in entries) > EXPANDED_LIMIT:
                raise Problem("Expanded backup exceeds 256 MiB.", 413)
            for entry in entries:
                if (not MEMBER.fullmatch(entry.filename) or entry.file_size > MEMBER_LIMIT or entry.flag_bits & 1
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise Problem("Backup contains an unsafe path, link, encrypted entry, or oversized file.")
            if archive.getinfo("manifest.json").file_size > 1_000_000:
                raise Problem("Backup manifest is too large.")
            manifest = json.loads(archive.read("manifest.json"))
            if (manifest.get("format") != "sheetpilot-backup" or manifest.get("version") != 1
                    or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION):
                raise Problem("Backup format or database version is incompatible. Use the matching SheetPilot release.")
            files = manifest.get("files")
            if not isinstance(files, dict) or set(files) != set(names) - {"manifest.json"} or "sheetpilot.sqlite" not in files:
                raise Problem("Backup manifest and archive file list disagree.")
            staging = Path(temporary) / "installation"
            staging.mkdir()
            for name, metadata in files.items():
                entry = archive.getinfo(name)
                if (not isinstance(metadata, dict) or metadata.get("size") != entry.file_size
                        or not isinstance(metadata.get("sha256"), str) or not re.fullmatch("[a-f0-9]{64}", metadata["sha256"])):
                    raise Problem("Backup manifest contains invalid file metadata.")
                path = staging / name
                path.parent.mkdir(exist_ok=True)
                with archive.open(entry) as source, path.open("xb") as destination:
                    shutil.copyfileobj(source, destination, length=64 * 1024)
                if digest(path) != metadata["sha256"]:
                    raise Problem("Backup file hash verification failed; nothing was restored.")
            counts = _validate_database(staging / "sheetpilot.sqlite", files, manifest["schema_version"], temporary)
            (staging / "originals").mkdir(exist_ok=True)
            (staging / "outputs").mkdir(exist_ok=True)
            restore_id = uid()
            parent = store.root / "restores"
            parent.mkdir(exist_ok=True)
            target = parent / restore_id
            # Exclusive destination, atomic publication. Live database is never changed.
            publishing = parent / (restore_id + ".staging")
            try:
                shutil.copytree(staging, publishing)
                publishing.rename(target)
            finally:
                if publishing.exists(): shutil.rmtree(publishing)
            return {"id": restore_id, "status": "restored", "data_dir": str(target), "counts": counts,
                    "message": "Verified backup restored into an isolated installation. Existing workspaces are unchanged. "
                               "Start a separate SheetPilot server with SHEETPILOT_DATA_DIR set to this folder."}
    except Problem:
        raise
    except (BadZipFile, OSError, ValueError, KeyError, TypeError, sqlite3.Error, RuntimeError, RecursionError):
        raise Problem("Invalid or unreadable backup. No live workspace data was changed.") from None
