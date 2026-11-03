# SheetPilot independent audit

Reviewed baseline `c98a4c3` on November 4, 2026. The existing public SheetPilot-AI repository already contains the application and both demo companies. The project brief is the source of the hackathon requirements. It is not an official judging rubric.

## What was already working

The Python CLI reads Excel offline. The FastAPI application reuses its ZIP/XML/grid limits and structural report. React exposes eight screens from upload through audit. SQLite holds workspace-scoped objects and reviewed records with source rows and cell coordinates. Exact identifier overlap supports same-file and cross-file relationship proposals. Manual label suggestions and Meta proposals have distinct origins. Decimal calculations feed dashboards, inventory scenarios and supplier quote matching. Approving an action rechecks the snapshot, generates another workbook and guards repeat approvals. The API tests open the generated file and compare every original to its uploaded bytes.

The starting suite passed 153 Python tests with two skips under normal Windows permissions, and all 31 frontend unit tests passed. The skips were the OS symlink case and opt-in live test. A separate live request on this machine found the configured Muse Spark model in the official account catalog and returned a schema-valid generation. These checks used fictional workbooks.

## Prioritized findings

| Priority | Evidence at the starting revision | Effect |
| --- | --- | --- |
| P0 | Ingestion registered the workbook before registering all tables. Duplicate detection preceded the write lock. | Failure after parsing could strand a snapshot, block retry or accept simultaneous identical uploads. |
| P0 | With only a reader token configured, authorization fell through to unrestricted local mode. Matching reader and owner tokens also granted owner privileges. | An operator attempting read-only access could unintentionally allow writes. |
| P1 | Reproduced a second confirmed view over the same Electronics sales cells. Revenue jumped from USD 1,258 to USD 2,516 with no new sale. | Manual region correction could silently double revenue. |
| P1 | Mapping/relationship review committed before rebuilding the derived mirror. Rule suggestions read and wrote tables without a shared transaction. | A failed rebuild or competing review could leave operational data inconsistent with the shown mapping. |
| P1 | A test provider returned “Sales were 999 dollars.” without a tool call. The orchestrator marked the run completed with zero steps. Inventory tool output also included unmapped custom fields. | A business answer could appear grounded without evidence. Irrelevant workbook text could reach the provider. |
| P1 | Currency validation used Unicode alphabetic characters. The frontend used the value directly in Intl.NumberFormat. | Three non-Latin letters could pass validation and crash a dashboard. |
| P1 | Quotes rounded unit cost to cents before multiplying. Draft idempotency only compared whole proposals. | Six units at 0.125 should total 0.75. Separately approved product subsets could also order against the same on-hand row twice. |
| P2 | XML preflight checked a worksheet's bounding box but did not sum overlapping merge expansions. | Many overlapping large merges could multiply parser work inside a bounded grid. |
| P2 | The sales tool only returned whole-workspace aggregates. Row provenance existed in SQLite, but a business owner could not directly inspect sales records behind a revenue figure. | A narrower business question could be answered with the wrong aggregate. |
| P2 | Workspace selection changed the request root before the matching data arrived. A rejected switch left stale data on screen. | In a local multi-business demo a user could see one company's records under another selection. |

## Other boundaries found during inspection

- Exact raw-row deduplication is a business assumption. Two genuinely identical transactions without distinct IDs can be treated as duplicates. Blank-separated and explicit tables work better than merged forms or layouts with repeated subtotals. Formula and error cells cannot supply operational facts.
- Owner and reader tokens apply to the entire local installation. The workspace ID scopes queries, but there is no per-company membership, SSO or tenant-grade isolation. The audit table is writable by a local database administrator.
- The orchestrator has three allowlisted tools, typed arguments and finite turn/call limits. There is no arbitrary SQL, code execution, inventory write, supplier communication or approval tool. Guided checks are deterministic. There is no OpenAI Agents SDK dependency.
- The workspace state response includes structural reports and historical run details. The app repeatedly scans whole workspaces for some analytics. The upload ceiling is not a performance benchmark or a per-workspace quota.
- Approval idempotency applies to the same proposal. Separate overlapping product selections or a changed snapshot can still represent the same purchasing need. Incoming orders and supplier pack sizes are outside the model.
- The build uses TypeScript and Vite. The repo defines no standalone lint command. Docker packages the same local application. Existing screenshots and test summaries document earlier runs and do not establish the current result.

## Screen-by-screen inspection

| Screen | Behavior and decision |
| --- | --- |
| Overview | Revenue already kept currencies separate. Added a way to inspect contributing sales and their source coordinates. |
| Excel File Manager | Individual upload errors used to stop the rest of the batch. Added per-file feedback and a next step based on mapping state. |
| Structure Explorer | Existing controls show regions, alternate headers, merged cells, hidden sheets and unexecuted formulas. Manual selection is still needed for irregular layouts. |
| Mapping Review | Existing per-column evidence and relationship diagnostics supported corrections. Added aligned sample rows under the operator's current field choices and protected overlapping confirmations. |
| Business Analytics | Existing stock and demand panels distinguish missing thresholds. Revenue inspection now shares the same sales calculations as the agent. |
| Agent Workspace | Existing traces exposed tool results as JSON. Scoped answers now show validated totals and the selected scope in plain text, with the trace still available. |
| Approval Center | Existing details expose lines, source versions and human approval. Fixed fractional quote display and duplicate purchasing across proposals. |
| Activity Timeline | Existing events record tools, conflicts and executions. Successful approvals now have an explicit actor and snapshot event in the execution transaction. |

See [implementation and verification](IMPROVEMENTS.md) for disposition, scenario evidence and remaining work.
