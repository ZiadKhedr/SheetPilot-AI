# SheetPilot audit handoff

November 4, 2026. The existing FastAPI, SQLite, React/TypeScript and offline analyzer remain the product. The demonstration now has a checkable chain from an original cell to a revenue answer and from reviewed inventory to an approved Excel file. See [baseline findings](AUDIT_REPORT.md) and [run instructions](README.md).

## Implementation

| Area | Changes | Principal files |
| --- | --- | --- |
| Intake | Check duplicate hashes under a write lock. Commit the snapshot metadata, regions and audit event together. Remove the attempted file on failure. Bound cumulative merged-cell expansion before OpenPyXL loads the file. | `ingestion.py`, `excel_intelligence/workbook_reader.py` |
| Review | A mapping, its invalidated relationships and its operational mirror commit together. Rule proposals cannot race a human review. Confirmed regions cannot share data cells. For previous overlapping views the shared read path counts equivalent views once and withholds conflicting regions. | `mapping.py`, `analytics.py`, `routes.py`, `demand.py` |
| Procurement | Preserve up to six fractional digits in a supplier quote and round the extended line amount to cents. A stock row cannot be ordered twice through overlapping proposals. Recheck at approval for previously stored drafts. Record the approving actor, snapshot and execution outcome. | `actions.py`, `analytics.py`, `frontend/src/AgentPages.tsx` |
| Access and provider errors | Reader-only configurations require the read token. Matching owner/reader credentials fail startup. Reject malformed model catalogs, clear failed verification and recover from a corrupt verification cache. | `api.py`, `provider.py`, `routes.py` |
| Business questions | Meta chooses typed tools. Sales accepts exact product IDs, currencies and inclusive ISO dates. Inventory supports one product or all products. The backend renders the published answer from executed tools and includes scope, totals and evidence. An unsupported answer without tools gets one retry, then fails visibly. Inventory tool messages omit unmapped custom columns. Tool payloads have a model-context size limit. | `agents.py`, `models.py`, `analytics.py` |
| Product experience | File-by-file progress and recovery, a contextual next step, aligned sample rows during mapping, a revenue drill-down with filtering, paging and original cell addresses, sub-cent unit price display and guarded workspace loading. All eight screens use the existing visual system. | `frontend/src/App.tsx`, `DataPages.tsx`, `MappingPage.tsx`, `DashboardPage.tsx`, `SalesEvidence.tsx`, `style.css` |
| Reproducible browser verification | Each Playwright server starts with a unique fictional SQLite workspace. Screenshots and downloads from the live workflows go to the test output directory rather than overwriting tracked demo evidence. | `frontend/playwright.config.ts`, `frontend/e2e/` |

Backend filenames without a directory refer to `src/sheetpilot/`. The changes introduce no new dependencies and require no database migration.

When a supplier row predates precision tracking, procurement compares its stored price with the original cell. A mismatch blocks the draft and asks the operator to confirm the supplier mapping again. Confirmation rebuilds the mirror from the preserved cells. Historical executed workbooks remain historical artifacts.

## Scenario results

