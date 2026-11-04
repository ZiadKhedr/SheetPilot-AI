# SheetPilot AI build progress

## Workspace lifecycle upgrade · November 4, 2026

- All six milestones complete. Final browser rerun: 12 passed, two opt-in live-provider scenarios skipped (1.5 minutes), including every new vertical slice and the original mapping, demand, supplier recovery, report, intake and mobile workflows. Credential scan passed for staged/tracked files and 451 historical Git blobs; runtime/secret paths remain excluded. The offline analyzer source is unchanged. All milestone commits are pushed to the existing authorized repository.

- Milestone 6 implemented: separate supplier-term review/preview and explicit incoming-order ledger; source-threshold precedence; supplier-specific fallback lead times; exact base units and currency; receipt/status/source eligibility; deterministic Decimal pack/MOQ arithmetic; full proposal/approval/audit/Excel calculation basis. Fourteen commercial tests passed, including stale inbound lineage and lead-time precedence. Real-backend supplier browser workflow passed; final suite results follow below.
- Final backend release check: 227 passed, five documented skips (Windows symlink plus four opt-in live Meta checks), one existing Starlette deprecation warning. Full frontend suite: 53 passed; TypeScript/Vite built. Browser suite initially passed 11 scenarios with two live cases skipped and one overly broad legacy mobile selector; the selector was scoped to Main navigation for the final rerun.

- Milestone 5 complete: SQLite-persisted queue, one local background worker, transactional request deduplication/claims, real step progress, browser reload/reconnect, safe-step cancellation, 30-second worker leases, explicit interrupted states and context/hash-checked explicit retries. Durable calls never automatically replay timeout/length provider generations. Restored queued/running jobs become interrupted. Twenty-five worker/specialist backend tests, eight frontend tests and two real-backend Edge scenarios passed. Actual official Meta durable stock review passed on fictional Company A in 13.11 seconds; the independent manifest supplied its four-product oracle. No purchase action was created.

- Milestone 4 complete: source-cell quality workspace, explicit numeric/date interpretations and unique reviewed identifier reconciliation, before/after derived record and Decimal total previews, separate approval, append-only correction revisions, source hashes/actor audit, relationship/proposal/report invalidation and separately previewed audited reversals. Eighteen repair/version/backup tests, eight repair/normalization tests, one frontend test and one real-backend Edge/mobile scenario passed. Original bytes and historical reports stayed unchanged; correction backup round trip passed.

- Milestone 3 complete: immutable workbook families with inactive version candidates; compatible mapping proposals still require review; exact reviewed composite identifiers; schema/added/changed/removed previews; ambiguity blockers; separate revision-checked review and activation. Only active snapshots enter records, planning and action fingerprints. Activation conflicts pending actions and marks historical analyses stale while preserving executed outputs/reports and source hashes. Twenty-six version/demand/action tests, one frontend test and one real-backend Edge workflow passed; TypeScript/Vite built.

- Milestone 2 complete: workspace-aware next steps returned by the state API and refreshed after mutations; exact mapping/relationship/run/action links; plain-language data and procurement blockers; current-fingerprint analysis recognition. Seven checklist/API tests, one frontend test and one real-backend Edge/mobile scenario passed; TypeScript/Vite built.

- Baseline: clean working tree at `976be9b`; verified existing `ZiadKhedr/SheetPilot-AI` remote at the same main revision. 183 offline Python tests passed, four documented skips; 45 frontend tests passed. Restricted filesystem tests were rerun with normal permissions.
- Milestone 1 complete: consistent database and referenced-workbook backup; versioned manifest; path/size/schema/reference/hash validation; restore into a new isolated installation; owner-only export and mutation-protected restore; connected recovery screen. Eight new backend tests and two frontend tests passed. TypeScript/production build passed. One real-backend Edge round-trip and invalid-archive scenario passed. Binary fetch stalled in this browser; the bounded base64 JSON transport passed, preserving the exact ZIP bytes. Direct binary API export passed separately.

## Agent jobs and work products · November 4, 2026

