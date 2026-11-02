"""Human-gated, idempotent purchase-order generation; originals are immutable."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from .analytics import inventory_tool, money, records
from .ingestion import digest
from .store import Problem, now, uid


def fingerprint(store, workspace, con=None):
    value = {
        "workbooks": sorted((w["id"], w["sha256"]) for w in store.list(workspace, "workbook", con)),
        "tables": sorted((t["id"], t["revision"], t["status"]) for t in store.list(workspace, "table", con)),
        "relationships": sorted((r["id"], r["status"], r["revisions"]) for r in store.list(workspace, "relationship", con)),
    }
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def draft_lines(store, workspace, product_ids=None):
    stock = [r for r in inventory_tool(store, workspace) if r["low_stock"]]
    if product_ids:
        unknown = set(product_ids) - {r["product_id"] for r in stock}
        if unknown:
            raise Problem("Requested products are not in the validated low-stock list.")
        stock = [r for r in stock if r["product_id"] in product_ids]
    if not stock:
        raise Problem("No validated products currently need replenishment.")
    suppliers = [r for r in records(store, workspace) if r["entity"] == "suppliers"]
    links = [r for r in store.list(workspace, "relationship") if r["status"] == "confirmed" and r["field"] == "product_id"]
    lines, problems = [], []
    for item in stock:
        candidates = []
        for record in suppliers:
            supplier = record["data"]
            pair = {item["source"]["table_id"], record["source"]["table_id"]}
            linked = any({r["left_table"], r["right_table"]} == pair for r in links)
            if (linked and supplier["product_id"] == item["product_id"]
                    and (not item.get("supplier_id") or supplier["supplier_id"] == item["supplier_id"])):
                candidates.append(record)
        if len(candidates) != 1:
            problems.append(f"{item['product_id']}: needs exactly one supplier quote linked by a reviewed product relationship.")
            continue
        record = candidates[0]
        supplier = record["data"]
        if not item.get("currency") or item["currency"] != supplier.get("currency"):
            problems.append(f"{item['product_id']}: stock and supplier currencies must be explicit and match.")
            continue
        quantity = Decimal(item["suggested_quantity"])
        cost = Decimal(supplier["unit_cost"])
        lines.append(dict(product_id=item["product_id"], product_name=item.get("product_name") or item["product_id"],
            supplier_id=supplier["supplier_id"], supplier_name=supplier["supplier_name"], quantity=str(quantity),
            unit_cost=money(cost), line_total=money(quantity * cost), currency=item["currency"],
            stock_quantity=item["stock_quantity"], target_stock=item["target_stock"],
            sources=[item["source"], record["source"]]))
    if problems:
        raise Problem("Cannot safely draft: " + " ".join(problems))
    return sorted(lines, key=lambda l: (l["supplier_id"], l["product_id"]))


def propose(store, workspace, product_ids=None):
    store.workspace(workspace)
    lines = draft_lines(store, workspace, product_ids)
    snapshot = fingerprint(store, workspace)
    key = sha256((snapshot + json.dumps(lines, sort_keys=True)).encode()).hexdigest()
    totals = defaultdict(Decimal)
    for line in lines:
        totals[line["currency"]] += Decimal(line["line_total"])
    with store.connection(immediate=True) as con:
        if snapshot != fingerprint(store, workspace, con):
            raise Problem("Data changed while preparing the draft. Please retry.", 409)
        existing = next((a for a in store.list(workspace, "action", con) if a["idempotency_key"] == key), None)
        if existing:
            return existing
        action = store.put(workspace, "action", dict(
            id=uid(), type="purchase_order", title=f"Replenish {len(lines)} low-stock products", status="pending",
            justification="Validated on-hand quantity is below the reviewed reorder threshold. Restore to target stock; purchase orders do not alter on-hand inventory.",
            lines=lines, totals=[{"currency": c, "amount": money(v)} for c,v in sorted(totals.items())],
            source_versions=[{"workbook_id": w["id"], "name": w["name"], "sha256": w["sha256"]}
                             for w in store.list(workspace, "workbook", con)],
            snapshot=snapshot, product_ids=product_ids or [], idempotency_key=key,
            validation=["Reviewed mappings", "Confirmed product relationships", "Unambiguous supplier quote",
                        "Matching explicit currency", "Deterministic quantities and Decimal money"],
            output=None, reviewed_at=None, modifications=[]), con)
        store.event(workspace, "action.proposed", action["title"], {"action_id": action["id"], "totals": action["totals"]}, con)
        return action


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_purchase_order(store, action):
    destination = store.root / "outputs" / f"{action['id']}.xlsx"
    temporary = store.root / "outputs" / f"{action['id']}.tmp.xlsx"
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Purchase Orders"
    sheet.append(["PO Reference", "Supplier ID", "Supplier", "Product ID", "Product", "Quantity", "Unit Cost", "Line Total", "Currency"])
    for line in action["lines"]:
        reference = f"SP-{action['id'][:8]}-{line['supplier_id']}"
        sheet.append([safe_cell(v) for v in [reference, line["supplier_id"], line["supplier_name"],
            line["product_id"], line["product_name"], float(Decimal(line["quantity"])),
            float(Decimal(line["unit_cost"])), float(Decimal(line["line_total"])), line["currency"]]])
    trace = wb.create_sheet("Source Trace")
    trace.append(["Product ID", "Source workbook", "SHA256", "Worksheet", "Row", "Region"])
    versions = {s["workbook_id"]: s for s in action["source_versions"]}
    for line in action["lines"]:
        for source in line["sources"]:
            version = versions[source["workbook_id"]]
            trace.append([safe_cell(v) for v in [line["product_id"], version["name"], version["sha256"],
                                                source["sheet"], source["row"], source["ref"]]])
    meta = wb.create_sheet("Execution")
    meta.append(["Property", "Value"])
    for row in [("Action", action["id"]), ("Approved by", action["approved_by"]), ("Approved at", action["reviewed_at"]),
                ("Operation", "Additional purchase-order workbook; uploaded originals preserved"),
                ("Idempotency key", action["idempotency_key"])]:
        meta.append(row)
    for ws in wb:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill("solid", fgColor="174E40")
        for column in ws.columns:
            ws.column_dimensions[column[0].column_letter].width = min(52, max(16, max(len(str(c.value or "")) for c in column)+2))
    try:
        wb.save(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
        wb.close()
    return destination


def review_action(store, workspace, identifier, decision, actor):
    error = None
    try:
        with store.connection(immediate=True) as con:
            action = store.get(workspace, "action", identifier, con)
            if action["status"] == "executed":
                if decision == "reject":
                    raise Problem("An executed action cannot be rejected.", 409)
                return action
            if action["status"] != "pending":
                raise Problem("Only pending actions can be reviewed.", 409)
            if decision == "reject":
                action.update(status="rejected", reviewed_at=now(), approved_by=actor)
                store.put(workspace, "action", action, con)
                store.event(workspace, "action.rejected", "Proposal rejected; no workbook was generated.",
                            {"action_id": identifier, "actor": actor}, con)
                return action
            changed = action["snapshot"] != fingerprint(store, workspace, con)
            for source in action["source_versions"]:
                path = store.root / "originals" / f"{source['workbook_id']}.xlsx"
                if not path.is_file() or digest(path) != source["sha256"]:
                    changed = True
            if changed:
                error = "Source files, mappings, or relationships changed. Regenerate and review the proposal."
            else:
                current_lines = draft_lines(store, workspace, action["product_ids"])
                if current_lines != action["lines"]:
                    error = "The proposal differs from the current validated calculations."
            if error:
                action.update(status="conflicted", validation=action["validation"] + [error])
                store.put(workspace, "action", action, con)
                store.event(workspace, "action.conflicted", error, {"action_id": identifier}, con)
            else:
                action.update(reviewed_at=now(), approved_by=actor)
                path = write_purchase_order(store, action)
                action.update(status="executed", output={"name": f"Purchase-Orders-{identifier[:8]}.xlsx", "sha256": digest(path)},
                    modifications=[{"operation": "create_workbook", "sheet": "Purchase Orders",
                                    "range": f"A1:I{len(action['lines'])+1}", "data_rows": len(action["lines"])},
                                   {"operation": "create_sheet", "sheet": "Source Trace"},
                                   {"operation": "create_sheet", "sheet": "Execution"}])
                store.put(workspace, "action", action, con)
                store.event(workspace, "action.executed", "Approved purchase orders generated; originals preserved.",
                            {"action_id": identifier, "actor": actor, "output_sha256": action["output"]["sha256"],
                             "modifications": action["modifications"]}, con)
        if error:
            raise Problem(error, 409)
        return action
    except OSError:
        store.event(workspace, "action.failed", "Could not save the output workbook; proposal remains pending.", {"action_id": identifier})
        raise Problem("Could not save the output workbook. Please retry.", 500)
