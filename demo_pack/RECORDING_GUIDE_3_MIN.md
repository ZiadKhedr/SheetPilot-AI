# SheetPilot AI — three-minute recording script

**Final video: 2:55, with a five-second margin.** The screen names below match the current web sidebar. Read only the quoted English narration. Actions and preparation notes are not spoken.

## Before recording

- Use a fresh Nile Circuit Distribution workspace and the three files in `core/`: `01_Commerce.xlsx`, `02_Warehouse.xlsx`, `03_Supplier_Quotes.xlsx`.
- Verify the real Meta connection before filming. Keep the commercial policy disabled for this main scenario. Use November 3, 2026 as the historical stock scenario date.
- Rehearse the actual workflow once in a separate workspace. Record a fresh real workflow for the final footage. Review all four operational mappings and the three necessary links yourself.
- This is an edited three-minute demonstration. Capture the full real operations, then remove upload/provider/calculation waiting and unneeded navigation. Retain the genuine review and approval steps, and use a small “Processing time shortened” caption across cuts. Never invent responses, progress, reports or approval history. A continuous live run cannot be guaranteed to finish within three minutes.
- Narration is deliberately short. Rehearse at approximately 125–135 words per minute. Keep the exported video at or below 3:00. Optional challenge packs are outside this video.

## Exact screen sequence and English narration

### 0:00–0:15 — Excel files

**Action:** Start on **Excel files** in the fresh workspace. Click **Browse files**, select the three core workbooks, and show their inspected file cards. Do not use the built-in Electronics demo: it is a different dataset.

**Say:**

> “This is SheetPilot AI: your spreadsheets, your AI workforce. Nile Circuit Distribution runs on separate sales, stock, and supplier workbooks. I upload their existing Excel files to bring the business together.”

### 0:15–0:30 — Structure explorer

**Action:** Click **Explore structure** on the commerce file, or open **Structure explorer** in the sidebar. Show **Sales Lines** and **Orders**, the detected header row and source range. Briefly show the hidden **Internal Notes** tab without mapping it.

**Say:**

> “SheetPilot detects the tables and their layouts, including offset headers and hidden notes. Every business value keeps its original workbook and cell reference.”

### 0:30–1:00 — Mapping review

**Action:** Open **Mapping review** → **Analyze with Meta**. After the real response, show the price/revenue fields and physical stock field. Review and click **Confirm mapping** for Sales Lines, Orders, Current Stock and Supplier Quotes. Use short cuts between real confirmations.

**Review checklist, not narration:** Sales Lines is sales; Units Sold is quantity; Net Selling Price is unit_price; List Price and Discount per Unit are separate; Net Line Amount is revenue. Orders is orders and Invoice Total is order_total. Physical On Hand is stock_quantity, separate from opening/reserved stock. Quotes is suppliers with product, supplier and base-unit cost. Preserve useful custom columns. Exclude Internal Notes and title rows.

**Say:**

> “Meta proposes what the columns mean. I review the actual selling price, line revenue, and physical stock before confirming. Order totals stay separate from sales-line revenue, so the dashboard cannot count them twice. Unfamiliar business columns are preserved.”

### 1:00–1:18 — Mapping review: relationships

**Action:** Click **Discover relationships**. Show evidence and use **Confirm relationship** only for Sales Lines–Orders on order_id, Sales Lines–Current Stock on product_id, and Current Stock–Supplier Quotes on product_id. Inspect exact matches and cardinality; skip other candidates.

**Say:**

> “Next, I review the exact links between order headers, sales lines, stock, and supplier quotes. These confirmed relationships supply dates, product descriptions, and purchasing evidence.”

### 1:18–1:38 — Business analytics

**Action:** Open **Business analytics**. Show **Revenue over time**, **Top-selling products**, then the stock-planning result for **NC-001, Wireless Earbuds**. If necessary set its stock scenario date to November 3, 2026 during the captured workflow, then cut routine navigation. Do not enable a demand ordering fallback or supplier policy.

**Say:**

> “The dashboard now uses reviewed records. These wireless earbuds have just eighteen units on hand, against average sales of twenty per day: less than one day of stock cover in this historical snapshot.”

### 1:38–2:08 — Agent workspace: Review the business

**Action:** Open **Agent workspace**. Under **How to run**, choose **Meta chooses and runs tools**. Click **Start job** on **Review the business**. Show the actual completed specialist checks and their evidence. In the resulting report, show the sales comparison: **NC-002 +200%**, **NC-003 −60%**. Download the work report using its report download control.

**Say:**

> “I ask the Orchestrator to review the business. Meta selects the tools; deterministic calculations produce the numbers. Sales checks totals and compares equal seven-day periods. Inventory prioritizes stock risks, and Procurement checks suppliers. The dock grew two hundred percent, while the SSD fell sixty percent. Every check includes evidence.”

### 2:08–2:28 — Agent workspace: Prepare purchase drafts

**Action:** In the same screen, click **Start job** on **Prepare purchase drafts**. Show the actual Inventory and Procurement steps, then click **Open Approval Center**. Keep the generated proposal pending until the next segment.

**Say:**

> “Now I request purchase drafts. Inventory and Procurement prepare a pending proposal. For the earbuds, the source stock target gives a top-up of one hundred sixty-two units, costing forty-four thousand five hundred fifty Egyptian pounds.”

### 2:28–2:50 — Approval center, then downloaded Excel

**Action:** In **Approval center**, click **Review details**. Show the NC-001 quantity, supplier, EGP line total and affected source versions. Close the details modal and click **Approve & generate Excel** once. Click **Download Excel**. Open the generated workbook in Excel and briefly show **Purchase Orders**, **Source Trace**, and **Execution**. This final portion switches from the website to the downloaded workbook.

**Say:**

> “I review the quantities, supplier, costs, and sources, then approve generation. SheetPilot creates an additional Excel workbook with purchase orders, source traces, and execution details. The originals remain unchanged. No supplier message is sent, and physical stock is not increased.”

### 2:50–2:55 — Closing shot

**Action:** Hold on the generated workbook, or return to the executed proposal in **Approval center**. Do not start another run or create another proposal.

**Say:**

> “SheetPilot AI: spreadsheet intelligence, visible agent work, and human-controlled action.”

## Final check

- Keep genuine Meta provenance visible. Guided checks are no-AI alternatives and cannot stand in for Meta footage.
- Sales comparison ends at the latest reviewed sale: October 28–November 3 versus October 21–27, 2026. The comparison appears in the business review report; do not hunt for a separate product-change dashboard panel.
- The EGP 44,550 amount is the NC-001 line, not the whole proposal. The full core proposal contains three lines totaling EGP 906,550. These are expected deterministic results, not proof that the live recording has already completed.
- The short video omits version review, repairs, supplier-pack rounding, incoming-order entry and a repeat-approval demonstration. Those remain separate optional segments in the longer recording guide.
- If any live result differs, stop and review it before recording a successful outcome. Never narrate expected figures over contradictory results.
