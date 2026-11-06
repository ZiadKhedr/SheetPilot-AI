# SheetPilot AI

**Your Spreadsheets. Your AI Workforce.**

Turn business Excel files into reviewed analytics and human-approved purchase orders. SheetPilot AI uses the official Meta Model API to propose business mappings and coordinate Sales, Inventory and Procurement tools, while deterministic Python calculates quantities and money.

Built for the Meta AI Hackathon with React, TypeScript, FastAPI and SQLite.

[Project description](docs/JUDGE_DESCRIPTION.md) · [Architecture](ARCHITECTURE.md) · [Verification results](docs/TEST_RESULTS.md) · [Known limitations](docs/KNOWN_LIMITATIONS.md)

## What it does

- **Understand unfamiliar workbooks:** inspect worksheets, table regions, headers, formulas and hidden sheets, including English and Arabic layouts.
- **Review Meta proposals:** confirm business entities, column meanings and relationships backed by identifier overlap.
- **Explore business performance:** view revenue, sales trends, inventory and stock-planning calculations from reviewed records, with links to source cells.
- **Work with specialist agents:** ask Meta to select typed Sales, Inventory and Procurement tools and inspect their execution results.
- **Approve an Excel output:** review a pending purchase proposal, approve or reject it, and download an additional workbook with Purchase Orders, Source Trace and Execution sheets.
- **Recover and update workspaces:** download validated installation backups, restore into isolated storage, follow a backend-derived checklist, compare workbook versions using reviewed stable keys, and activate one snapshot at a time.
- **Repair with review:** preview numeric/date interpretations and exact identifier reconciliation, approve a derived correction revision, or preview an audited reversal while preserving originals.
- **Reconnect to saved agent work:** durable local jobs retain actual progress after reload, support safe cancellation and explicit context-checked retries, and never restart provider work on reconnect.
- **Plan supplier purchases:** review delivery times, explicit base units, pack sizes and minimum quantities; separately record incoming supplier orders and inspect the full deterministic purchase calculation.

See [workspace lifecycle](docs/WORKSPACE_LIFECYCLE.md), [supplier planning](docs/SUPPLIER_PLANNING.md) and [agent jobs](docs/AGENT_WORK.md) for workflows and boundaries.

Original workbooks remain unchanged. Mapping and relationship review precede operational use; generating a purchase-order workbook requires human approval. Source hashes, deterministic calculations, idempotent execution and an audit timeline make the result traceable.

## Quick start

### Requirements

- Python 3.10+; tested with Python 3.12.
- Node.js 22.19+; tested with Node.js 24.
- pnpm 11.
- A Meta Model API key with access to the configured model for AI features. The tested default is `muse-spark-1.3`.

### 1. Clone and install

```sh
git clone https://github.com/ZiadKhedr/SheetPilot-AI.git
cd SheetPilot-AI
```

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[app,dev]"
Copy-Item .env.example .env
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[app,dev]'
cp .env.example .env
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
```

### 2. Configure Meta

Edit the new `.env` file and set:

```dotenv
MODEL_API_KEY=your_meta_api_key
META_MODEL=muse-spark-1.3
```

The client uses the official `https://api.meta.ai/v1` endpoint. Keep the key in the server environment or ignored `.env`; never put it in frontend code or the browser UI. Meta receives bounded table summaries and small source samples for mapping, rather than workbook binaries. See [Meta integration](docs/META_API.md) for details.

### 3. Start the app

**Windows PowerShell**

```powershell
.\scripts\start.ps1
```

