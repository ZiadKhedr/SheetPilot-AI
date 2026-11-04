# SheetPilot AI build progress

## Workspace storage recovery · November 4, 2026

- Diagnosed the reported workspace-list 500 from the running server log: `sqlite3.OperationalError: unable to open database file`. The configured `.data` directory was absent. No matching original workspace database was found among 1,218 local work/test databases; previous uploads/reviews were not recovered.
- Restored normal startup with a new local data folder and replaced the stale port-8000 server. Storage paths are absolute; request-time connections cannot silently create a replacement database. Storage failures return an actionable 503; health checks verify the workspace table and the UI supports retrying initialization.
- Recovery/API subset: 10 passed. Full offline Python suite: 170 passed, 3 skipped, one existing dependency warning. Frontend: 34 passed; TypeScript and production build passed. Installed Edge loaded all seven primary routes against the running port-8000 app with no 500s or page errors. No live Meta calls were needed for this storage fix.
- Existing real-backend browser regressions in installed Edge: 5 passed, 2 opt-in live Meta cases skipped (29.8 seconds). Covers demand policy, partial upload recovery, supplier review, retail mappings/relationships and mobile navigation. Initial launches without the Edge channel failed because bundled Chromium was absent; the Edge rerun passed.

- [x] Inspect Phase 1 and establish Git baseline: 57 passed, 1 symlink test skipped.
- [x] 1. Working upload and structure explorer — 2 new API tests passed; React upload surface connected.
- [x] 2. Official Meta provider, reviewed mappings and relationship proposals — live key/model/structured generation verified; provider and mapping validation tests pass.
- [x] 3. Normalized records and verified analytics — both independent company oracles pass; relationship evidence is computed from source values.
- [x] 4. Typed specialist tools and agent orchestration — live Meta tool workflow passed with actual pending purchase proposal.
- [x] 5. Approval, rejection, idempotency and actual Excel output — connected API flow passes for both companies; auth, cross-workspace and stale mapping tests pass.
- [x] 6. Responsive dashboard and two-company demo — eight connected pages compile; 7 frontend unit tests pass. Browser workflows now under validation.
- [x] 7. Validation and handoff — 95 Python tests passed (2 documented skips), 7 frontend unit tests passed, real Meta browser flows for both companies and mobile passed; Excel downloads inspected against the oracle. Compose config and installed-wheel smoke passed.
Live Meta access must be verified with the user's key; no fixture counts as live verification.

- [x] Procurement recovery fix (2026-11-02): read-only prerequisite checks, actionable Needs review runs, explicit supplier-link discovery/review, and stale relationship revision rejection. No automatic relationship confirmation or purchase-order execution.

- [x] Advanced semantics (2026-11-03): 53 business meanings, nine supported entities, row-aligned Meta context, explicit currency settings, safe per-table reanalysis, same-workbook identifier links, diagnostics/cardinality, and reviewed order-to-sales context. See docs/SEMANTIC_MAPPING.md.
- [x] Stale relationship recovery: confirming source mappings refreshes existing proposals; current revision checks drive the UI, with an explicit refresh action for legacy stale links. No relationship auto-approval.
- [x] Analytics explanations: reviewed inventory-to-sales product names, explicit missing-currency review links/header hints, and unassessed stock when reorder rules are absent. No currency or threshold auto-approval.

- [x] Sales-based stock planning: per-product trailing sales velocity, days remaining, estimated depletion dates, editable replenishment scenarios, explicit policy review, preservation of source thresholds, typed agent results and approval/audit integration. See docs/DEMAND_PLANNING.md.
- [x] Preview feedback recovery: explicit calculating/completion/unchanged-result states, direct results/policy navigation, clear missing-history recovery, and an accurate stock-planning CTA in Agent Workspace. Preview remains separate from approval.
- [x] Meta completion recovery: explicit reasoning/output allowance, one bounded larger-budget retry for length-truncated replies, distinct stop-reason errors, concise mapping evidence, and atomic rejection after exhausted retries. Full Python suite: 153 passed, 2 documented skips.

## Independent audit · November 4, 2026

- Intake and review now commit atomically. Overlap checks protect sales totals, read-only tokens fail closed and previously ordered inventory rows cannot be ordered again from another proposal. Supplier quote precision survives Excel generation.
- The sales tool supports product, inclusive date and currency filters and returns source cells. The orchestrator requires tool evidence before publishing a business answer. Both live Python scenarios passed separately, including USD 270.00 for product A001.
- The release Python suite with live Meta enabled passed 169 tests with one Windows symlink skip and one dependency deprecation warning. Both companies passed their real-provider browser workflows, alongside the demand, supplier-review, retail and mobile scenarios.
- UI and handoff milestone. Added source-cell inspection, aligned mapping previews, recovery from individual bad uploads and stale workspace switches, and explicit re-review of older rounded quotes. The frontend suite passed 34 tests. TypeScript and Vite built successfully. All seven browser scenarios passed across the final live suite and an isolated recovery check. The download validator matched both outputs against original product cells and hashes.
