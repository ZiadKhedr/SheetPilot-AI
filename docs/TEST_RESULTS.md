# SheetPilot AI — verification evidence

## Workspace storage recovery · November 4, 2026

- Reproduced database/folder loss in API regressions: workspace reads, writes and health return sanitized actionable 503 responses, never create an empty replacement file, and recover the original workspace after storage restoration. A relative store path also survives a working-directory change.
- Full offline suite: **170 passed, 3 skipped**, one existing Starlette warning. The skips are the Windows symlink test and two opt-in Meta cases. Focused recovery/upload/API workflow subset: **10 passed**.
- Frontend: **34 passed**; TypeScript and Vite build passed using installed local tools. The pnpm wrapper attempted a forbidden sandbox symlink; direct Node execution of the existing TypeScript/Vite/Vitest installations succeeded.
- Existing browser suite in installed Edge: **5 passed, 2 live Meta cases skipped**, 29.8 seconds. An initial bundled-Chromium launch failed because its executable was absent. No live Meta calls were performed for this fix.
- The repaired local server on port 8000 passed a separate seven-route browser smoke check and database health check, with no 500 responses or browser page errors. The original `.data` directory was missing before the repair; previous user workspaces/uploads were not recovered. The running app now uses newly initialized local storage.

## Independent audit run · November 4, 2026

| Verification | Observed |
| --- | --- |
| Full pytest suite with live Meta enabled | **169 passed, 1 skipped** in 141.33 seconds on Windows on the final compatibility run. Both real Meta tests ran. The skipped CLI test requires symlink privileges. Starlette emitted one TestClient dependency deprecation warning. |
| Real Meta account check | The official `/models` catalog included `muse-spark-1.3` and a structured ping succeeded. The live mapping, replenishment, approval and scoped A001 revenue tests passed. |
| Frontend tests | **34 passed** across eight files, including mapped-row preview, source cells, unknown products and retry. |
| Build | TypeScript project check and Vite production build passed. Python bytecode compilation and `git diff --check` passed. No standalone Python or frontend linter is configured or installed here. |
| Browser | Seven distinct scenarios passed in headless Edge. The final live run passed six tests in 4.2 minutes. A seventh test passed separately and verified partial batch recovery and stale-data handling after a failed workspace switch. Playwright started the production frontend and a fresh FastAPI/SQLite workspace for each run. |
| Download inspection | Both Excel files reopened. All three order lines per business matched the independent product/quantity/amount oracle. Electronics totaled USD 1,809.00 and restaurant totaled EGP 12,630.00. Each of the six trace rows per file matched an original workbook hash, sheet, range and product cell. Both downloads contained an execution sheet and no formulas. |
| Packaging | `docker compose config --quiet` passed. Docker Desktop's Linux engine pipe was absent, so container build/start was not executed. The browser tests started the native production app. |

The first live workflow failed because the model encoded unused filters as the string `"null"`. The final schema accepts an explicit array of filters. No fake fallback was introduced. One new frontend test required cleanup between dialogs and one quote test needed an explicit header review. All product verification used fictional inputs.

The following is historical evidence from the initial build.

Date: 2026-11-02. Local Windows host. Python 3.12.14, pytest 8.4.2, OpenPyXL 3.1.5, Pydantic 2.14.1, Node 24.22.1, Vite 7.3.7, Vitest 3.2.7, installed Microsoft Edge via Playwright.

## Original baseline
57 passed, 1 skipped before app changes. The skipped case requires symlink creation privileges. A restricted first attempt also failed the hard-link case; it passed when rerun with normal filesystem permissions.

## Current Python suite
**95 passed, 2 skipped, 1 dependency warning** in 13.52 seconds. Raw logs are retained locally under ignored `outputs/`; they are not included in a clean clone.

Coverage includes structure, hidden sheets, formulas, merged titles, offset/Arabic headers, pre-load resource limits, upload errors, strict Meta output validation, invalid/unknown AI tools, source-column checks, reviewed relationships, accurate calculations for both companies, API access control, cross-workspace lookup protection, rejected/changed-source approvals, repeated/concurrent execution, original preservation, actual Excel output, body limits and numeric ambiguity.

Expected skips in the regular local suite:
- OS symlink test: this Windows account cannot create symlinks.
- Opt-in live Meta test: omitted from the ordinary offline test command.

One dependency warning is emitted: Starlette deprecates its current HTTPX TestClient adapter in favor of HTTPX2. Existing integration assertions pass; this is not hidden as a test failure.

