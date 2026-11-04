# Recording guide

Use a new workspace named Nile Circuit Distribution. Upload only core/01_Commerce.xlsx, core/02_Warehouse.xlsx and core/03_Supplier_Quotes.xlsx. Default as-of date: 2026-11-03. These are historical snapshot facts. Set the demand estimate stock date to 2026-11-03 if needed. Use an already configured real Meta provider for Meta footage. Generation and validation do not configure or call Meta. Guided tools are labeled no AI.

## Main story (6 minutes 30 seconds)

| Time | Screen and action | Evidence and concise narration |
|---|---|---|
| 0:00–0:40 | Excel File Manager: upload the three core files. Structure Explorer: open Sales Lines, Orders, Current Stock and Supplier Quotes. | Show offset headers and source coordinates. Exclude the hidden Internal Notes sheet, and exclude title/subtitle rows above each manifest header. No administrative table belongs in analytics. |
| 0:40–2:00 | Mapping Review: request actual Meta proposals, then inspect each mapping. | Net Selling Price is unit_price, List Price is list_unit_price, Discount per Unit is unit_discount, Net Line Amount is revenue. Physical On Hand is stock_quantity; opening and reserved quantities are separate. Orders is order-header grain; Invoice Total maps to order_total. Leave Sales Channel, Campaign Code, Line Notes, Quote Reference and Quote Notes as preserved custom columns. Confirm the four operational mappings. |
| 2:00–2:30 | Mapping Review: discover relationships; review three exact links. | Sales Lines–Orders on order_id (many-to-one), Sales Lines–Current Stock on product_id (many-to-one), Current Stock–Supplier Quotes on product_id (one-to-one). Check entity, field, exact overlap, cardinality and unmatched IDs. Do not accept every candidate. Dates and descriptions now flow through reviewed joins. |
| 2:30–3:20 | Overview, then Business Analytics. | Revenue EGP 16307447.00, 21462 units, 6,000 sales lines, 1,200 headers and 40 stock SKUs. Order totals do not double revenue. Show seven-day comparison anchored to latest reviewed sale: 2026-10-28–2026-11-03 versus 2026-10-21–2026-10-27. NC-002 +200%, NC-003 -60%. Show NC-001 at 20/day and 0.9 days cover, plus NC-004 out of stock. |
| 3:20–4:25 | Agent Workspace: select Meta mode and Review the business. | Wait for the real run. Show Sales Agent sales_analysis and sales_comparison, Inventory Agent inventory_analysis, Procurement Agent procurement_review: four sequential tool checks, actual status/runtime/work counts/source evidence. Download the text work report. This review creates no purchase proposal. Narration: Meta selects typed tools; Python calculates the numbers. |
| 4:25–5:25 | Agent Workspace: Prepare purchase drafts in Meta mode. Open Approval Center. | Show actual inventory_analysis and draft_purchase_orders steps. Inspect the pending proposal, supplier IDs, currency, quantity and sources. With commercial policy disabled NC-001 is 162 units, EGP 44,550.00. Quoted packs/MOQ alone do not round it. Full core proposal is EGP 906550.00; exact lines and supplier subtotals are in expected_results.json. |
| 5:25–6:30 | Approval Center: approve once; download. Inspect Purchase Orders, Source Trace and Execution sheets. Activity Timeline: show real execution. | The approved output is an additional workbook. Reopen the same completed proposal: the same output is returned, with no second execution. Download/open the original warehouse file: NC-001 remains 18. Narration: the human approves workbook generation; no supplier order is sent and no receipt is recorded. |

Do not promise a fixed provider response time. Cut quiet waiting in editing without fabricating progress or logs. Only describe reconnection/recoverability if actually observed in a real run. A worker interruption requires explicit review/retry; no promise of automatic replay.

## Three paste-ready custom requests (Meta mode)

1. Compare NC-002 and NC-003 separately over the latest seven calendar days versus the preceding seven. Use sales_comparison with exact product IDs and show source evidence.
2. Use inventory_analysis for NC-001. Explain its dated demand, stock cover, source thresholds and quantity basis.
3. Use inventory_analysis and draft_purchase_orders for NC-001 only. Prepare a pending purchase draft with quantity, supplier, EGP total and sources for my review.

The comparison tool accepts one product scope per call. The first request requires separate scoped calls. If a provider request fails, show its actual error, review the connection and explicitly retry. Guided/no-AI results must never be presented as Meta results.

