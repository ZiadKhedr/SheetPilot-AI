# Known limitations

Supplier planning requires explicit human-reviewed base units, per-base-unit pricing and matching currencies. No unit/currency conversion, supplier communication or external order sync is implemented. Horizon-eligible receipts may still arrive after depletion; delivery dates are reviewed estimates. Source/mapping/correction changes require incoming-order re-review. Legacy basic stock-target planning remains available when the optional supplier policy is disabled. See [supplier planning](SUPPLIER_PLANNING.md).

## Workspace recovery

Backups are plaintext installation snapshots with limits of 64 MiB compressed, 256 MiB expanded and 2,048 entries. Restore publishes a separate local installation; configure its data folder and credentials in another server process. It does not merge into the running workspace. Only the current manifest/database schema is supported. See [workspace lifecycle](WORKSPACE_LIFECYCLE.md).

Workbook activation requires genuinely unique reviewed identifier fields (including composite keys). Tables without stable identifiers cannot be matched by row position. The comparison returns complete counts and bounded examples, rather than an unbounded cell diff. Candidate mappings must be reviewed and affected product links reconfirmed before purchasing; there is no automatic fuzzy migration or live cloud sync.

Data repairs support explicitly selected numeric/date conventions and exact identifier reconciliation against a unique reviewed reference. They do not execute formulas, invent missing commercial terms or perform arbitrary text rewrites. The screen shows up to 500 issues and 100 affected-record examples; counts/totals cover the complete bounded workspace. Reversing a historical/remapped source correction requires returning to the appropriate source/version review.

Durable jobs use a local worker thread and SQLite leases for the single-operator installation. Cancellation and the 180-second budget are checked between safe steps; an in-flight provider request may finish or time out first. A dead worker lease takes up to 30 seconds to expire. Interrupted or restored jobs require an explicit retry; changed sources require a new job. Legacy API callers can still request synchronous execution. This is not a distributed enterprise job scheduler.

## Verified scope
Local upload/snapshot workflow, reviewed semantics and relationships, dashboard calculations, bounded logical agents, and approved additional Excel purchase-order outputs. Full results are in TEST_RESULTS.md.

## Workbook comprehension
- .xlsx only; encrypted and macro-bearing packages are unsupported.
- Rectangular region/header detection is heuristic. Single-column tables, overlapping regions, multilevel headers, forms and charts are not comprehensively understood.
- A user can explicitly add a region and review its header. Every business mapping still needs confirmation.
- Formula expressions are inspected, never calculated. Mapped formula/error cells are excluded from operational records until resolved.
- Exact duplicate raw rows are excluded from derived totals with an alert; different order identifiers remain distinct.
- Numeric text with commas is flagged as ambiguous instead of guessing locale. Operational numeric inputs above one billion are flagged/excluded to bound arithmetic in this MVP.
- Resource grid limits may reject sparse sheets with formatting far from populated cells. The analyzer deadline is cooperative, not a hard OS quota.

## Business semantics and calculations
- Meta proposals and confidence are not guarantees or calibrated probabilities.
- Identifier overlap is evidence only. Relationships require confirmation, including strong proposals.
- Each product needs a single validated inventory snapshot. Conflicting inventory identities are excluded.
- Procurement requires a unique matching supplier quote, reviewed product relationship, matching supplier ID when provided, and explicit matching currency.
- Currency conversion, probabilistic demand forecasting, tax and multi-warehouse stock rules are outside this MVP. Reviewed supplier delivery/pack/minimum terms and separately recorded incoming orders are supported; see SUPPLIER_PLANNING.md.
- Target stock defaults to twice the reorder threshold when no target field exists. Historical sales are not subtracted from current on-hand quantities.
- New uploads are snapshots, not live synchronization. Mappings need review after schema changes. Workbooks are not replaced in place; use a separate workspace when testing a different version of the same dataset.

## Execution and access
- Approval creates an additional workbook. It does not send an order, contact suppliers or increase on-hand stock.
- Original uploads are immutable to the application; source hash changes block approval.
- Idempotency is local to the SQLite workspace and reviewed snapshot. Distributed execution needs stronger durable outbox/unique-constraint handling.
- Owner/read-only tokens and workspace-scoped lookups support a local operator. This is not enterprise authentication or full multi-tenant authorization.
- Keep the service on localhost. No internet deployment, OneDrive/SharePoint connection or SSO is claimed.
- SQLite audit events are application-append-only but a machine owner can edit local database files.

## Environment verification
- The Windows account cannot create symlinks, so that platform-specific regression is skipped. The real hard-link protection test passes with normal permissions.
- Live Meta tests are opt-in and incur provider usage; no-key environments show a clear unavailable state.
- Docker Compose config validates, but this host's Docker engine is stopped, so image build/container startup were not exercised.
- Local browser tests launch a fresh server using the installed environment and built frontend. Fresh checkout/dependency installation/build and non-live browser checks also passed on GitHub's Ubuntu runner. A local clean VM and Docker container execution were not exercised.

## Advanced mapping boundaries
- The expanded vocabulary retains order headers, customers, product catalogs, supplier directories, purchases and payments. This does not add automated accounting, tax, payment, lead-time or MOQ rules.
- Relationship candidates are limited to recognized/mapped business IDs. Formatting-normalized-only matches are previews; fuzzy joins, arbitrary foreign-key editing and leading-zero reconciliation require further work.
- Automatic context enrichment is limited to unique reviewed exact order-header and product-catalog joins. General multi-hop joins and revenue reconciliation between headers and lines are not implemented.
- Meta can analyze a selected reviewed table again, which deliberately requires fresh confirmation. All model confidence remains an estimate.

## Demand planning limits
Trailing-average consumption is a scenario, not a guaranteed forecast. Historical cutoffs and stock-snapshot alignment are explicit. Sparse history, missing dates or mismatched units cannot drive replenishment. The rate scenario does not model returns, seasonality or promotional changes. A separate reviewed supplier layer applies eligible incoming stock, pack sizes and MOQ to operational purchases. Policy review and supplier/action approvals remain required; no source facts are overwritten.