## Real Meta verification
- Account-visible GET /models included muse-spark-1.3.
- A real strict-schema generation succeeded.
- Opt-in backend live test: **1 passed** in 40.61 seconds. It performed real semantic mapping, reviewed normalization/relationships, Meta tool orchestration, human-approved execution, and an Excel output.
- Final browser live tests also exercised this path for both companies, including a provider verification click.

No mock transport was used in these live runs. Unit tests use isolated MockTransport responses only for provider error/contract coverage.

## Frontend
- TypeScript compilation: passed.
- Production build: passed; vendor/chart chunks separated.
- Vitest: **7 passed** across API error handling, workspace-token handling, currency display, unavailable vs real metrics, disabled actions and accessible review dialog.

## Actual end-to-end browser run
Fresh backend on port 8010, built frontend, real Meta API, no mocked application backend:
- Electronics: **passed**, 43.7 seconds.
- Restaurant/Arabic schema: **passed**, 56.0 seconds.
- Mobile navigation/layout: **passed**, 1.1 seconds.
- Total: **3 passed**, 1.7 minutes.

Both flows created a workspace, uploaded three real files through the UI, requested Meta mappings, confirmed three business tables, discovered/reviewed relationships, checked actual KPIs, ran Meta specialist orchestration, inspected action details, approved, downloaded Excel, and checked the execution timeline. Browser page-error assertions passed.

Historical screenshots and downloaded workbooks are retained locally under ignored `outputs/`; rerun the browser suite to produce fresh artifacts under `frontend/test-results/`. They show actual execution data, not a designed mockup. A first browser attempt failed to launch due to restricted temporary-folder permissions; a first test-server attempt had an invalid Windows relative command path. Both were corrected before the successful run.

## Downloaded workbook inspection
scripts/validate_downloads.py opened each browser download with OpenPyXL:
- Company A: three lines, 82 units, USD 1,809.
- Company B: three lines, 47 units, EGP 12,630.
- Product-level quantities/totals match the independent fixture oracle.
- Purchase Orders, Source Trace and Execution sheets exist.
- Untrusted strings are not formula cells.
- API/service tests separately verify all uploaded originals byte-for-byte and confirm rejection creates no output.

## Deployment/packaging
- Native production frontend/backend HTTP startup: passed.
- Non-editable installed Python wheel: frontend serving, demo ingestion and API smoke check passed with explicit SHEETPILOT_ROOT.
- Docker Compose configuration: passed `docker compose config --quiet`.
- Docker image build/container execution: **not run** because Docker Desktop's engine is stopped. No successful container deployment is claimed.
- GitHub Actions passed for release commit 2ae59c6 on a fresh Ubuntu runner: clean dependency installation, backend tests, frontend tests/build, and mobile browser validation all succeeded. Evidence: https://github.com/ZiadKhedr/SheetPilot-AI/actions/runs/41484828970. Live Meta remains opt-in and was verified locally for both businesses; no key was added to CI.

## Credential hygiene
scripts/check_secrets.py confirms the configured Meta key is absent from tracked working files and historical Git blobs. .env, .data, work/, .venv and node_modules are ignored. The committed demo datasets and sanitized validation evidence contain fictional data only. Generated screenshots, downloads and raw logs are ignored.

## Remaining non-MVP validation
Authorized real-company workbook benchmarks, hard ingestion worker isolation, OS-enforced runtime/memory quotas, production identity/tenant controls, cloud synchronization and container-engine execution remain outside verified scope. See KNOWN_LIMITATIONS.md.

## Procurement review recovery — 2026-11-02
- Python: 102 passed, 2 skipped (Windows symlink privilege and opt-in live Meta), one dependency deprecation warning.
- Frontend: 10 unit tests passed; TypeScript and production build passed.
- Real-backend browser regression passed: absent links create no action; discovery alone does not approve; explicit confirmation unlocks a pending EGP 12,630 draft with no output workbook. This regression uses guided tools, not live Meta.