## Optional A: data quality and reversible repair (fresh workspace)

Upload only challenges/A_quality/Quality_Repairs.xlsx. Map Sales with explicit sale_date. B5:H5 and B6:H6 are exact duplicates, including invoice ID. Another DQ-A order is a valid independent sale. C8 has no product ID and remains excluded. D12 `1200` is already usable numeric text.

Data quality repairs: preview D9 as thousands_comma (`1,200` to 1200), approve. Preview E10 as decimal_comma (`25,50` to 25.50), approve. Preview F11 as date_dmy (03/11/2026 to 2026-11-03), approve. Revenue stages: EGP 1750.00 → 4150.00 → 4201.00 → 4201.00. Dated trend revenue stages: 1700.00 → 4100.00 → 4151.00 → 4201.00. An invalid date retains revenue but omits it from trends. Reverse the three corrections in reverse order using preview and human approval; revenue returns to 1750.00, with original files preserved. No formula repair or unsupported identifier guess is involved.

## Optional B: demand ordering policy (fresh workspace)

Upload only challenges/B_demand/Demand_Policy.xlsx, confirm Sales, Current Stock and Supplier Quotes, then confirm the two exact product links in the manifest. Business Analytics: Change settings, stock date 2026-11-03; More settings: 30-day lookback, 7 delivery days, 3 safety days, 14 extra stock days. Update estimate previews only. DP-001 has 150 units / 30 days = 5/day, stock 6, cover 1.2 days, reorder 50, target 120 and top-up 114. Explicitly acknowledge comparable base units and alignment with the physical stock snapshot, then Save ordering settings. Only then prepare purchase drafts and separately approve output. Source thresholds take precedence wherever present. Call this a trailing-average scenario, never an ML forecast or a guaranteed stockout date.

## Optional C: supplier terms and incoming orders (fresh workspace)

Upload only challenges/C_commercial/Supplier_Terms.xlsx. Confirm its three mappings and two exact product links. Open Supplier planning. Set planning date 2026-11-03 and horizon 14. Review and enter ALL three SKU rules from incoming_order_entry_guide.json; select the matching quote, per-base-unit prices, units and EGP. Preview, acknowledge and save. NC-001 changes from 162 to 168 units (14 packs of 12), EGP 46,200.00.

Incoming orders: explicitly enter and confirm the 48-unit unreceived external order in the JSON guide, expected 2026-11-06. Position becomes 18 + 48 = 66, below reorder 70. Net requirement 180 - 66 = 114; ten packs produce 120 units, EGP 33,000.00. Optional overdue, cancelled and day-15 examples do not count. A generated workbook or imported purchases table does not record incoming stock. Save all rule/receipt changes before preparing a fresh proposal; data changes can invalidate a pending one. Use an NC-001-scoped custom request to isolate the hero line if desired.

## Optional D: new stock snapshot (after purchase footage or fresh core workspace)

File Manager: select the original warehouse file, choose New snapshot and upload challenges/D_versions/02_Warehouse_v2.xlsx. Do not upload it as an independent active inventory file. Confirm the candidate mapping. Preview changes with product_id as the stable key, explicitly save the identifier/key review, then activate the candidate. Expected: 1 added (NC-041), 1 removed (NC-040), 3 changed (NC-001/002/003), 36 unchanged. Row movement alone is unchanged. Only the active snapshot contributes; old originals remain downloadable. Review links against the new mapping. Previous findings/pending proposals may become stale. The added SKU intentionally lacks a quote until separately reviewed; do not continue core procurement claims after this update.

## Optional E/F: broader entities and Arabic mapping

E_mapping/Broader_Entities.xlsx is a small entity-preservation showcase in a separate workspace. Map products, customers, supplier_directory, purchases and payments to their own entities. Standalone sales revenue is zero, and no incoming order is created. It does not implement CRM, receivables or automatic purchase ingestion. A supplier directory cannot replace product-specific quotes. If showing this alongside a deliberately extended core workspace, retain inventory-to-sales enrichment and do not also confirm product-master-to-sales enrichment, which can create ambiguous inherited context.

F_arabic/Manara_Trading.xlsx belongs to a separate company/workspace, Manara Electronics Trading, with MN-/MNV- IDs and EGP. Confirm the Arabic tables and two exact product links. Its expected revenue is EGP 31500.00. Do not load a translated second copy of core data into the main workspace.
