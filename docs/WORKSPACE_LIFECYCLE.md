# Workspace backup, review and version lifecycle

## Guided next steps

Overview displays six steps from the backend state API: upload, mapping review, relationship review, data blockers, analysis and purchase review. Status is computed from active workbook metadata, actual mapping/relationship revisions, excluded row errors, missing currency, procurement prerequisites and persisted runs/actions. A historical completed job counts as current only when its input fingerprint still matches. Each item links to its exact table, relationship, run or purchase action when available. All changes reload the checklist with the workspace state. Opening a checklist link never approves anything.

## Workbook version updates

In Excel files, choose **New snapshot** for the current active workbook. Every upload receives a new immutable original, source hash and family version. The candidate stays inactive. Compatible prior mappings are proposals only: review or exclude every new table in Mapping review.

Open Version review, pair corresponding tables (or explicitly mark added/removed tables), and choose one or more reviewed identifier meanings as the record key. The comparison uses exact keys, never row positions or fuzzy matching. Missing, formula/error or duplicate keys block review. Choose a genuinely unique composite key or reconcile identifiers explicitly. Preview shows column schemas, mapping changes and added/removed/changed/unchanged counts, with up to 30 before/after examples per change type per table. Every confirmed previous/new table must be accounted for.

Confirm the identifier/difference review, then separately **Activate reviewed version**. Source hashes and current review fingerprints are checked under the SQLite write lock. Exactly one family snapshot becomes active; previous originals stay downloadable. Existing pending proposals become conflicted and analyses need rerunning. Old relationships become stale; new product relationships still require explicit confirmation before purchasing. Historical reports and executed outputs retain their original source versions. Repeated activation returns the same result. Historical mappings cannot be manually rewritten through the mapping review endpoint.

API: `POST .../workbooks/{id}/versions` uploads a candidate; `GET .../versions/{id}` gives review context; `POST .../versions/{id}/preview` compares reviewed keys; `PUT .../versions/{id}/review` records human confirmation; `POST .../versions/{id}/activate` requires its current fingerprint/revision. Legacy workbooks without version metadata remain active version 1.

## Backup and restore

Open **Backup and restore** to download an installation ZIP. A SQLite write reservation spans a consistent SQLite backup and the collection of database-referenced original/output workbooks. The ZIP contains a versioned manifest, file sizes and SHA256 hashes, the database (all workspaces, mappings, relationships, policies and audit events), and referenced Excel files. Credentials, `.env`, provider verification, local dependencies and unrelated files are excluded. Backup fails if referenced originals or executed outputs are missing or changed.

Restore accepts at most 64 MiB compressed, 256 MiB expanded, 128 MiB per file and 2,048 entries. Only allowlisted relative filenames are accepted. Duplicate paths, links, encryption, extra/missing entries, hash disagreement, incompatible schema, executable schema changes and missing workspace/source references are rejected. Validation completes before publishing a new folder under the configured data directory's `restores` directory. Interrupted copies use a staging name and do not become an installation.

The current app remains connected to its existing data. The result shows the restored data folder and counts. In a separate terminal, set `SHEETPILOT_DATA_DIR` to that absolute folder and start the app on an unused port, for example `python -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port 8001`. Configure connection credentials separately. No restore merges records into, or overwrites, a running installation. Backups are plaintext and include the business workbooks; choose storage appropriate for that data.

API: `GET` or `POST /api/backups/export` returns the ZIP; `?encoding=base64` supplies the same ZIP in JSON for browser download. `POST /api/backups/restore` accepts multipart `file`. Export is explicitly owner-only and restore requires mutation access when tokens are configured. Database schema version 1 is assigned through a backward-compatible startup migration; a newer database fails closed.