If PowerShell blocks script execution, start the server directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port 8000
```

**macOS / Linux**

```sh
sh scripts/start.sh
```

Open [SheetPilot AI](http://127.0.0.1:8000). FastAPI serves the built frontend and API together. In **Connections**, verify Meta: both the model-catalog request and a structured generation must succeed for the provider to show as connected. Stop the server with Ctrl+C.

## Try the complete workflow

1. Create a workspace and load a fictional demo company, or upload its three workbooks from `demo_data/`.
2. Open **Structure Explorer** to inspect detected tables and source ranges.
3. In **Mapping Review**, choose **Analyze with Meta**, inspect the proposed meanings and mapped-row previews, then confirm the business tables. Exclude unrelated tables.
4. Discover relationships, review identifier-overlap evidence and confirm the appropriate links.
5. Open **Overview** or **Business Analytics**. Use **Inspect sales rows** to trace revenue to original workbook cells.
6. In **Agent Workspace**, ask: “Analyze inventory and draft purchase orders for all low-stock products.” Inspect the specialist tool results and pending proposal.
7. In **Approval Center**, review quantities, costs, validations and source versions. Approve to generate and download the workbook, or reject to generate no output.
8. Open **Activity Timeline** to inspect the recorded reviews, agent runs, approval and execution.

For a scoped sales example with the Electronics dataset, ask: “What is the reviewed sales revenue for product ID A001 alone, across all dates?” Its fixture expectation is USD 270.00; the sales tool exposes the contributing source rows.

**Label suggestions · no AI** and **Guided check** are deterministic alternatives available without a Meta key. They are labeled separately from Meta-generated results.

## Included demo datasets

| Fictional business | Workbook layout | Reviewed revenue | Low-stock products | Purchase draft |
| --- | --- | ---: | ---: | ---: |
| Electronics distribution | English labels, offset headers and tables | USD 1,258.00 | 3 | 82 units / USD 1,809.00 |
| Restaurant supply | Arabic labels and different layouts | EGP 11,890.00 | 3 | 47 units / EGP 12,630.00 |

Both datasets include duplicate rows, missing identifiers, numeric text, unrelated tables, hidden sheets and formulas. These figures are independent fixture expectations; the application calculates its results from reviewed source data. See the [dataset guide](docs/DEMO_DATA.md).

For a larger EGP dataset, the [Nile Circuit demo pack](demo_pack/README.md) contains 6,000 sales lines, 1,200 orders, 40 SKUs and eight suppliers, plus focused challenge workbooks. Upload its three `core/` workbooks into a fresh workspace. Its generator, exact expectations and isolated validation are included.

## Development and tests

For frontend development, keep the backend running on port 8000 and run `pnpm --dir frontend dev` in a second terminal. Vite serves the frontend on port 5173 and proxies `/api` to FastAPI.

Run backend tests using your virtual environment:

```powershell
# Windows
.\.venv\Scripts\python.exe -m pytest -q
```

```sh
# macOS / Linux
.venv/bin/python -m pytest -q
```

Run frontend checks and browser regressions:

```sh
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend exec playwright install chromium
pnpm --dir frontend e2e
```

Playwright starts a separate backend on port 8010 with an isolated data directory under `work/e2e/`. The default suite exercises the deterministic workflow; live Meta browser tests are opt-in. Browser artifacts are written to ignored `frontend/test-results/` and `frontend/playwright-report/`.

To run real-provider tests in **PowerShell** after configuring `.env`:

```powershell
$env:SHEETPILOT_LIVE_META_TEST="1"
.\.venv\Scripts\python.exe -m pytest tests_app/test_live_meta.py -v
$env:SHEETPILOT_E2E_META="1"
pnpm --dir frontend e2e
```

On macOS/Linux, use `SHEETPILOT_LIVE_META_TEST=1 .venv/bin/python -m pytest tests_app/test_live_meta.py -v` and `SHEETPILOT_E2E_META=1 pnpm --dir frontend e2e`.

Live tests call the actual provider and may consume API credits. To use installed Edge instead of bundled Chromium, set `PLAYWRIGHT_CHANNEL=msedge`. After a live browser run, run `scripts/validate_downloads.py` with the virtual-environment Python to inspect both downloaded workbooks against the demo expectations.

Recorded results, skips and verification boundaries are in [TEST_RESULTS.md](docs/TEST_RESULTS.md). Unit-test provider mocks are confined to tests.

## Configuration and storage

| Variable | Purpose | Default |
| --- | --- | --- |
| `MODEL_API_KEY` | Server-side Meta credential | Unset |
| `META_MODEL` | Meta model identifier | `muse-spark-1.3` |
| `SHEETPILOT_DATA_DIR` | SQLite, immutable uploads and generated workbooks | `.data` |
| `SHEETPILOT_ACCESS_TOKEN` | Optional owner token | Unset |
| `SHEETPILOT_READ_TOKEN` | Optional read-only token | Unset |

Keep this single-operator MVP on localhost. When workspace tokens are configured, enter them in **Connections**. Owner and reader tokens must differ; configuring only a reader token disables writes.

Runtime data is ignored by Git. Back up the entire data directory with the server stopped. If storage becomes unavailable, restore it before restarting and use **Retry connection**. Starting with no data directory initializes an empty database. For a fresh demo, select a different `SHEETPILOT_DATA_DIR` rather than deleting existing workspaces.

## Docker Compose

After creating `.env` and configuring the Meta key:

```sh
docker compose up --build
```

Open [SheetPilot AI](http://127.0.0.1:8000). Compose binds to loopback and persists SQLite and workbooks in a named volume. The Dockerfile builds the frontend and runs the Python app as a non-root user.

Compose configuration has been validated. Container build and startup have not been verified on the development host; native startup and browser workflows have been tested.

## Repository guide

| Path | Contents |
| --- | --- |
| `src/excel_intelligence/` | Offline, read-only workbook analyzer and CLI |
| `src/sheetpilot/` | FastAPI, Meta integration, SQLite, analytics, tools and approvals |
| `frontend/` | React/TypeScript interface, component tests and Playwright scenarios |
| `demo_data/` | Two fictional businesses and their expected results |
| `demo_pack/` | Larger EGP sample workbooks, expected results and reproducible validation |
| `tests/`, `tests_app/` | Analyzer and application regression tests |
| `scripts/` | Startup, demo generation and verification utilities |
| `docs/` | Technical guides, dataset instructions, test evidence and limitations |

The standalone analyzer remains available as `excel-analyze workbook.xlsx -o report.json`. See the [CLI guide](docs/PHASE1_CLI.md).

## Current boundaries

Unfamiliar layouts may require manual region selection and mapping review. Formula expressions are inspected but never executed or recalculated. Ambiguous numeric values and invalid required fields need review; exact duplicate rows are excluded from the operational mirror and reported as quality issues.

Money uses `Decimal`, and currencies stay separate. Inventory represents an on-hand snapshot; historical sales are not deducted again. Purchase-order generation leaves stock quantities unchanged. The app does not implement live OneDrive/SharePoint synchronization, supplier emailing or production multi-user identity and tenant controls.

See [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the full scope.
