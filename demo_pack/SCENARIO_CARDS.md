# Scenario cards

Company: Nile Circuit Distribution. Historical snapshot: 2026-11-03. All quantities are base units (`each`).

## NC-001 — Wireless Earbuds

Urgent fast mover: 600 units / 30 days = 20 per day. Stock 18 gives 0.9 days. Core top-up 162 at EGP 275 = 44,550.00.

Sources: 02_Warehouse.xlsx 'Current Stock'!C6:N6; 01_Commerce.xlsx 'Sales Lines'!A62:L62, 'Sales Lines'!A120:L120, 'Sales Lines'!A188:L188, 'Orders'!B18:D18, 'Orders'!B30:D30, 'Orders'!B43:D43; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B8:M8.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-002 — USB-C Docking Station

Dock campaign growth: current seven-day quantity is three times previous, fixed EGP 1,800 net price. Revenue +200%.

Sources: 02_Warehouse.xlsx 'Current Stock'!C7:N7; 01_Commerce.xlsx 'Sales Lines'!A71:L71, 'Sales Lines'!A144:L144, 'Sales Lines'!A146:L146, 'Orders'!B20:D20, 'Orders'!B34:D34, 'Orders'!B35:D35; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B9:M9.

Responsible specialist/tool: Sales Agent / sales_comparison. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-003 — Portable SSD 1TB

SSD decline: current seven-day quantity is 40% of previous, fixed EGP 2,400 net price. Revenue -60%.

Sources: 02_Warehouse.xlsx 'Current Stock'!C8:N8; 01_Commerce.xlsx 'Sales Lines'!A31:L31, 'Sales Lines'!A96:L96, 'Sales Lines'!A151:L151, 'Orders'!B12:D12, 'Orders'!B25:D25, 'Orders'!B36:D36; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B10:M10.

Responsible specialist/tool: Sales Agent / sales_comparison. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-004 — 65W GaN Charger

Out of stock with 25 units per day of dated historical demand. Source top-up 300.

Sources: 02_Warehouse.xlsx 'Current Stock'!C9:N9; 01_Commerce.xlsx 'Sales Lines'!A15:L15, 'Sales Lines'!A76:L76, 'Sales Lines'!A209:L209, 'Orders'!B9:D9, 'Orders'!B21:D21, 'Orders'!B47:D47; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B11:M11.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-005 — Wireless Keyboard

Healthy stock: 600 physical units against 10 units per day. No source-rule purchase.

Sources: 02_Warehouse.xlsx 'Current Stock'!C10:N10; 01_Commerce.xlsx 'Sales Lines'!A25:L25, 'Sales Lines'!A133:L133, 'Sales Lines'!A202:L202, 'Orders'!B11:D11, 'Orders'!B32:D32, 'Orders'!B46:D46; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B12:M12.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-006 — Micro USB Cable

Overstocked slow seller: 1,000 physical units against one unit per day. No source-rule purchase.

Sources: 02_Warehouse.xlsx 'Current Stock'!C11:N11; 01_Commerce.xlsx 'Sales Lines'!A21:L21, 'Sales Lines'!A79:L79, 'Sales Lines'!A208:L208, 'Orders'!B10:D10, 'Orders'!B21:D21, 'Orders'!B47:D47; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B13:M13.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-007 — Legacy VGA Adapter

Older sales history, no last-30-day sales. No recent demand estimate or confirmed zero-demand claim.

Sources: 02_Warehouse.xlsx 'Current Stock'!C12:N12; 01_Commerce.xlsx 'Sales Lines'!A54:L54, 'Sales Lines'!A116:L116, 'Sales Lines'!A187:L187, 'Orders'!B16:D16, 'Orders'!B29:D29, 'Orders'!B43:D43; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B14:M14.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## NC-008 — Smart Travel Hub

New SKU: exactly two positive records on two days. Insufficient history cannot supply demand thresholds.

Sources: 02_Warehouse.xlsx 'Current Stock'!C13:N13; 01_Commerce.xlsx 'Sales Lines'!A5927:L5927, 'Sales Lines'!A5998:L5998, 'Orders'!B1191:D1191, 'Orders'!B1205:D1205; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B15:M15.

Responsible specialist/tool: Inventory Agent / inventory_analysis. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.

## Challenge source coordinates

A_quality / Quality_Repairs.xlsx, Sales: duplicate B5:H5 copied exactly to B6:H6. C8 is missing product ID. D9 requires thousands-comma interpretation. E10 requires decimal-comma interpretation. F11 requires DMY interpretation. D12 contains accepted numeric text `1200`.

B_demand / Demand_Policy.xlsx: DP-001 Sales A4:M33; Current Stock B6:K6; Supplier Quotes A8:L8. Inventory Agent uses reviewed 30-day history; save the explicit demand policy to make calculated thresholds operational.

C_commercial / Supplier_Terms.xlsx: NC-001 Current Stock C6:N6; Supplier Quotes B8:M8. Procurement Agent uses only saved supplier rules and separately saved incoming records. See incoming_order_entry_guide.json for every SKU rule.

D_versions / 02_Warehouse_v2.xlsx: use product_id, not row number. One added, one removed, three changed and 36 unchanged. The manifest and expected_results.json list keys.
