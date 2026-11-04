# Reviewed supplier planning

Open **Supplier planning**. Select the stock snapshot date, a receipt horizon in days and an exact supplier quote for each product. Enter delivery days (1–365), base units per pack, minimum order quantity and the explicit base-unit name. Quote prices must be per one base unit. Stock, quote and policy currencies must match. No unit/currency conversion or missing commercial value is inferred. Source commercial fields are retained as evidence; they never self-approve.

Preview the policy and quantities, acknowledge the date, units, prices and terms, then save the review. Saving creates no purchase action. When supplier planning is enabled, missing/stale terms block affected purchasing. An explicitly reviewed quote choice can resolve multiple quotes; unreviewed ambiguity still blocks. Without this optional policy, the existing stock-target workflow remains available and does not assume pack, MOQ, delivery or incoming-order terms.

Source reorder points and targets retain precedence. For products using an enabled reviewed demand fallback, the selected supplier's delivery days replace the scenario lead time; the demand/stock and supplier planning dates must agree. This does not overwrite source facts or the saved scenario.

## Incoming orders

Record actual external supplier orders separately: reference, product, supplier, ordered and already-received base-unit quantities, currency, order date, expected receipt date and status. Explicitly acknowledge their alignment with the stock snapshot. Generated purchase workbooks never create or confirm incoming stock. Incoming updates never change on-hand inventory; a changed stock count requires a new snapshot or separately approved derived correction.

Only `confirmed` or `partially_received` lines count. Remaining quantity is ordered minus already received. The expected date must fall inclusively between the planning date and planning date + horizon days. Overdue, future-outside-horizon, draft, cancelled, received, unit/currency-mismatched or stale source/mapping/correction records do not count. Re-review/reanchor incoming lines after relevant snapshot changes. Duplicate reference/product/supplier lines are rejected; repeated identical request IDs return the saved record. Updates check revisions and preserve before/after audit history.

## Calculation and approval

Inventory position = physical stock + eligible incoming. If position is below the reviewed reorder point, net requirement = max(0, target − position); otherwise no purchase is suggested. For positive need, quantity = ceil(max(net requirement, minimum quantity) / pack size) × pack size. Rounding can exceed the stock target. Quantities support six decimal places and money uses Decimal, retaining source quote precision before final line-total rounding.

Every proposal includes stock/threshold basis, incoming records and exclusion reasons, pack/MOQ arithmetic, supplier delivery/expected date, units/currency, policy revision, review actor/time and source hashes/revisions. Approval recalculates and checks the exact basis. Source, policy, correction or incoming changes invalidate pending proposals. The Execution sheet retains the full JSON basis and readable calculation; audit records retain proposed lines and the approved basis digest. On-hand stock and incoming-order records remain unchanged by generation. Final purchase workbook generation still requires separate human approval.

Delivery estimates do not guarantee availability before depletion; a receipt inside the horizon may still arrive after a stockout. No external supplier confirmation, live order synchronization, multi-currency conversion or arbitrary unit conversion is implemented. Up to 100 product rules and 1,000 incoming lines are supported locally.
