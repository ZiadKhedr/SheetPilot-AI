# Workspace backup, review and version lifecycle

## Data quality repair workspace

Open **Data quality repairs** from navigation or a checklist issue link. Each issue shows workbook, sheet, row, original cell values, reviewed meanings and source SHA256. Formatting-only relationship mismatches also surface as identifier review issues. Up to 500 issues are shown at a time; resolve and refresh to continue.

Choose a repairable cell and explicitly select its source convention: decimal point, decimal comma, grouped comma thousands, ISO date, day/month/year or month/day/year. Identifier reconciliation requires an exact replacement found uniquely in another active, confirmed reference table with the same identifier meaning. No fuzzy identifier is silently chosen. Formula/error values are not evaluated or invented, and missing meanings/currencies go back to mapping review.

**Preview correction** recalculates records under a rolled-back savepoint and shows the proposed before/after values, affected records, row counts, inventory quantities and Decimal sales totals per currency. It persists no correction, records or audit events. Only the separate acknowledgement and **Approve correction** apply a revision. Approval repeats the calculation and checks the current source hashes, mapping/review fingerprint, correction revision and preview hash under a write lock. Up to 20 cells may be submitted through the typed API; the screen reviews one at a time.

Corrections form an append-only derived cell layer. Original reports/uploads remain untouched; record lineage and purchase output execution metadata retain correction IDs/revisions and source hashes. Identifier changes stale affected relationships; all approved/reversed corrections stale analyses and conflict pending proposals. Executed workbooks and historical agent reports remain unchanged. A **Preview reversal** operation recomputes the effect and requires separate approval to append an audited reversal. A later patch on the same cell, changed source, or incompatible remapping prevents blindly undoing an older patch. Identifier reconciliation that creates inventory collisions does not make those records operational.

API: `GET .../quality/repairs`, `POST .../quality/repairs/preview`, `POST .../quality/repairs/approve`, `POST .../quality/repairs/{id}/reverse/preview`, and `POST .../quality/repairs/{id}/reverse`. Revisions, actor, before/after values, preview basis and source hashes are retained in SQLite and included in backups.

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
