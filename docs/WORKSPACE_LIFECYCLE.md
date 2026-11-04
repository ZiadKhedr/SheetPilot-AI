# Workspace backup, review and version lifecycle

## Backup and restore

Open **Backup and restore** to download an installation ZIP. A SQLite write reservation spans a consistent SQLite backup and the collection of database-referenced original/output workbooks. The ZIP contains a versioned manifest, file sizes and SHA256 hashes, the database (all workspaces, mappings, relationships, policies and audit events), and referenced Excel files. Credentials, `.env`, provider verification, local dependencies and unrelated files are excluded. Backup fails if referenced originals or executed outputs are missing or changed.

Restore accepts at most 64 MiB compressed, 256 MiB expanded, 128 MiB per file and 2,048 entries. Only allowlisted relative filenames are accepted. Duplicate paths, links, encryption, extra/missing entries, hash disagreement, incompatible schema, executable schema changes and missing workspace/source references are rejected. Validation completes before publishing a new folder under the configured data directory's `restores` directory. Interrupted copies use a staging name and do not become an installation.

The current app remains connected to its existing data. The result shows the restored data folder and counts. In a separate terminal, set `SHEETPILOT_DATA_DIR` to that absolute folder and start the app on an unused port, for example `python -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port 8001`. Configure connection credentials separately. No restore merges records into, or overwrites, a running installation. Backups are plaintext and include the business workbooks; choose storage appropriate for that data.

API: `GET` or `POST /api/backups/export` returns the ZIP; `?encoding=base64` supplies the same ZIP in JSON for browser download. `POST /api/backups/restore` accepts multipart `file`. Export is explicitly owner-only and restore requires mutation access when tokens are configured. Database schema version 1 is assigned through a backward-compatible startup migration; a newer database fails closed.
