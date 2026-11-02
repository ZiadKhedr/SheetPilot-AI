# Architecture

## Target system

```text
Company Excel (.xlsx) in OneDrive / SharePoint
        ↕ approved, conflict-aware sync
Integration adapters → canonical mappings + provenance → operational mirror
                                      ↓                    ↓
                              validation/review       dashboard + agents
                                                           ↓
                                      permissioned tools → audit → sync
```

Excel remains the user's source of truth and familiar workspace. The operational mirror exists for reliable querying, history, relationships, and agent context; it is not a silent replacement. Sync must detect concurrent edits, validate writes, preserve formulas/layout, and report partial failures.

## Phase 1 boundaries

```text
CLI → ZIP/XML preflight → analyzer → workbook reader (OpenPyXL, no saves)
                 → region/header heuristics
                 → column profiler
                 → Pydantic report schema → JSON
```

Modules should remain independently testable. The workbook reader enforces file and workbook limits, opens with formulas visible (never calculated), and extracts structural facts. The detector proposes candidate rectangular regions and confidence with warnings. The profiler summarizes a bounded set of values without changing source cells. A schema validates output. No network, database, AI model, macros, or write-back is involved.

Preflight streams XML with defusedxml before OpenPyXL loading, rejects DTD/entity declarations and excessive ZIP expansion, and validates worksheet dimensions, physical cell coordinates, merged ranges, and XML complexity. Limits are shared across preflight and analysis. The processing deadline is cooperative and cannot interrupt a single library call; future hosted ingestion also needs worker-level memory/time enforcement. CLI output rejects source aliases and replaces JSON atomically.

## Future services and contracts

- **Source adapters:** OneDrive/SharePoint first, using Microsoft Graph with least-privilege OAuth scopes. Keep provider IDs and file version/ETag with every snapshot. Local-file support requires a separate sync client.
- **Structure registry:** persist workbook fingerprints, sheet/table coordinates, column lineage, mapping versions, and reviewed decisions.
- **Semantic mapper:** propose entity/field mappings from labels, samples, formulas-as-text, and context. Return confidence, evidence, and unresolved alternatives. Require review below policy thresholds.
- **Data quality pipeline:** retain raw values and source coordinates; represent cleaned values and issues separately. Never silently overwrite ambiguous source data.
- **Operational mirror:** PostgreSQL with tenant isolation, source lineage, sync checkpoints, and history. Canonical entities plus tenant-specific fields/mappings.
- **Sync engine:** idempotent pull/push, ETag/version checks, retries, conflict queue, validation, explicit approval policies, and audit events. Preserve source formatting and formulas where possible.
- **Dashboard/API:** tenant-scoped metrics and configurable views over reviewed mappings.
- **Agents:** specialized read/recommend/act roles. Agents call narrow backend tools; no direct workbook or database access. Policy checks, validation, approval, idempotency, and audit wrap every action.

## Security and reliability

Treat workbook values, formulas, file names, and embedded links as untrusted data. Bound file size, worksheets, cells, runtime, and samples. Do not follow external links. Keep credentials out of logs. Enforce tenant and role checks server-side. Record actor, proposal, policy, approval, source version, before/after values, outcome, and correlation ID. Support rollback/reconciliation for writes.

## Key decisions

- Start with `.xlsx` and OpenPyXL.
- Use deterministic structural heuristics before AI; ambiguity is a valid result.
- Preserve originals and source coordinates.
- Start cloud sync with OneDrive for Business/SharePoint, not local Excel files.
- Keep Phase 1 independent of cloud services, LLMs, dashboards, and agents.
