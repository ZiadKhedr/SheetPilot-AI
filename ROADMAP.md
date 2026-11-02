# Development Roadmap

Each phase should ship as a small, reviewable increment. Do not skip user review when the system is uncertain or an action has material impact.

Phase 1 implementation and synthetic tests are available. See `docs/PHASE_1_ACCEPTANCE.md` for verified behavior and the pending representative-workbook review before advancing.

| Phase | Outcome | Exit gate |
|---|---|---|
| 1. Structure analyzer | Read-only `.xlsx` inspection, region/header proposals, profiles, JSON CLI | Synthetic and representative workbook tests pass; limitations documented |
| 2. Semantic mapping | Suggest workbook/table/column meanings with evidence, confidence, and review UI/API | Users can accept, reject, or correct mappings; uncertainty is visible |
| 3. Safe profiling and cleaning | Detect missingness, duplicates, type inconsistencies, and propose normalized values | Raw data is retained; no ambiguous source value is silently changed |
| 4. Relationship discovery | Suggest keys and joins across reviewed tables/files | Relationships validated on samples and reviewable before use |
| 5. Operational mirror | Tenant-scoped PostgreSQL model with lineage and history | Repeatable imports, isolation checks, and reconciliation are reliable |
| 6. OneDrive/SharePoint sync | Change detection, source versioning, guarded writes, conflict workflow | Pull/push is idempotent, auditable, recoverable, and tested on copies |
| 7. Dashboards | Configurable KPIs and views over approved mappings | Metrics link back to source data and display freshness/quality |
| 8. Agent foundation | Permissioned read-only suggestions and audit trail | Agent cannot bypass tenant, role, or action policies |
| 9. Controlled actions | Sales, Inventory, Procurement agents and orchestrator with approval tiers | Low-risk bounds, human approvals, idempotency, and rollback are proven |

## Suggested next step after Phase 1

Run the analyzer against representative copies of different company workbooks. Review false positives and missed regions, improve deterministic structure detection, then design Phase 2's semantic mapping contract. Do not add agent autonomy before source mappings and permissions are dependable.

## Action permission tiers (future)

1. Read-only: analyze and recommend.
2. Bounded automatic actions: narrowly scoped, reversible, low-impact actions with explicit company limits.
3. Approval required: purchasing, external communication, financial changes, or other consequential writes.

Every tier is tenant-configurable and enforced by backend tools, not by prompt instructions alone.
