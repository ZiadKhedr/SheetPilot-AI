# SheetPilot AI
### Your Spreadsheets. Your AI Workforce.

A working local hackathon application that connects unfamiliar Excel workbooks to a reviewed operational mirror, business dashboards, Meta-powered specialist tools, human approvals, and downloadable purchase-order workbooks.

For reviewers: [project description](docs/JUDGE_DESCRIPTION.md), [architecture](ARCHITECTURE.md), [demo script](docs/DEMO_SCRIPT.md), [test results](docs/TEST_RESULTS.md) and [known limitations](docs/KNOWN_LIMITATIONS.md).

**No migration away from Excel. No invented KPIs. No automatic source edits.**

## Clean setup

Requirements: Python 3.10+ (tested on 3.12), Node 22.19+ (tested on 24), and pnpm 11.

Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[app,dev]"
Copy-Item .env.example .env
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
.\scripts\start.ps1
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[app,dev]'
cp .env.example .env
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
sh scripts/start.sh
```

Edit .env locally to set `MODEL_API_KEY`. The key stays on the server. In Connections, verify the provider; both a model-catalog request and an actual structured generation must succeed for Meta to show as connected.

Workspace data and immutable uploaded originals live in ignored `.data/` (or `SHEETPILOT_DATA_DIR`). Back up this folder with the server stopped; Git does not back it up. If storage becomes unavailable, restore the folder and click **Retry connection**.

Keep this MVP on localhost. Optional `SHEETPILOT_ACCESS_TOKEN` enables owner authentication and `SHEETPILOT_READ_TOKEN` grants GET-only access. Enter those workspace tokens (not the Meta key) in Connections when configured. This is a local single-operator MVP, not a production identity/tenant system.

For frontend development, run the backend on 8000 and `pnpm --dir frontend dev` on 5173. Vite proxies /api to FastAPI.

For a clean demonstration on a prepared machine, choose a new data directory in the current terminal before starting. For example, use `$env:SHEETPILOT_DATA_DIR="work/demo-$(Get-Date -Format yyyyMMdd-HHmmss)"` in PowerShell. Existing workspaces stay in their own directories. If you configure only a reader token, all writes are disabled. Owner and reader credentials must differ.

## The complete workflow

1. Create a workspace, upload the Sales, Inventory and Suppliers workbooks, or load one of the two fictional demo companies.
2. Explore worksheet ranges, proposed headers, hidden sheets, merged cells and formula expressions. Add a rectangular source region manually if needed.
3. Choose **Analyze with Meta**. Only bounded table summaries and small samples are sent. The key stays on the server.
4. Review each proposed entity/column meaning and confirm the business tables. Exclude unrelated tables. Unmapped extra columns remain custom fields.
5. Discover relationships. Inspect actual identifier overlaps and explicitly confirm links.
6. Open Overview or Business Analytics. Every metric is computed from reviewed records, with currency kept explicit.
7. Ask Meta to analyze sales/inventory and draft purchase orders. The Orchestrator calls typed Sales, Inventory and Procurement tools.
8. Inspect line items, validation checks, and source versions in Approval Center. Approve or reject.
9. Approval creates an additional real Excel workbook. Download it and inspect Purchase Orders, Source Trace and Execution. Rejection generates nothing.
10. Activity Timeline records actual processing, reviews, tools, approvals, failures and executions.

**Guided check** and **Label suggestions · no AI** are explicitly deterministic alternatives, never represented as live AI.

On a sales mapping, expand **Preview mapped rows** to see your field choices alongside original row numbers. On Overview, choose **Inspect sales rows** under revenue to find the exact workbook, sheet and amount cell or quantity × unit-price cells. In Agent Workspace, try “What is the reviewed sales revenue for product ID A001 alone, across all dates?” The Electronics answer is USD 270.00. The tool trace shows the selected scope and contributing evidence.

When upgrading a previously reviewed workspace that uses fractional-cent supplier prices, confirm the supplier mapping again before drafting. This reloads the original quote precision into the derived records.

## Demo datasets

| Business | Schemas | Expected reviewed revenue | Stock | Low-stock | Expected purchase draft |
|---|---|---:|---:|---:|---:|
| Electronics | English labels, offset rows/columns | USD 1,258.00 | 34 | 3 | 82 units / USD 1,809.00 |
| Restaurant supply | Different Arabic labels/layouts | EGP 11,890.00 | 24 | 3 | 47 units / EGP 12,630.00 |

Both contain exact duplicate sales, a missing product identifier, numeric text, admin tables, hidden sheets and formulas. Totals are independent fixture expectations, not values imported by production analytics. See [demo guide](docs/DEMO_DATA.md); regenerate with `python scripts/generate_demo_data.py`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
pnpm --dir frontend test
pnpm --dir frontend build
```

