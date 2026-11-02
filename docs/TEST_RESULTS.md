# SheetPilot AI — verification evidence

Date: 2026-11-02. Local Windows host. Python 3.12.14, pytest 8.4.2, OpenPyXL 3.1.5, Pydantic 2.14.1, Node 24.22.1, Vite 7.3.7, Vitest 3.2.7, installed Microsoft Edge via Playwright.

## Original baseline
57 passed, 1 skipped before app changes. The skipped case requires symlink creation privileges. A restricted first attempt also failed the hard-link case; it passed when rerun with normal filesystem permissions.

## Current Python suite
**95 passed, 2 skipped, 1 dependency warning** in 13.52 seconds. The output is saved in outputs/python-test-results.txt and outputs/verification-summary.json.

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

Screenshots and downloaded workbooks are in outputs/. They show actual execution data, not a designed mockup. A first browser attempt failed to launch due to restricted temporary-folder permissions; a first test-server attempt had an invalid Windows relative command path. Both were corrected before the successful run.

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
scripts/check_secrets.py confirms the configured Meta key is absent from tracked working files and historical Git blobs. .env, .data, work/, .venv and node_modules are ignored. Screenshots and committed demo artifacts contain fictional data only.

## Remaining non-MVP validation
Authorized real-company workbook benchmarks, hard ingestion worker isolation, OS-enforced runtime/memory quotas, production identity/tenant controls, cloud synchronization and container-engine execution remain outside verified scope. See KNOWN_LIMITATIONS.md.
