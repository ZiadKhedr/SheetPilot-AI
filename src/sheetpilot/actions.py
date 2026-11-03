"""Human-gated, idempotent purchase-order generation; originals are immutable."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from .analytics import inventory_tool, money, quoted_cost, records
from .ingestion import digest
from .store import Problem, now, uid


def fingerprint(store, workspace, con=None):
    value = {
        "workbooks": sorted((w["id"], w["sha256"]) for w in store.list(workspace, "workbook", con)),
        "tables": sorted((t["id"], t["revision"], t["status"]) for t in store.list(workspace, "table", con)),
        "relationships": sorted((r["id"], r["status"], r["revisions"]) for r in store.list(workspace, "relationship", con)),
        "demand_policy": [(p["id"],p["revision"],p["enabled"]) for p in store.list(workspace,"demand_policy",con)],
    }
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class ProcurementBlocked(Problem):
    """A recoverable business prerequisite; never a provider failure."""
    def __init__(self, readiness):
        self.readiness = readiness
        super().__init__("Cannot safely draft: " + " ".join(b["message"] for b in readiness["blockers"]))


def procurement_readiness(store, workspace, product_ids=None):
    store.workspace(workspace)
    inventory = inventory_tool(store, workspace)
    stock = [r for r in inventory if r["low_stock"]]
    if product_ids:
        unknown = set(product_ids) - {r["product_id"] for r in stock}
        if unknown:
            raise Problem("Requested products are not in the validated low-stock list.")
        stock = [r for r in stock if r["product_id"] in product_ids]
    suppliers = [r for r in records(store, workspace) if r["entity"] == "suppliers"]
    tables = {t["id"]: t for t in store.list(workspace, "table")}
    links = []
    for relation in store.list(workspace, "relationship"):
        left, right = tables.get(relation["left_table"]), tables.get(relation["right_table"])
        if (relation["status"] == "confirmed" and relation["field"] == "product_id" and left and right
                and relation.get("match_mode", "exact") == "exact"
                and left["status"] == right["status"] == "confirmed"
                and relation["revisions"] == [left["revision"], right["revision"]]):
            links.append(relation)
    lines = []
    blockers = [{"code": "reorder_threshold_missing", "product_id": r["product_id"],
        "message": r["product_id"] + ": review a sales-demand policy with sufficient dated history, or map a source reorder point.",
        "next_step": "review_data", "inventory_table_id": r["source"]["table_id"]}
        for r in inventory if not r["replenishment_configured"] and not product_ids]
    for item in stock:
        def block(code, message):
            blockers.append({"code": code, "product_id": item["product_id"],
                "message": item["product_id"] + ": " + message,
                "next_step": "review_relationships" if code == "relationship_review" else "review_data",
                "inventory_table_id": item["source"]["table_id"]})
        candidates = []
        product_quotes = [r for r in suppliers if r["data"]["product_id"] == item["product_id"]]
        matching_quotes = [r for r in product_quotes if not item.get("supplier_id")
                           or r["data"]["supplier_id"] == item["supplier_id"]]
        if not product_quotes:
            block("missing_supplier_quote", "no validated supplier quote is available. Review the supplier mapping and data.")
            continue
        if not matching_quotes:
            block("supplier_mismatch", "the inventory supplier ID does not match the supplier quote. Review both source mappings.")
            continue
        for record in matching_quotes:
            supplier = record["data"]
            pair = {item["source"]["table_id"], record["source"]["table_id"]}
            linked = any({r["left_table"], r["right_table"]} == pair for r in links)
            if (linked and supplier["product_id"] == item["product_id"]
                    and (not item.get("supplier_id") or supplier["supplier_id"] == item["supplier_id"])):
                candidates.append(record)
        if not candidates:
            block("relationship_review", "supplier quote exists, but the inventory-to-suppliers product relationship must be reviewed and confirmed.")
            continue
        if len(candidates) != 1:
            block("ambiguous_supplier_quote", "multiple reviewed supplier quotes match. Resolve the ambiguous quotes before drafting.")
            continue
        record = candidates[0]
        supplier = record["data"]
        if not item.get("currency") or item["currency"] != supplier.get("currency"):
            block("currency_mismatch", "stock and supplier currencies must be explicit and match. Review their mappings and source values.")
            continue
        quantity = Decimal(item["suggested_quantity"])
        cost = Decimal(supplier["unit_cost"])
        lines.append(dict(product_id=item["product_id"], product_name=item.get("product_name") or item["product_id"],
            supplier_id=supplier["supplier_id"], supplier_name=supplier["supplier_name"], quantity=str(quantity),
            unit_cost=quoted_cost(cost), line_total=money(quantity * cost), currency=item["currency"],
            stock_quantity=item["stock_quantity"], target_stock=item["target_stock"],
            sources=[item["source"], record["source"]]))
        if item.get("planning"):
            lines[-1]["planning"]=item["planning"]
            lines[-1]["sources"].extend(item["planning"]["evidence"]["sales_examples"])
    return {"ready": bool(stock) and not blockers, "low_stock_count": len(stock),
            "ready_count": len(lines), "blockers": blockers,
            "lines": sorted(lines, key=lambda l: (l["supplier_id"], l["product_id"]))}


def draft_lines(store, workspace, product_ids=None):
    readiness = procurement_readiness(store, workspace, product_ids)
    if readiness["blockers"]:
        raise ProcurementBlocked(readiness)
    if not readiness["low_stock_count"]:
        raise Problem("No validated products currently need replenishment.")
    return readiness["lines"]


def order_overlap(actions, lines, snapshot, *, skip=None):
    def stock_rows(items):
        return {(line["sources"][0]["workbook_id"], line["sources"][0]["sheet"],
                 line["sources"][0]["row"], line["product_id"]) for line in items}
    requested = stock_rows(lines)
    for other in actions:
        if other["id"] == skip:
            continue
        if other["status"] == "executed" or (other["status"] == "pending" and other["snapshot"] == snapshot):
            if requested & stock_rows(other["lines"]):
                return (f"Purchase-order proposal {other['id'][:8]} ({other['status']}) already covers "
                        "one or more of these inventory rows. Review that proposal before ordering again.")


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
        actions = store.list(workspace, "action", con)
        existing = next((a for a in actions if a["idempotency_key"] == key), None)
        if existing:
            return existing
        overlap = order_overlap(actions, lines, snapshot)
        if overlap:
            raise Problem(overlap, 409)
        action = store.put(workspace, "action", dict(
            id=uid(), type="purchase_order", title=f"Replenish {len(lines)} low-stock products", status="pending",
            justification="Validated on-hand quantity is below the reviewed reorder threshold. Restore to target stock; purchase orders do not alter on-hand inventory.",
            lines=lines, totals=[{"currency": c, "amount": money(v)} for c,v in sorted(totals.items())],
            source_versions=[{"workbook_id": w["id"], "name": w["name"], "sha256": w["sha256"]}
                             for w in store.list(workspace, "workbook", con)],
            snapshot=snapshot, product_ids=product_ids or [], idempotency_key=key,
            validation=["Reviewed mappings", "Confirmed product relationships", "Unambiguous supplier quote",
                        "Matching explicit currency", "Deterministic quantities and Decimal money"] +
                       (["Human-reviewed sales-demand policy and stock snapshot assumptions"] if any(l.get("planning") for l in lines) else []),
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
    for line in action["lines"]:
        if line.get("planning"):
            meta.append([safe_cell("Demand basis: "+line["product_id"]),json.dumps(line["planning"],ensure_ascii=False,sort_keys=True)])
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
                error = "Source files, mappings, relationships, or planning policy changed. Regenerate and review the proposal."
            else:
                # Older installations could create overlapping pending proposals.
                # The first approved one wins; subsequent executions must conflict.
                executed = [a for a in store.list(workspace, "action", con) if a["status"] == "executed"]
                error = order_overlap(executed, action["lines"], action["snapshot"], skip=identifier)
                if not error:
                    try:
                        if draft_lines(store, workspace, action["product_ids"]) != action["lines"]:
                            error = "The proposal differs from the current validated calculations."
                    except Problem as exc:
                        error = f"The proposal no longer passes validation. {exc}"
            if error:
                action.update(status="conflicted", validation=action["validation"] + [error])
                store.put(workspace, "action", action, con)
                store.event(workspace, "action.conflicted", error, {"action_id": identifier}, con)
            else:
                action.update(reviewed_at=now(), approved_by=actor)
                store.event(workspace, "action.approved", "Operator approved the validated purchase-order proposal.",
                            {"action_id": identifier, "actor": actor, "snapshot": action["snapshot"]}, con)
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
