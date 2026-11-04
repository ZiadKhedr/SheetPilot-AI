"""Read-only business jobs and evidence-backed work reports for bounded agents."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from .analytics import money, records, sales_metrics

JOBS = {
    "custom": ("Custom request", ()),
    "daily_review": ("Business review", ("sales_analysis", "sales_comparison", "inventory_analysis", "procurement_review")),
    "sales_review": ("Sales performance report", ("sales_analysis", "sales_comparison")),
    "stock_review": ("Stock risk priorities", ("inventory_analysis",)),
    "supplier_review": ("Supplier readiness report", ("procurement_review",)),
    "replenishment": ("Purchase-order preparation", ("inventory_analysis", "draft_purchase_orders")),
}


def compare_sales(store, workspace, arguments):
    scope = arguments.scope()
    data = [r for r in records(store, workspace) if r["entity"] == "sales"
            and (not scope.product_id or r["product_id"] == scope.product_id)
            and (not scope.currency or r["data"].get("currency") == scope.currency)]
    dated, omitted = [], 0
    for record in data:
        try:
            day = date.fromisoformat(record["data"].get("sale_date") or "")
            if not date(1900, 1, 1) <= day <= date.today():
                raise ValueError()
            dated.append((record, day))
        except (ValueError, TypeError):
            omitted += 1
    result = {"status": "insufficient_history", "window_days": arguments.window_days,
              "scope": scope.model_dump(mode="json", exclude_none=True), "rows_compared": 0,
              "periods": [], "revenue_changes": [], "product_changes": [], "warnings": [], "source_examples": []}
    if omitted:
        result["warnings"].append(f"{omitted} sales rows have missing, invalid or future dates and were excluded.")
    if not dated:
        result["warnings"].append("No reviewed dated sales are available for this comparison.")
        return result
    end = max(day for _, day in dated)
    current_start = end - timedelta(days=arguments.window_days-1)
    previous_end = current_start-timedelta(days=1)
    previous_start = current_start-timedelta(days=arguments.window_days)
    complete = min(day for _, day in dated) <= previous_start
    result["status"] = "completed" if complete else "limited_history"
    result["warnings"].append("Periods end at the latest reviewed sale, not necessarily today. Calendar days without recorded sales count as zero; incomplete or delayed uploads may affect the comparison.")
    if not complete:
        result["warnings"].append("The earlier period is not fully covered by available history. Changes are not treated as a comparable trend.")
    groups = {}
    for name, start, finish in (("previous", previous_start, previous_end), ("current", current_start, end)):
        rows = [r for r, day in dated if start <= day <= finish]
        groups[name] = rows
        metrics = sales_metrics([r["data"] for r in rows])
        result["periods"].append({"name": name, "from": start.isoformat(), "to": finish.isoformat(),
                                  "rows": len(rows), "units": metrics["units_sold"] or "0", "revenue": metrics["revenue"]})
        result["rows_compared"] += len(rows)
        result["warnings"].extend(w for w in metrics["warnings"] if w not in result["warnings"])
        result["source_examples"].extend({"period": name, "product_id": r["product_id"], "source": r["source"]} for r in rows[:3])
    previous, current = ({r["currency"]: Decimal(r["amount"]) for r in p["revenue"]} for p in result["periods"])
    for currency in sorted(previous.keys() | current.keys()):
        old, new = previous.get(currency, Decimal(0)), current.get(currency, Decimal(0))
        result["revenue_changes"].append({"currency": currency, "previous": money(old), "current": money(new),
            "change": money(new-old) if complete else None,
            "percent": money((new-old)*100/old) if complete and old else None})
    products = defaultdict(lambda: {"previous": Decimal(0), "current": Decimal(0)})
    names = {}
    for period, rows in groups.items():
        for row in rows:
            value = row["data"]
            if not value.get("currency"):
                continue
            key = (row["product_id"], value["currency"])
            names[key] = value.get("product_name") or row["product_id"]
            products[key][period] += Decimal(value["revenue"])
    if complete:
        for key, amounts in sorted(products.items(), key=lambda item: abs(item[1]["current"]-item[1]["previous"]), reverse=True)[:10]:
            old, new = amounts["previous"], amounts["current"]
            result["product_changes"].append({"product_id": key[0], "name": names[key], "currency": key[1],
                "previous": money(old), "current": money(new), "change": money(new-old),
                "percent": money((new-old)*100/old) if old else None})
    return result


def work_counts(run):
    done = [s for s in run["steps"] if s["status"] in {"completed", "needs_review"}]
    sales = max((s["result"].get("total", s["result"].get("rows_compared", 0)) for s in done
                 if s["tool"] in {"sales_analysis", "sales_comparison"}), default=0)
    stock = max((s["result"].get("total_products", 0) for s in done if s["tool"] == "inventory_analysis"), default=0)
    suppliers = max((s["result"].get("ready_count", 0) for s in done if s["tool"] == "procurement_review"), default=0)
    return {"completed_checks": len(done), "sales_rows_in_largest_check": sales,
            "stock_products_checked": stock, "supplier_lines_ready": suppliers}


def report_text(store, workspace, run):
    """Plain text only: file/cell names and data cannot become executable markup."""
    lines = ["SheetPilot AI — Agent work report", run.get("title", "Agent run"),
             f"Run: {run['id']}", f"Status: {run['status']}",
             f"Execution: {'Meta planned the tools' if run['origin']=='meta' else 'Guided data tools; no AI used'}",
             f"Started: {run['created']}",
             f"Elapsed: {run['elapsed_ms']/1000:.2f} seconds" if "elapsed_ms" in run else "Elapsed: not recorded for this older run",
             "", run["summary"], ""]
    workbooks = {w["id"]: w for w in run.get("source_versions", store.list(workspace, "workbook"))}
    lines.append("Workspace source snapshots (context; source rows checked are listed per tool below):")
    lines.extend(f"{w['name']} | SHA256 {w['sha256']}" for w in workbooks.values())
    lines.append("")
    for step in run["steps"]:
        lines.extend([f"{step['agent']} — {step['tool']}", step.get("summary", ""),
                      f"Tool runtime: {step['elapsed_ms']/1000:.3f} seconds" if "elapsed_ms" in step else "Tool runtime: not recorded for this older run"])
        result = step.get("result") or {}
        if step["tool"] == "sales_comparison":
            for period in result.get("periods", []):
                lines.append(f"{period['name']}: {period['from']} to {period['to']}; {period['rows']} rows; {period['units']} units")
            for change in result.get("revenue_changes", []):
                lines.append(f"{change['currency']}: {change['previous']} -> {change['current']}; change {change['change'] or 'not comparable'}")
        if step["tool"] == "inventory_analysis":
            for item in result.get("priorities", [])[:20]:
                lines.append(f"{item['product_name']} ({item['product_id']}): {item['reason']}; top-up {item['suggested_quantity']} units")
        if step["tool"] in {"procurement_review", "draft_purchase_orders"}:
            for item in result.get("lines", []):
                lines.append(f"{item['product_id']} / {item['supplier_id']}: {item['quantity']} units, {item['currency']} {item['line_total']}")
        evidence = list(result.get("rows", result.get("source_examples", [])))
        evidence += [{"source": r["source"]} for r in result.get("stock", []) if r.get("source")][:3]
        evidence += [{"source": source} for source in result.get("source_examples_raw", [])]
        for row in evidence[:12]:
            source = row.get("source", {})
            book = workbooks.get(source.get("workbook_id"), {})
            cells = ", ".join(f"{field}={cell}" for field, cell in source.get("cells", {}).items())
            lines.append(f"Source: {book.get('name','workbook')} | {source.get('sheet','')} row {source.get('row','')} | {cells} | SHA256 {book.get('sha256','')}")
        lines.extend(result.get("warnings", []))
        lines.extend(b["message"] for b in result.get("blockers", []))
        lines.append("")
    lines.extend(["Actions: " + (", ".join(run["action_ids"]) or "None"),
                  "Findings record this run's inputs and checks. Review current proposal status in Approval Center.",
                  "Purchase drafts require separate human approval. Originals are preserved. No supplier is contacted."])
    return "\n".join(lines)
