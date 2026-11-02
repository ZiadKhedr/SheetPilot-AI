# Universal Excel-to-Agentic ERP Platform — Project Brief

## Product vision

Build a platform that lets a company keep using its existing Excel workbooks while adding a structured operational mirror, useful dashboards, and permission-controlled AI assistance. Excel files remain the working source of truth. The product learns each company's workbook structure during onboarding and records mappings so later imports and syncs can reuse them.

The long-term product can discover tables and likely business meaning across varied workbooks, profile and safely normalize data, connect related records, and synchronize approved changes back to the source. Sales, Inventory, Procurement, and Orchestrator agents can eventually recommend or execute bounded actions.

## Product principles

- Accept a wide range of `.xlsx` layouts, languages, and conventions; never promise perfect comprehension of arbitrary files.
- Keep original workbooks intact during analysis. Preserve source coordinates and provenance in every derived record.
- Separate deterministic structural analysis from semantic inference. Inferences carry confidence and ambiguity; users can review mappings.
- Treat source workbooks as untrusted input. Never execute formulas or macros, and do not send data to an external AI service in Phase 1.
- Make cleaning non-destructive. Preserve raw values and propose normalized values separately.
- Require explicit approval for risky edits; enforce permissions at a backend action boundary and audit every attempted and completed action.
- Design for safe reprocessing, idempotent sync, conflict detection, and recoverability.

## Users and jobs

- Business owner: see cross-workbook KPIs, exceptions, and pending approvals without replacing familiar spreadsheets.
- Operations staff: continue editing workbooks while benefiting from validation, alerts, and faster reporting.
- Administrator: connect OneDrive for Business/SharePoint workbooks, review detected structure and mappings, assign roles and action limits.
- Agent: read authorized data, prepare proposals, and invoke only explicitly permitted tools.

## Scope

### Phase 1 (implementation available)

Read-only Excel Structure Analyzer for `.xlsx`: inspect sheets (including hidden), populated cell coordinates, merged ranges, formulas as text, blank gaps, candidate table regions and headers, column profiles, duplicate rows, warnings, and machine-readable JSON. Provide a CLI and synthetic fixtures.

Verification status is tracked in `docs/PHASE_1_ACCEPTANCE.md`. Synthetic checks are distinct from acceptance on representative company workbooks. Report schema 1.1 includes header candidates, evidence, and explicit ambiguity.

### Later phases (not implemented)

Semantic mapping; safe cleaning and validation; relationship discovery across workbooks; operational mirror; OneDrive/SharePoint integration and bidirectional sync; dashboards; permissioned Sales, Inventory, Procurement, and Orchestrator agents.

## Phase 1 success criteria

- Analyze a valid `.xlsx` without changing it and retain original coordinates.
- Report hidden sheets, formulas, merged cells, blank rows/columns, and used ranges.
- Find common rectangular tables with headers below row 1 and multiple separated tables.
- Profile source columns and mark uncertain headers/regions rather than presenting heuristics as certainty.
- Produce validated, JSON-serializable output and clear errors for unsupported/corrupt or over-limit inputs.
- Include synthetic test workbooks and a documented CLI.

## Explicit limitations

The analyzer does not infer business semantics, execute formulas, read legacy `.xls`, `.xlsm`, encrypted files, or guarantee detection of irregular layouts. Header and table detection are heuristic. Formula cached values may be absent. Phase 1 never edits the source, connects to cloud storage, or calls an LLM.
