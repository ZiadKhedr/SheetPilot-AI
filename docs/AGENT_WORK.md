# Agent jobs and work reports

Agent Workspace turns reviewed spreadsheet data into explicit work products. The Orchestrator is a logical role backed by the official Meta API when Meta mode is selected; Sales, Inventory and Procurement are bounded specialist tools. The UI does not imply four independent LLM services or unrestricted autonomous workers.

## Jobs

| Job | Required checks | Output | Purchase action |
| --- | --- | --- | --- |
| Business review | Sales totals, period comparison, stock analysis, supplier review | Combined business brief | None |
| Sales performance | Sales totals and equal-window comparison | Sales brief and product revenue changes | None |
| Stock risk priorities | Inventory analysis | Ranked stock review list with dated evidence | None |
| Supplier readiness | Procurement review | Reviewed quote matches and blockers | None |
| Purchase preparation | Inventory analysis and purchase draft tool | Pending proposal, or the existing action/status | Human approval required |

Meta receives only the tools permitted for the selected job. A read-only job cannot call the draft tool, even if the model requests it. Required checks must complete before the job can finish successfully. Custom questions retain the bounded existing tool selection. Guided mode runs the job's fixed checks without calling a model and is labeled accordingly in both UI and report.

## Sales comparison

`sales_comparison` takes a typed 1–90-day window (default seven) and optional exact product/currency filters. Its latest window ends at the latest usable reviewed sale. The preceding window has equal calendar length. Missing/invalid/future dates are excluded with a warning. Earlier history must extend to the preceding window's start before changes are presented as a comparable trend. Calendar days without recorded sales count as zero, with an explicit caveat about incomplete uploads.

Revenue and differences use Decimal and remain separated by currency. A zero prior-period amount produces no percentage, never infinity. Product changes are ranked by absolute revenue movement within their own currency. Samples retain original cells; no formula is evaluated and no original is edited.

## Work, evidence and progress

Runs persist a title, selected job, source snapshot fingerprint and workbook versions, actual start/end timestamps, measured elapsed time and completed-check counts. Each step records typed arguments, actual running/completed/failed state, runtime, result and a deterministic summary. The client polls only while its request is active; displayed activity comes from persisted backend steps. There are no simulated agent stages.

The work tally names what was actually checked. Sales counts describe the largest sales check, avoiding double-counting overlapping period/all-sales checks. No manual-work baseline or invented hours-saved figure is claimed.

Readable deliverables show sales leaders, comparison periods, stock priorities, supplier lines and blockers. Raw JSON is behind technical details. Older runs retain their recorded evidence; absent older priority/runtime metadata is identified as unrecorded. Purchase cards consult current action status to avoid presenting an already executed proposal as still awaiting approval.

Work reports download as UTF-8 plain text with source-cell examples and captured workbook SHA256 values. Report rendering does not mutate the saved run. Files uploaded after the run are excluded from its captured source context. A review-context change during execution marks the job as needing review. Purchasing revalidates its own source hashes, snapshot and calculations at approval.

## API and boundaries

- `POST /api/workspaces/{id}/agents`: adds optional typed `task` and a 32-character hexadecimal `request_id`; existing custom/guided requests remain supported.
- `GET .../agents/progress/{request_id}`: workspace-scoped progress for the active request.
- `GET .../agent-runs/{run_id}/report`: authenticated plain-text work-report download; running jobs return 409.

Read-only jobs still record runs and audit events; they do not change business source facts, policies or purchase actions. Existing read-only access tokens cannot initiate jobs. Jobs follow the local HTTP request lifecycle; this is not a durable background queue. Interrupted jobs may need to be retried. Purchase preparation remains idempotent, cannot approve itself and never contacts a supplier.
