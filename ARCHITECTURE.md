# SheetPilot AI architecture

## Workspace lifecycle and recoverable operations

[Workspace lifecycle](docs/WORKSPACE_LIFECYCLE.md) documents consistent allowlisted backups, isolated validated restoration, backend-derived guidance, exact stable-key version comparisons and explicit activation, and approved derived correction/reversal revisions. Active snapshots alone enter operational calculations. Historical original files, reports and executed outputs retain their lineage; review changes invalidate pending actions and current findings.

[Agent work](docs/AGENT_WORK.md) describes the SQLite-persisted local worker, transactional claims/request deduplication, real step progress, heartbeat leases, safe-step cancellation and explicit retries. Browser reconnection does not start provider work. Restored active jobs become interrupted. The existing specialist tools, allowlists and human purchase-approval boundary remain in place.

[Supplier planning](docs/SUPPLIER_PLANNING.md) adds a reviewed quote/terms policy and independently recorded supplier-order lines. Incoming stock requires current source lineage, explicit status/dates/units/currency and horizon eligibility. Source thresholds retain precedence; eligible demand fallbacks can use reviewed supplier delivery days. Pack/MOQ calculations use Decimal and the complete basis enters proposals, approval checks, audit records and Excel execution metadata. Workbook generation never records an incoming order or stock receipt.

## Local vertical slice

```text
React + TypeScript + Tailwind + Radix + Recharts
                    ↓ REST /api
FastAPI → immutable Excel snapshots → preserved Phase 1 analyzer
                    ↓
Bounded summaries → official Meta Model API → validated proposals
                    ↓
Human-reviewed mappings + identifier-overlap relationships
                    ↓
Normalized SQLite records + lineage → deterministic analytics
                    ↓
Meta Orchestrator → typed Sales / Inventory / Procurement tools
                    ↓
Pending action → human approve/reject → version checks → Excel output
                    ↓
Audit timeline + downloadable source-traced workbook
```

FastAPI serves the production frontend build. Vite is optional for frontend development. SQLite and all workbooks live under ignored .data. Docker Compose packages the same services in one container with a persistent named volume.

## Preserved analyzer

src/excel_intelligence remains an offline, read-only library and CLI. It bounds ZIP/XML expansion and worksheet grids, never executes formulas/macros/links, and emits validated structural reports. The app uses stricter ingestion limits (10 MiB uploads, 30 sheets, 100k cells/sheet, 200k total grid cells). A request-body gate runs before multipart parsing, including for chunked requests.

Generic heuristics cannot recognize every layout; the Structure Explorer exposes source details and supports explicit rectangular region selection.

## Data and provenance

- workspaces: separate business data contexts.
- objects: workspace-scoped workbooks, source tables/mappings, relationships, quality reports, agent runs and actions.
- records: persisted canonical operational rows, indexed by workspace/entity/product_id.
- events: append-only application audit entries.

Original files are stored under generated UUID names with SHA256 hashes, retaining human filenames only as metadata. Tables retain source workbook, worksheet, region and header row. Normalized rows retain source row and canonical-field cell coordinates. Unmapped custom fields use column indices plus original labels so repeated labels do not overwrite each other.

Confirmed mappings materialize the operational mirror. Exact duplicate raw rows are reported and excluded; invalid mandatory values are reported and excluded. Numeric text is validated with Decimal and ambiguous separators are rejected. Currency must be explicit for monetary KPIs and purchase orders. No source value is edited by normalization.

Mappings have revisions and optimistic concurrency checks. Re-review invalidates related relationship decisions. Action fingerprints include all source versions, mapping revisions/statuses and relationship decisions.

## Meta boundary

The agent job/work-report layer is described in [docs/AGENT_WORK.md](docs/AGENT_WORK.md). Named read-only jobs restrict the model's tool allowlist and require their checks to finish. New sales-period comparisons and supplier reviews produce source-backed work products. Runs expose actual step progress/runtime and downloadable text reports while preserving the separate purchase-approval boundary.

HTTPX calls https://api.meta.ai/v1 with MODEL_API_KEY from the server environment/ignored .env. muse-spark-1.3 is the tested default. No OpenAI agent framework is required.