| Scenario | Expected | Observed | Result |
| --- | --- | --- | --- |
| 1. Conventional sales | Normalize numeric cells, compute deterministic revenue and units. | Electronics produced USD 1,258.00 from eight reviewed sales, 31 units. | Pass |
| 2. Unconventional terminology | Preserve source labels and accept reviewed alternate meanings. | The Arabic restaurant schema produced EGP 11,890.00. Textile headers such as Swatch and Bolts required explicit review. The leading-zero ID 007 survived. | Pass |
| 3. Multiple related sheets | Count line sales once and inherit context only across reviewed links. | Four-sheet retail fixture produced GBP 54.00. Order totals were excluded and order dates appeared after relationship approval. | Pass |
| 4. Inconsistent inventory | Exclude invalid quantities and surface missing reorder thresholds. | Textile stock totaled 9 across valid rows. The text quantity was excluded. Separate demand fixtures showed unassessed stock until an eligible policy was approved. | Pass |
| 5. Partially matching files | Show matched and unmatched identifiers without autojoining. | Dispatch and Bins shared only 007. The proposal stayed unconfirmed with unmatched IDs on both sides. | Pass |
| 6. Ambiguity | Retain drafts until confirmed and protect already counted cells. | Reproduced USD 2,516 for an overlapping Electronics mapping at baseline. The same confirmation now returns 409 and revenue stays USD 1,258. | Pass |
| 7. Unsupported or malformed file | Return a bounded error, allow retry and preserve the workspace. | Bad ZIP/extension tests returned 422. Injected late registration failure left no workbook or original. Concurrent identical retries produced one success and one 409. | Pass |
| 8. Formulas and untrusted text | Display formulas as data, exclude mapped formulas and validate money inputs. | Textile formula and invalid currency rows were excluded. Instruction-like source text caused no action. Downloaded purchase workbooks had no formula cells. | Pass |
| 9. Verifiable natural-language question | Select only A001 and report the fixture total using reviewed rows. | Live Meta selected the product filter. The tool returned USD 270.00 with source cell references. No purchase proposal was created. | Pass |
| 10. Approved action | A pending draft has no output. One approval creates one workbook. | Electronics produced 82 units / USD 1,809.00. Restaurant produced 47 units / EGP 12,630.00. Reopened both browser downloads and matched every product, quantity and amount to the oracle. Both had three order lines and six source-trace rows. | Pass |
| 11. Insufficient permission | Reader and wrong-workspace requests cannot approve. | API returned 403 for readers, 401 for invalid credentials and 404 for the other workspace. No output was written. | Pass |
| 12. Provider failure | Errors remain visible and cannot silently become successful AI runs. | Contract tests rejected invalid schemas, disallowed tools, missing keys and repeated truncation. A real tool argument encoding failed on the first live run. Explicit filter arrays fixed it and the same live workflow passed. | Pass after fix |

Mixed-batch failures, absent currencies, unsupported arbitrary questions and incomplete supplier evidence have explicit UI or API handling. The model can still choose an inappropriate scope. The product shows that scope and the source facts so an operator can check it.

## Performance and verification scope

A local synthetic sheet with 2,500 sales and 15,006 populated cells took 0.81 seconds for intake, 0.20 seconds for review and materialization and 0.12 seconds for a dashboard read. The reviewed total was GBP 16,250.00. This was one measurement on the prepared Windows machine, with no concurrent clients or network model call.

The actual course of verification matters. The sandboxed Python run encountered a filesystem failure and stalled. Running with normal Windows permissions completed the suite. The installed pnpm tried to replace the existing dependency directory, so local verification invoked the already-installed Vitest, TypeScript, Vite and Playwright executables. A new UI test initially left two dialogs mounted across tests. Explicit cleanup fixed it. A quote-precision fixture initially attempted to confirm an unknown header. It now explicitly reviews row one, as a human would. Details and final counts are in [test results](docs/TEST_RESULTS.md).

## Hackathon assessment and next work

The strongest demonstration is a live semantic proposal on unfamiliar columns, a human correction, a source-backed business answer, and an Excel purchase order after approval. The final two live browser flows took about 2.1 minutes for Electronics and 1.5 minutes for Restaurant. Allow time for provider variation when recording. Use the [four-minute walkthrough](docs/DEMO_SCRIPT.md).

1. **Before adding more purchasing actions**, support replacement snapshots, outstanding orders, cancellations and reconciliation. Current idempotency guards reuse of the same immutable stock row. A different uploaded snapshot can still represent the same physical stock.
2. **Before recommending unattended imports**, benchmark authorized business files with repeated subtotals, multirow headers, legitimate identical transactions, missing IDs and mixed units. Exact duplicate exclusion and positive, single-grain quantities need human scrutiny.
3. **Before shared hosting**, add authenticated company membership, isolated workers, quotas, external audit storage and backup/restore tests. Pagination of sales evidence is available, but workspace state still returns full structural reports.
4. **For broader business Q&A**, add separately tested tools for returns, margin and unit conversion. Published answers today are calculated summaries within the supported sales, inventory and procurement scopes. Guided mode is a separate deterministic workflow.
