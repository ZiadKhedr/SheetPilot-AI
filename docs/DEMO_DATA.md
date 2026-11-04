# SheetPilot AI — synthetic company fixtures

For the larger EGP recording scenario, use the separate [Nile Circuit demo pack](../demo_pack/README.md). It contains three core upload files (6,000 sales lines, 1,200 orders, 40 SKUs and eight suppliers), six challenge/showcase workbooks, a deterministic Python generator, independent and isolated-application validation, exact expected results, and a [6½-minute recording guide](../demo_pack/RECORDING_GUIDE.md). Start with a fresh workspace and upload only its core files. The [ZIP](../demo_pack/SheetPilot_Demo_Pack.zip) contains the complete pack. The regression fixtures below remain separate.

All businesses, transactions, addresses, and supplier contacts in these files are fictional. Email domains use `example.invalid` and cannot be delivered. No fixture contains an API key or real company data.

Regenerate the six workbooks and fixture oracle from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py
```

The generator overwrites only the requested output directory (default `demo_data/`). Fixture values are reproducible. ZIP timestamps may differ between generations.

## What these assets verify

The companies use different file names, sheet names, languages, row offsets, and column offsets. All main worksheets have merged title cells, a business table, then a blank gap and an unrelated administrative table. Each workbook also has a hidden notes worksheet with formulas. The primary revenue columns contain actual numeric values, so analytics never depend on calculating an Excel formula.

The manifest at `demo_data/manifest.json` is an **explicit test oracle and human review guide**, not a production mapping algorithm. Application inference must not import its expected mappings. A live Meta or manual mapping workflow should independently propose/review the same source fields.

Column indices in the manifest are absolute, 1-based worksheet indices. File metadata includes the main `sheet`, `header_row`, `ref`, original column labels, canonical field map, administrative region, and hidden sheet name.

## Company A: Circuit Harbor Electronics

Currency: **USD**. Quantities are individual units.

| File | Business sheet | Header row | Business range |
|---|---|---:|---|
| `company_a/Sales.xlsx` | Transactions | 5 | A5:H15 |
| `company_a/Inventory.xlsx` | Warehouse | 3 | B3:I7 |
| `company_a/Suppliers.xlsx` | Partners | 4 | C4:H8 |

Sales fields use labels such as `Item Code`, `Units Sold`, `Selling Price`, and `Net Sales`. Inventory uses `SKU`, `Available Units`, `Reorder At`, and `Purchase Cost`. Suppliers use `Product Reference`, `Trading Name`, and `Supply Price`.

Expected reviewed analytics:

| Metric | Result |
|---|---:|
| Raw sales rows | 10 |
| Exact duplicate extra rows | 1 |
| Missing-product rows quarantined | 1 |
| Valid unique sales rows | 8 |
| Reviewed revenue | USD 1,258.00 |
| Raw revenue before quality policy | USD 1,717.00 |
| Units sold | 31 |
| Valid inventory products | 4 |
| Current inventory quantity | 34 |
| Inventory value at unit cost | USD 780.00 |
| Low-stock products | 3 |
| Replenishment quantity | 82 |
| Replenishment cost | USD 1,809.00 |

| Product | Current | Reorder below | Target | Draft quantity | Unit cost | Line cost | Supplier |
|---|---:|---:|---:|---:|---:|---:|---|
| A001 — USB-C Hub | 8 | 10 | 30 | 22 | 22.00 | 484.00 | S01 |
| A002 — 24-inch Monitor | 2 | 5 | 12 | 10 | 110.00 | 1,100.00 | S02 |
| A004 — HDMI Cable | 0 | 15 | 50 | 50 | 4.50 | 225.00 | S03 |

A003 — Keyboard has 24 units and a reorder threshold of 8; it must not be ordered by this threshold policy.

Product revenue: A001 270.00; A002 540.00; A003 280.00; A004 168.00 USD.

## Company B: مائدة للمطاعم والتوريد

Currency: **EGP**. Each SKU uses its named pack size as its unit: flour is a 25 kg bag, oil a 5 L container, tomatoes a crate, rice a 10 kg bag. Do not add unlike physical weights or convert packs without explicit business rules. The dashboard's total quantity is an item-count sum, not kilograms or litres.

| File | Business sheet | Header row | Business range |
|---|---|---:|---|
| `company_b/Orders.xlsx` | طلبات المطاعم | 7 | B7:I17 |
| `company_b/Stock.xlsx` | المخزن | 4 | D4:K8 |
| `company_b/Vendors.xlsx` | جهات التوريد | 6 | A6:F10 |

The worksheets use right-to-left display. Orders identify products with `مرجع المنتج`; stock uses `رمز المادة`; vendor quotes use `كود المادة الغذائية`. These labels should map to the same product identifier field after evidence and review. Other labels include `الوحدات المباعة`, `قيمة الطلب`, `الرصيد الحالي`, `حد إعادة الطلب`, and `الرصيد المستهدف`.

Expected reviewed analytics:

| Metric | Result |
|---|---:|
| Raw sales rows | 10 |
| Exact duplicate extra rows | 1 |
| Missing-product rows quarantined | 1 |
| Valid unique sales rows | 8 |
| Reviewed revenue | EGP 11,890.00 |
| Raw revenue before quality policy | EGP 14,650.00 |
| Units sold | 40 |
| Valid inventory products | 4 |
| Current inventory quantity | 24 |
| Inventory value at unit cost | EGP 4,230.00 |
| Low-stock products | 3 |
| Replenishment quantity | 47 |
| Replenishment cost | EGP 12,630.00 |

| Product | Current | Reorder below | Target | Draft quantity | Unit cost | Line cost | Supplier |
|---|---:|---:|---:|---:|---:|---:|---|
| R01 — دقيق | 6 | 10 | 25 | 19 | 260.00 | 4,940.00 | V10 |
| R02 — زيت | 3 | 8 | 20 | 17 | 200.00 | 3,400.00 | V11 |
| R04 — أرز | 1 | 4 | 12 | 11 | 390.00 | 4,290.00 | V10 |

R03 — طماطم has 14 units and a reorder threshold of 5; it must not be ordered.

Product revenue: R01 3,840.00; R02 3,250.00; R03 1,440.00; R04 3,360.00 EGP.

## Data-quality review policy

These results apply the following **explicit fixture policy**, and must not be represented as unquestioned cleaning of arbitrary real-company records:

1. Exact duplicate rows include the same order identifier and every source value. Flag the extra occurrence and use the reviewed duplicate policy to exclude it from the normalized analytics copy. Different order identifiers remain separate sales even when their products, amounts, and dates match.
2. The final sales row has no product identifier. Quarantine it from joined analytics pending correction.
3. The third inventory product stores its current stock as a numeric string: `"24"` in Company A and `"14"` in Company B. Validate the conversion for the operational mirror; do not rewrite the source cell.
4. The third supplier quote has no optional email address. Warn, but this does not block generation of a local PO draft.
5. Historical sales must not be subtracted from a current stock snapshot. Replenish only when `stock_quantity < reorder_point`, with quantity `target_stock - stock_quantity`.
6. Exclude administrative tables and hidden notes from business semantics unless a user deliberately maps them. Preserve them when creating a workbook copy.

Physical issue rows:

| Company | Duplicate sales row | Missing-product sales row | Numeric-text inventory row | Missing optional email row |
|---|---:|---:|---:|---:|
| A | 14 | 15 | 6 | 7 |
| B | 16 | 17 | 7 | 9 |

## Relationship evidence

For each company, the four distinct valid sales product identifiers overlap all four inventory product identifiers. All four inventory product identifiers also appear in supplier quotes. This yields 4 matching keys and 100% valid-left-key coverage for both proposed product joins.

Supplier identifiers are deliberately nonunique in the quotes table: a supplier can supply multiple products. Match procurement quotes using **product_id and supplier_id**, not supplier_id alone. A supplier-only join would incorrectly multiply inventory records.

Company A's three low-stock products have three suppliers. Company B has two suppliers for three low-stock lines; grouping by supplier yields two purchase-order groups, with V10 totaling EGP 9,230.00 and V11 totaling EGP 3,400.00.

Companies are separate workspaces. Never combine USD and EGP into one revenue number or infer cross-company relationships.
