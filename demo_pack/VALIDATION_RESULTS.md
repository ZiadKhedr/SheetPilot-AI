# Validation results

Result: PASS. 176,510 assertions against saved workbooks and their derived expectations.

Files: 9 normal XLSX workbooks. Largest full populated bounding grid: 72,048 cells. All workbook sizes are below 10 MiB. No formulas, macro projects or external links.

## Checks actually executed

- Saved XLSX readability, bounded grids, styling, literal cells, source coordinates and exact keys: passed.
- Independent saved-row arithmetic, coverage, comparison windows, history eligibility, risks, draft totals and version diff: passed.
- Same date/seed regenerate byte-identical workbooks, manifests, expectations and guides: passed.
- Isolated SheetPilot core ingestion, mapping, required joins, analytics, real guided jobs, pending approval, actual Excel and idempotency: passed.
- Isolated SheetPilot thousands/decimal/DMY repair previews, approvals, reversals and original hashes: passed.
- Isolated SheetPilot demand preview and reviewed policy supplies exact 50/120/114 thresholds and quantity: passed.
- Isolated SheetPilot all-SKU supplier review, 162/168/120 quantities, incoming exclusions, stale proposal and Decimal output: passed.
- Isolated SheetPilot candidate mapping, explicit stable-key review, exact diff and snapshot activation: passed.
- Isolated SheetPilot broader entity preservation and distinct Arabic-company deterministic analytics: passed.

## Application and provider boundaries

Application integration: passed.

Application checks use temporary isolated stores, explicit fixture reviews and real deterministic service functions/guided jobs. No existing application workspace database is opened or populated. All temporary action outputs, reports and review records are discarded, not packaged as a completed demo run.

Live Meta validation: not run. No provider is instantiated or called and no .env is read by these scripts. For Meta recording, use the real configured provider and show its actual outputs. This report establishes deterministic data/workflow correctness, not successful live Meta semantic proposals or browser footage.

Reproduce with `python validate_demo_pack.py --pack-dir <pack> --app` from the repository environment. Generator-only validation can run with openpyxl alone. No frontend or native Excel UI automation is claimed here.
