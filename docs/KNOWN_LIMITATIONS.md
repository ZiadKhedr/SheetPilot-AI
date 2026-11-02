# Known limitations

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
- Currency conversion, demand forecasting, tax, supplier minimum-order quantities, lead times and multi-warehouse stock rules are outside this MVP.
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
- Browser tests launch a fresh server using the installed Python environment and built frontend. Fresh dependency installation is documented but a separate clean machine has not been provisioned.