The semantic endpoint sends bounded summaries with source IDs, labels and samples, not workbook binaries. Strict provider JSON Schema is validated again with Pydantic and membership/uniqueness checks against actual supplied tables and columns. Suggestions never self-confirm.

The Orchestrator uses allowlisted function calls. Sales and Inventory tools return deterministic analyses. Procurement creates only a pending action with quantities/costs recalculated from reviewed records. Tool arguments are typed and the loop is bounded. The user-visible trace contains tool results and a concise decision summary, not private reasoning.

Connections distinguishes configured credentials from model-catalog plus actual-generation verification. Failures are sanitized and never replaced with fake AI. Label rules and guided checks are clearly identified as non-AI alternatives.

## Action state and concurrency

pending → rejected (no output), conflicted (revalidation required), or executed (actual saved workbook).

Approval runs under SQLite BEGIN IMMEDIATE. It checks every source file hash, the reviewed context fingerprint and current deterministic line items. Idempotency keys collapse identical proposals; repeated or concurrent approval returns the same execution. An approved action writes an additional workbook to a temporary path and atomically replaces the action's unique output path before recording success. Crash retries reuse that same path instead of appending duplicate orders.

Output sheets: Purchase Orders, Source Trace, Execution. Untrusted text is escaped to prevent formula injection. Originals and on-hand inventory are untouched; the output represents a purchase-order document, not a fulfilled delivery. Generated-file hashes are checked on download.

## Permissions and operating model

The server defaults to loopback. Optional owner/read-only bearer tokens are enforced server-side; read-only tokens cannot invoke mutations. Cross-workspace IDs are resolved only within their requested workspace. Browser mutations from unexpected origins are rejected. This is a local single-operator access model; workspace separation is not a claim of enterprise tenant security.

Before hosting: implement proper identity, tenant membership, CSRF/session policy, stronger audit immutability, isolated ingestion workers, OS memory/time limits, encrypted backups and production secret management.

## Review consistency and evidence

The current SQLite implementation commits upload metadata, tables and the intake event together. Reviews rebuild the operational mirror on the same write transaction. Read paths suppress ambiguous older overlapping mappings. Reviewed sales evidence is paged at `GET /api/workspaces/{workspace}/sales/evidence`. The dashboard and scoped sales tool share Decimal aggregation. Meta selects tools and filters, and published business numbers are rendered from their results. A model-supplied final sentence is never the authority for an amount or an approval.

Purchase proposals also check for overlapping inventory source rows under the write lock. Separate subsets cannot execute against the same on-hand row twice. Local Excel publication and the SQLite commit are separate durability mechanisms. After a hard interruption, a file can exist without an executed database record. Downloads require an executed record and a matching digest. Pending actions can be retried.

## PostgreSQL path

Retain UUIDs, workspace scoping, service boundaries and canonical records. Replace sqlite3 repository transactions with a PostgreSQL adapter/migrations, JSON text with JSONB, and BEGIN IMMEDIATE with row locks plus unique idempotency constraints. Move binaries to private object storage and retain content hashes/version metadata. Introduce a durable outbox/job worker for ingestion and execution; do not put cloud sync inside agent prompts.

## Tests and deployment evidence

See docs/TEST_RESULTS.md and docs/KNOWN_LIMITATIONS.md. Native startup and real browser workflows are tested. Docker Compose configuration is validated; engine-dependent image build/run remains unverified on this host.

## Advanced semantic review (2026-11-03)
The shared catalog, row-aligned profiler, atomic bounded Meta batches, and within/across-workbook relationship engine are documented in [docs/SEMANTIC_MAPPING.md](docs/SEMANTIC_MAPPING.md). Order headers, customers, product catalogs, supplier directories, purchase lines and payments now retain their own grain. Reviewed exact joins can enrich missing sales context without adding header totals to revenue. Currency constants carry explicit reviewed-setting lineage; inventory without thresholds remains visible but cannot drive replenishment.

## Demand planning
[docs/DEMAND_PLANNING.md](docs/DEMAND_PLANNING.md) describes the read-only velocity/depletion calculator and separate versioned, human-reviewed policy. Only current exact sales/inventory joins and usable dates support replenishment; source thresholds take precedence. Policy revisions enter action fingerprints and Excel/action audits retain the calculation basis.