- Added concrete business/sales/stock/supplier/purchase-preparation jobs, with task-specific tool permissions and required checks. New typed comparison logic uses equal windows, Decimal arithmetic and currency separation; supplier review is read-only. Existing approval/idempotency rules remain intact.
- Workbench now shows real specialist outputs, source examples, actual persisted progress, runtime/check counts and downloadable work reports. Current action status resolves historical pending/executed ambiguity; older unrecorded telemetry is labeled accurately. Overview highlights the latest completed job.
- Validation: 183 offline Python tests passed (4 expected skips), 45 frontend tests passed, TypeScript/Vite built, 6 real-backend browser scenarios passed (2 live cases skipped). A separate real Meta business-review regression passed on fictional inputs in 21.49 seconds with all four required checks and no purchase action.
- Actual workspace demonstration completed four read-only checks and saved a usable report. Before/after source, policy, action/event and workbook hash comparisons passed. Local progress history remains ignored; public documentation/evidence is in AGENT_WORK.md and TEST_RESULTS.md.

## Stock outlook usability redesign · November 4, 2026

- Rebuilt the planner around results: attention summary, urgency-sorted product cards, plain stock-cover/delivery language and correctly sourced operational top-up quantities. Settings are collapsed by default; arithmetic/test top-ups and optional ordering review are separate. Saved settings can be restored without a write.
- Actual workspace/browser verification passed, including a longer delivery test and restoration to the existing saved inputs. The independent six-product arithmetic and state/original preservation checks passed. No user policy or purchase action was changed.
- Validation: 41 frontend tests passed; TypeScript/Vite built; 5 real-backend Edge browser scenarios passed with 2 live-provider cases skipped. Planner coverage includes the 390-pixel layout and the explicit save/approval boundary. Backend calculations were not changed.

## Planner explanation and verification · November 4, 2026

- Independently verified all six current eligible products under the saved assumptions and a longer delivery scenario. Confirmed preview leaves saved policy, orders/events and original workbooks unchanged. All six current products already have source reorder points, so the scenario quantities differ from operational purchase targets by design.
- Added a purpose/how-to guide, plain-language input hints, a worked data example and explicit Excel-rule priority notices. Local saved settings were restored and the guide left open in the browser.
- Verification: 15 planner Python regressions, 38 frontend tests, TypeScript/Vite build and one real-backend planner browser workflow passed. Source files and public verification docs are committed; local progress history remains ignored.

## Guided check recovery · November 4, 2026

- Fixed unclear feedback on repeat checks of an already approved purchase-order workbook. The button shows progress and a nearby fresh result with deterministic sales/inventory summaries, explicit duplicate-prevention explanation, and direct run/output navigation. Missing reviewed inventory completes with mapping advice.
- Regression evidence: 172 Python tests passed (3 documented skips), 36 frontend tests passed, TypeScript/Vite built, and 5 real-backend browser workflows passed (2 live-provider cases skipped). The post-approval browser case verifies unchanged actions/output metadata and one execution. The actual user-selected button also completed successfully in the running workspace.
- Local progress history remains ignored per the reviewer-repository cleanup; public validation evidence is recorded in docs/TEST_RESULTS.md.

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

## Review repository cleanup · November 4, 2026

- Untracked generated outputs and internal prompts/planning/audit/handoff history using Git index-only removal; every removed file remains at its original local path and is ignored.
- Kept application source, regression tests, fictional demo datasets, CLI examples, reproducible setup, architecture, judge/demo guides, limitations and sanitized verification evidence.
- Removed machine-specific startup assumptions and repaired public documentation references. No application behavior changed.
- Validation: 170 Python tests passed, 3 skipped, one existing dependency warning (72.80 seconds with normal filesystem permissions). Initial sandbox run hit a filesystem test failure and was stopped. All 31 excluded files exist locally and are ignored; retained Markdown links and git diff whitespace checks pass.

## Reviewer README refresh · November 4, 2026

- Reorganized README around product capabilities, setup, review workflow, demo datasets and reproducible checks. Put Meta configuration before startup, added clone instructions and a configuration reference, and retained verified scope and limitations.
- Checked documented commands against startup scripts, package scripts, environment defaults and Playwright configuration. Application changes already in the working tree were left untouched.
- Validation: README local links, referenced files, code fences, setup order and whitespace checks passed. Confirmed provider uses a fixed official endpoint; README does not advertise the unused META_BASE_URL setting. Documentation only; no application tests rerun.