## Advanced mapping and relationships — 2026-11-03
- Full offline Python suite: **124 passed, 2 skipped**, one FastAPI/Starlette dependency deprecation warning. Skips: Windows symlink privilege and opt-in live Meta test.
- Frontend: **13 unit tests passed**; TypeScript and production build passed.
- Playwright with real backend: **3 passed, 2 opt-in live-browser tests skipped**. Covers procurement review recovery, four-sheet retail mapping/relationship review, and mobile navigation.
- Live official Meta mapping on the independent synthetic retail fixture: all four entities and price/discount/stock/order/customer meanings matched expectations; GBP was proposed from explicit monetary headers; all three expected identifier links appeared as unconfirmed previews. One mapping call completed in 44.4 seconds. Sanitized evidence: [validation/semantic-mapping-live.json](validation/semantic-mapping-live.json).
- Separate opt-in live Meta regression: **1 passed in 221.41 seconds**. Existing electronics mapping, deterministic analytics, actual Meta tool orchestration, pending purchase proposal, explicit test approval and Excel output all passed.
- Negative/edge regressions include omitted/foreign AI tables, unsupported currency, atomic batches, concurrent review, invalid headers, duplicate meanings, no-overlap diagnostics, normalized-only IDs, leading zeroes, ambiguous masters, stale joins, order-total double-counting, threshold-free inventory and broader entity retention.
- Originals remain byte-for-byte preserved; no source data was auto-confirmed. Live checks used synthetic/fictional data only. Current uploaded business data was inspected locally; it was not sent to Meta for this validation.

## Stale relationship recovery
- Focused backend/API/procurement suite: 35 passed.
- Frontend unit tests: 19 passed; TypeScript and production build passed.
- Real-backend retail browser regression: passed, including confirmation buttons becoming enabled after the final mapping confirmation without another discovery click.
- Legacy stale-link UI regression verifies the enabled refresh action, accurate status message, and continued approval blocking until evidence is current.
- Evidence refresh creates/revises proposals only. Relationship approval remains an explicit human action.

## Analytics context and review explanations
- Full Python suite: 126 passed, 2 documented skips; one dependency deprecation warning.
- Frontend: 22 unit tests passed; TypeScript and production build passed.
- Real-backend retail browser regression passed: reviewed inventory names reach the chart; missing currency leaves revenue unavailable; the review link opens the Sales mapping; the GBP shortcut fills a draft without saving; explicit confirmation produces the expected GBP revenue.
- Product-name enrichment does not infer sales currency, costs, stock quantities or thresholds from inventory. Missing reorder rules remain unassessed.

## Demand-based replenishment
- Full Python suite: 141 passed, 2 documented skips, one dependency deprecation warning.
- Frontend: 25 unit tests; TypeScript and production build passed.
- Real-backend Playwright: 4 passed, 2 live-Meta browser cases skipped. New scenario verifies 40 units over 10 calendar days = 4/day, 8 on hand = 2 days remaining, and a 20-unit recommendation for the selected assumptions. Preview creates no policy/action; explicit policy review enables a pending GBP 60 proposal with no output until approval.
- Backend coverage includes insufficient/undated/zero demand, mismatched units, historical/future dates, fractional stock rounding, source-threshold precedence, duplicate source views, policy concurrency/auth, actual Excel planning lineage, immutable originals, and invalidation of pending actions after policy changes.
- No new Meta calls were needed to validate demand arithmetic. This feature uses deterministic reviewed source data and exposes its results through the existing agent tool.

## Preview feedback recovery
- Frontend component/unit tests: 31 passed; TypeScript and production build passed.
- Regressions verify unchanged-result feedback, an explicit calculating state, visible request errors, no implicit policy writes, blocked confirmation without eligible history, and snapshot acknowledgement reset when assumptions change.
- This change was verified against source and synthetic mocked component fixtures. Live browser reproduction was blocked by the browser origin-permission gate; no live-page verification is claimed for this fix.

## Meta completion recovery — 2026-11-03

- Full offline Python suite: **153 passed, 2 documented skips**, one existing FastAPI/Starlette dependency warning. Focused provider/mapping suite: **42 passed**.
- New regressions reproduce length-truncated structured replies and tool calls, check the single larger-budget retry, reject malformed messages, distinguish other stop reasons, stop on authentication failure, and verify atomic persistence when a later batch recovers or exhausts its retry. Nine failing regression cases were reproduced before the fix.
- Live official Meta mapping on the public fictional electronics files: **passed in 86.3 seconds**, using an isolated temporary store. All three business tables matched the fixture's exact field mappings; three administrative tables remained `unknown`. Three completion calls finished normally, including one semantic validation repair; the live run did not need a length retry. Length recovery is covered with controlled transport responses in the regression suite.
- No mappings were confirmed, no operational records or purchase outputs were created, and uploaded fixture originals were verified byte-for-byte. The application's active workspace was not used by this live check.
- Sanitized usage/finish-reason evidence: [validation/meta-completion-recovery-live.json](validation/meta-completion-recovery-live.json). No provider content, private reasoning or credentials are stored in this evidence.
- This is service-level live verification. Browser origin permission remains a separate restriction; no live-page verification is claimed.
