# Nile Circuit sample workbooks

Synthetic EGP business data for evaluating SheetPilot. Historical snapshot: 2026-11-03.

## Try the core workflow

1. Create a fresh workspace and upload the three workbooks in `core/`.
2. Review the Sales Lines, Orders, Current Stock and Supplier Quotes mappings. Exclude Internal Notes and title rows above the headers.
3. Review exact relationships: Sales Lines to Orders on `order_id`, Sales Lines to Current Stock on `product_id`, and Current Stock to Supplier Quotes on `product_id`.
4. Inspect analytics, run an agent task, then review a pending purchase proposal before approving an additional Excel output.

| Fixture expectation | Result |
| --- | ---: |
| Sales lines | 6,000 |
| Order headers | 1,200 |
| Stock SKUs | 40 |
| Suppliers | 8 |
| Reviewed revenue | EGP 16307447.00 |
| Purchase draft with source thresholds and no commercial policy | EGP 906550.00 |

These are independent fixture expectations. The application calculates results from reviewed workbooks. `mapping_manifest.json` records source coordinates and required links; `expected_results.json` contains exact calculations and stages. Neither file grants application approval.

## Additional evaluation files

| Folder | Purpose | Workspace |
| --- | --- | --- |
| `challenges/A_quality/` | Numeric/date repair, duplicates and missing identifiers | Fresh |
| `challenges/B_demand/` | Reviewed demand-based ordering settings | Fresh |
| `challenges/C_commercial/` | Supplier terms and separately entered incoming orders | Fresh |
| `challenges/D_versions/` | Stable-key stock snapshot comparison | Core workspace: use New snapshot on the original warehouse workbook |
| `optional/E_mapping/` | Products, customers, supplier directory, purchases and payments | Fresh |
| `optional/F_arabic/` | Independent Arabic company | Fresh |

For demand and supplier planning, use the historical snapshot date above. Supplier-order entry values are in `challenges/C_commercial/incoming_order_entry_guide.json`. Review and save them separately in the app. Imported purchase rows and generated workbooks do not record incoming stock.

## Reproduce and validate

Requires Python 3.10+ and openpyxl 3.1+. From this folder:

```sh
python generate_demo_pack.py --as-of 2026-11-03 --seed 42 --output-dir ./generated
python validate_demo_pack.py --pack-dir ./generated --reproduce
```

From the repository root with app dependencies installed (Windows):

```powershell
.venv/Scripts/python demo_pack/validate_demo_pack.py --pack-dir demo_pack --app --reproduce
```

On macOS/Linux, use `.venv/bin/python`. Validation writes `VALIDATION_RESULTS.md` and `validation_results.json`. Application checks use isolated temporary stores and deterministic services; these scripts do not configure or call Meta.

All business values are literals. Decimal calculations round money to cents; per-base-unit quotes may retain six decimal places. XLSX timestamps are stable for byte reproducibility. All businesses and contacts are fictional; contact domains use `example.invalid`.
