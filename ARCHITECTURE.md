# SheetPilot AI architecture

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

## PostgreSQL path

Retain UUIDs, workspace scoping, service boundaries and canonical records. Replace sqlite3 repository transactions with a PostgreSQL adapter/migrations, JSON text with JSONB, and BEGIN IMMEDIATE with row locks plus unique idempotency constraints. Move binaries to private object storage and retain content hashes/version metadata. Introduce a durable outbox/job worker for ingestion and execution; do not put cloud sync inside agent prompts.

## Tests and deployment evidence

See docs/TEST_RESULTS.md and docs/KNOWN_LIMITATIONS.md. Native startup and real browser workflows are tested. Docker Compose configuration is validated; engine-dependent image build/run remains unverified on this host.
