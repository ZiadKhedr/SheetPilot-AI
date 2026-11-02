# SheetPilot AI — Project Brief

**Your Spreadsheets. Your AI Workforce.**

## Current objective

The user expanded the original Universal Excel-to-Agentic ERP vision on 2026-11-02 into a focused Meta AI Hackathon MVP. Build a polished, real workflow for a solo developer rather than an enterprise ERP in one pass. The full authorized brief is preserved in docs/HACKATHON_REQUIREMENTS.md.

Companies keep their existing Excel files. SheetPilot inspects structure, asks Meta for semantic proposals, lets users confirm mappings and relationships, computes a normalized business view, and coordinates bounded specialist tools. Human approval generates an additional purchase-order workbook with a source trace and execution record.

## Implemented product flow

Upload → structural report → Meta semantic proposals → mapping review → evidence-based relationship review → normalized SQLite mirror → dashboard → Orchestrator and specialist tools → pending proposal → approve/reject → real Excel download → audit timeline.

Eight UI pages: Overview, Excel File Manager, Structure Explorer, Mapping Review, Business Analytics, Agent Workspace, Approval Center and Activity Timeline.

Two independent fictional businesses exercise English/Arabic labels, different ranges and headers, duplicate/missing data, numeric text, unrelated admin tables, formulas and hidden sheets.

## Non-negotiable principles

- Preserve uploaded originals, source coordinates and file hashes.
- Separate facts, deterministic calculations, AI proposals and human review.
- Never claim perfect arbitrary-workbook comprehension.
- Require explicit review of semantic mappings and relationships before operational use.
- Keep private reasoning and API credentials off the client and out of Git.
- Let Meta plan and interpret; let typed backend tools calculate and act.
- Agents cannot execute arbitrary Python/SQL/filesystem operations or approve their own proposals.
- Risky edits require approval. This MVP generates an additional workbook; it does not overwrite source Excel.
- Validate source versions at approval, use deterministic money/quantity calculations, protect against duplicate execution, and audit outcomes.
- No fake calls, hardcoded business insights, or mock backend in product runtime.

## Verification and success

See docs/TEST_RESULTS.md for actual tests. Real official Meta model access, structured semantic generation and tool orchestration are exercised with the user's local key. Browser workflows cover both company schemas through actual Excel downloads; unit/contract mocks remain confined to tests.

## Long-term vision retained

The original platform can later expand to canonical entities plus custom fields, robust cross-file relationships, non-destructive cleaning, dynamic dashboards, permission-controlled operations, and version-aware bidirectional OneDrive/SharePoint sync. SQLite has a documented PostgreSQL migration path. Local file snapshots and approved output workbooks are the current, accurately stated capability.

## Boundaries

This is a local single-operator hackathon app. It does not implement enterprise RBAC/SSO, live cloud sync, external supplier communications or autonomous financial commitments. Irregular layouts and weak semantic evidence still require a human.