Live tests use the actual Meta account and may consume API credits:

```powershell
$env:SHEETPILOT_LIVE_META_TEST="1"
.\.venv\Scripts\python.exe -m pytest tests_app/test_live_meta.py -v
$env:SHEETPILOT_E2E_META="1"
$env:PLAYWRIGHT_CHANNEL="msedge"
pnpm --dir frontend e2e
```

For Playwright's bundled Chromium instead of installed Edge, omit PLAYWRIGHT_CHANNEL and install its browser once: `pnpm --dir frontend exec playwright install chromium`.

The browser suite starts a fresh backend on 8010 with a unique database under `work/e2e/`. With the live flag it uploads both datasets through the UI, performs real Meta mapping and agent calls, confirms mappings/relationships, approves, downloads Excel and checks the timeline. An independent guided browser test exercises approval and download without an API key. Screenshots and live downloads are under `frontend/test-results/`. After a live browser run, use `.\.venv\Scripts\python.exe scripts/validate_downloads.py` to compare both downloads with the fictional company oracles.

On Windows, the symlink test is skipped if the OS account lacks symlink privileges.

Actual results and verification limits are in [TEST_RESULTS.md](docs/TEST_RESULTS.md).

## Docker Compose

```sh
docker compose up --build
```

Open http://127.0.0.1:8000. Compose reads .env for the server-side key and uses a named volume for SQLite, immutable uploads and outputs. The Dockerfile builds React separately and runs Python as a non-root user. .env, .data, test artifacts and local dependencies are excluded from the image build context.

Compose configuration is validated. Container build/start was not executed on this host because the Docker engine is stopped; local production startup and browser workflows were exercised.

## Code map

- `src/excel_intelligence/`: preserved Phase 1 analyzer and CLI
- `src/sheetpilot/`: API, storage, ingestion, semantics, analytics, agents, approvals
- `frontend/`: React/TypeScript/Tailwind, Radix dialogs, Recharts, unit and browser tests
- `demo_data/`: six fictional workbooks and independent test oracle
- `tests/`, `tests_app/`: analyzer and app regression/integration tests
- `.data/`: ignored runtime data, source snapshots and generated workbooks
- `docs/`: architecture details, test evidence, limitations, demo script and judge description

The original CLI is still available: `excel-analyze workbook.xlsx -o report.json`. Its detailed contract is preserved in [PHASE1_CLI.md](docs/PHASE1_CLI.md).

## Limits

Unfamiliar structures are proposals, not guaranteed comprehension. Irregular forms may need manual region selection. Formula values are never calculated; mapped formula/error values require review and are excluded from operational calculations. Ambiguous numeric text with commas is flagged rather than guessed. Exact duplicate source rows are excluded from the derived mirror and surfaced as quality issues.

Money uses Decimal; currencies are never silently combined or converted. Stock is an on-hand snapshot: historical sales are not subtracted again. Target stock defaults to twice the reorder threshold only when no target field is mapped. Purchase orders do not increase on-hand inventory.

See [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md). No OneDrive/SharePoint sync, supplier emailing, multi-user SSO, or perfect arbitrary-file comprehension is claimed.
