# Four-minute SheetPilot demonstration

Start the production build on loopback with a fresh fictional workspace. Verify Meta in Connections before presenting. Keep the three Electronics files ready in `demo_data/company_a/`. Provider latency varies. If presenting on a clock, prepare a second, already reviewed fictional workspace as a clearly labeled checkpoint.

| Time | Show | What the audience should see |
| --- | --- | --- |
| 0:00–0:30 | Upload Sales, Inventory and Suppliers together. | Three immutable files and progress by filename. Open Sales in Structure Explorer and point to the header on row 5. |
| 0:30–1:25 | Choose **Review mappings**, then **Analyze with Meta**. Open **Preview mapped rows**. | The original labels, row numbers and proposed meanings line up. Confirm the three business tables. Leave the unrelated admin table unconfirmed. |
| 1:25–1:55 | Discover relationships and confirm the product links. Open Overview. | Four overlapping product identifiers support the joins. Revenue is USD 1,258. Click **Inspect sales rows**, filter by A001 and show the original worksheet and revenue cells. |
| 1:55–2:35 | Ask “What is the reviewed sales revenue for product ID A001 alone, across all dates?” | The sales tool shows the selected scope, USD 270.00, six units and contributing source rows. |
| 2:35–3:10 | Ask “Analyze inventory and draft purchase orders for all low-stock products.” | Expand the actual tool trace. Inventory is below threshold for three products. Procurement creates a pending proposal. |
| 3:10–3:50 | Open Approval Center, inspect source versions and approve. Download and open the workbook. | The three lines total 82 units and USD 1,809.00. Show the Source Trace and Execution sheets. |
| 3:50–4:00 | Open Activity Timeline. | The approval and execution events identify the operator and output. The Arabic restaurant dataset uses the same application and review process. |

On a provider failure, show the actual error. The label suggestions and **Run guided check** controls can demonstrate the deterministic path. Identify that path as guided when using it. There is no supplier email, source-file overwrite or live cloud synchronization.
