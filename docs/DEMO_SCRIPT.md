# Three-minute SheetPilot AI demonstration

Before recording: start the app, verify Meta, use a clean workspace, and keep the three Company A files in demo_data/company_a ready. All data is fictional. Do not display .env.

0:00–0:25 — The familiar starting point
“Companies already run on spreadsheets. SheetPilot adds an AI workforce without asking them to abandon Excel.”
Open Excel File Manager and upload Sales.xlsx, Inventory.xlsx and Suppliers.xlsx.

0:25–0:50 — Understand the structure
Show the Structure Explorer: sales headers on row 5, merged titles, an unrelated admin table, and hidden notes with formulas. “The analyzer maps structure and retains source coordinates. It never executes these formulas.”

0:50–1:20 — Meaning with human review
Choose Analyze with Meta. Show the live provider status and review the proposed Sales, Inventory and Suppliers mappings. Confirm the three business tables. Show an uncertain/admin table remaining unconfirmed or exclude it explicitly. Discover relationships and confirm product-ID overlap based on four matching identifiers.

1:20–1:45 — Calculations you can inspect
Open Overview. Show USD 1,258.00 revenue, 31 units sold, 34 units on hand, and three low-stock products. In Business Analytics show the exact duplicate and missing-product row excluded from the derived mirror. “The workbook stays untouched; this is a reviewed operational snapshot.”

1:45–2:20 — A real AI workforce
Ask: “Analyze sales and inventory. Draft purchase orders for all low-stock products. Do not approve anything.”
Show Orchestrator results and actual Inventory/Procurement tool calls. “Meta plans; typed backend tools calculate. Agents cannot approve orders or write arbitrary files.”

2:20–2:50 — Your call, every time
Open Approval Center. Inspect three line items totaling USD 1,809.00, source file versions, and validation results. Approve once, download and open the actual Excel output. Show Purchase Orders, Source Trace and Execution sheets. “No email was sent. No stock quantity was changed. This additional workbook is the approved result.”

2:50–3:00 — Close with evidence
Show Activity Timeline and test results. “We repeat the same workflow on a differently structured Arabic restaurant dataset. SheetPilot knows when to ask for review; we don’t claim perfect understanding of every file.”

If a live API request fails, show the real error and retry. The guided tool check is explicitly not AI and must not be presented as a successful Meta run.
