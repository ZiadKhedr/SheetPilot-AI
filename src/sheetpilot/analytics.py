"""Deterministic normalization and calculations; no LLM arithmetic."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from openpyxl.utils import get_column_letter

from .mapping import identifier, overlapping_data, source_rows
from .semantics import ENTITY_CATALOG, NUMERIC_FIELDS, currency_hint
from .store import Problem, uid
from .lifecycle import active_tables


CENT = Decimal("0.01")


def decimal_value(value, field):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} is missing or not numeric")
    try:
        text = str(value).strip()
        if "," in text:
            raise ValueError(f"{field} contains ambiguous numeric separators")
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{field} is not numeric")
    if not number.is_finite() or number < 0:
        raise ValueError(f"{field} must be a finite nonnegative number")
    if number > Decimal("1000000000"):
        raise ValueError(f"{field} exceeds the MVP numeric limit of one billion")
    return number


def money(value):
    return str(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def quoted_cost(value):
    cost = decimal_value(value, "unit_cost")
    if cost != cost.quantize(Decimal("0.000001")):
        raise ValueError("unit_cost has more than six decimal places")
    return money(cost) if cost == cost.quantize(CENT) else format(cost.quantize(Decimal("0.000001")), "f").rstrip("0")


def materialize(store, workspace, con=None):
    if con is None:
        with store.connection(immediate=True) as transaction:
            return materialize(store, workspace, transaction)
    records, issues = [], []
    for table in active_tables(store, workspace, con):
        if table["status"] != "confirmed":
            continue
        seen = {}
        for raw in source_rows(store, workspace, table, con):
            source = {"workbook_id": table["workbook_id"], "table_id": table["id"],
                      "sheet": table["sheet"], "row": raw["row"], "ref": table["ref"],
                      "cells": {field: get_column_letter(int(col)) + str(raw["row"])
                                for col, field in table["fields"].items() if field != "ignore"}}
            corrections=[cell['correction'] for cell in raw['values'].values() if 'correction' in cell]
            if corrections:source['corrections']=corrections
            signature = json.dumps([(c, v["data_type"], v["value"]) for c, v in raw["values"].items()],
                                   ensure_ascii=False, sort_keys=True)
            corrected_inventory = table['entity']=='inventory' and (bool(corrections) or seen.get(signature,False))
            if signature in seen and not corrected_inventory:
                issues.append(source | {"severity": "warning", "code": "duplicate", "message": "Exact duplicate excluded from derived totals."})
                continue
            seen[signature] = bool(corrections) or seen.get(signature,False)
            row, formula_fields = {}, []
            for col, field in table["fields"].items():
                if field == "ignore":
                    continue
                cell = raw["values"][col]
                row[field] = cell["value"]
                if cell["data_type"] in {"f", "e"}:
                    formula_fields.append(field)
            try:
                if formula_fields:
                    raise ValueError("Formula/error values need review: " + ", ".join(formula_fields))
                entity = table["entity"]
                for field in ENTITY_CATALOG.get(entity, {}).get("required", []):
                    if row.get(field) is None or identifier(row[field]) == "":
                        raise ValueError(field + " is missing")
                for field in list(row):
                    if field.endswith("_id") or field == "barcode": row[field] = identifier(row[field])
                row["product_id"] = identifier(row.get("product_id"))
                if table.get("constants", {}).get("currency"):
                    row["currency"] = table["constants"]["currency"]
                    source["constants"] = {"currency": {"value": row["currency"], "origin": "human-reviewed table setting"}}
                row["currency"] = identifier(row.get("currency")).upper() or None
                if row["currency"] is not None and (len(row["currency"]) != 3 or not row["currency"].isascii() or not row["currency"].isalpha()):
                    raise ValueError("currency must be a three-letter ASCII code")
                if entity == "sales":
                    quantity = decimal_value(row.get("quantity"), "quantity")
                    row["quantity"] = str(quantity)
                    revenue = (decimal_value(row["revenue"], "revenue") if "revenue" in row
                               else quantity * decimal_value(row.get("unit_price"), "unit_price"))
                    row["revenue"] = money(revenue)
                    if row.get("sale_date"):
                        try:
                            row["sale_date"] = date.fromisoformat(str(row["sale_date"])[:10]).isoformat()
                        except ValueError:
                            issues.append(source | {"severity": "warning", "code": "date", "message": "Invalid date; sale retained but omitted from trend."})
                            row["sale_date"] = None
                elif entity == "inventory":
                    for field in ["stock_quantity"]:
                        row[field] = str(decimal_value(row.get(field), field))
                    if row.get("reorder_point") is not None:
                        row["reorder_point"] = str(decimal_value(row["reorder_point"], "reorder_point"))
                        target = decimal_value(row.get("target_stock", Decimal(row["reorder_point"]) * 2), "target_stock")
                        if target < Decimal(row["reorder_point"]): raise ValueError("target_stock is below reorder_point")
                        row["target_stock"] = str(target)
                    else:
                        row["reorder_point"] = row["target_stock"] = None
                        issues.append(source | {"severity": "warning", "code": "reorder_missing", "message": "No source reorder threshold. Stock remains available; a confirmed sales-demand policy can supply an eligible calculated threshold."})
                    row["supplier_id"] = identifier(row.get("supplier_id"))
                elif entity == "suppliers":
                    row["supplier_id"] = identifier(row.get("supplier_id"))
                    if not row["supplier_id"] or not identifier(row.get("supplier_name")):
                        raise ValueError("Supplier identifier or name is missing")
                    row["unit_cost"] = quoted_cost(row.get("unit_cost"))
                    source["quote_precision_checked"] = True
                elif entity not in ENTITY_CATALOG or entity == "unknown":
                    continue
                # Retain richer meanings without treating order/payment totals as line revenue.
                for field in NUMERIC_FIELDS & row.keys():
                    if row[field] is not None:
                        row[field] = str(decimal_value(row[field], field))
                row["custom_fields"] = {
                    col + ":" + next((str(c["label"]) for c in table["columns"] if str(c["index"]) == col), ""): cell["value"]
                    for col, cell in raw["values"].items() if col not in table["fields"]}
                records.append(dict(id=uid(), entity=entity, product_id=row["product_id"], data=row, source=source))
            except ValueError as exc:
                issues.append(source | {"severity": "error", "code": "invalid", "message": str(exc) + "; excluded from derived totals."})
    enrich_reviewed_records(store, workspace, records, issues, con)
    # Conflicting inventory identities must never result in duplicate replenishment.
    groups = defaultdict(list)
    for record in records:
        if record["entity"] == "inventory":
            groups[record["product_id"]].append(record)
    conflicting = {key for key, rows in groups.items() if len(rows) > 1}
    valid_records = []
    for record in records:
        if record["entity"] == "inventory" and record["product_id"] in conflicting:
            issues.append(record["source"] | {"severity": "error", "code": "conflict",
                "message": "Multiple inventory records share this product ID; excluded until resolved."})
        else:
            valid_records.append(record)
    con.execute("DELETE FROM records WHERE workspace=?", (workspace,))
    con.executemany("INSERT INTO records VALUES(?,?,?,?,?,?,?)",
        ((r["id"], workspace, r["source"]["table_id"], r["entity"], r["product_id"],
          json.dumps(r["data"], ensure_ascii=False), json.dumps(r["source"], ensure_ascii=False)) for r in valid_records))
    old = store.list(workspace, "quality", con)
    value = {"id": old[0]["id"] if old else uid(), "issues": issues}
    store.put(workspace, "quality", value, con)
    return valid_records, issues


def enrich_reviewed_records(store, workspace, rows, issues, con=None):
    """Only a unique master across all reviewed exact links may enrich missing context."""
    tables = {t["id"]: t for t in active_tables(store, workspace, con)}
    by_table, joins = defaultdict(list), defaultdict(list)
    for row in rows: by_table[row["source"]["table_id"]].append(row)
    for link in store.list(workspace, "relationship", con):
        left, right = tables.get(link["left_table"]), tables.get(link["right_table"])
        if (not left or not right or link["status"] != "confirmed" or link.get("match_mode", "exact") != "exact"
            or any(t["status"] != "confirmed" for t in (left,right))
            or link["revisions"] != [left["revision"],right["revision"]]): continue
        for source, target in ((left,right),(right,left)):
            if source["entity"] == "orders" and target["entity"] == "sales" and link["field"] == "order_id":
                fields = ("sale_date", "customer_id", "currency")
            elif ((source["entity"] == "products" and target["entity"] in {"sales","inventory"})
                  or (source["entity"] == "inventory" and target["entity"] == "sales")) and link["field"] == "product_id":
                fields = ("product_name", "category", "brand", "unit_of_measure")
            else: continue
            joins[(target["id"], link["field"], fields)].append((source["id"], link["id"]))
    for (target_id, key_field, fields), sources in joins.items():
        lookup = defaultdict(list)
        for source_id, relationship_id in sources:
            for item in by_table[source_id]:
                key = identifier(item["data"].get(key_field))
                if key: lookup[key].append((item, relationship_id))
        for item in by_table[target_id]:
            matches = lookup.get(identifier(item["data"].get(key_field)), [])
            if len(matches) > 1:
                issues.append(item["source"] | {"severity": "warning", "code": "join_ambiguous", "message": "Reviewed joins have multiple matching master rows; context was not inherited."})
                continue
            if not matches: continue
            master, relationship_id = matches[0]
            inherited = []
            for field in fields:
                if item["data"].get(field) in (None, "") and master["data"].get(field) not in (None, ""):
                    value = master["data"][field]
                    if field == "sale_date":
                        try: value = date.fromisoformat(str(value)[:10]).isoformat()
                        except ValueError: continue
                    item["data"][field] = value
                    inherited.append(field)
            if inherited:
                item["source"].setdefault("joins",[]).append({"relationship_id":relationship_id, "source":master["source"], "fields":inherited})


def legacy_overlaps(store, workspace, con=None):
    """Read older workspaces safely without rewriting their operator decisions."""
    groups, excluded = defaultdict(list), {}
    for table in active_tables(store, workspace, con):
        if table["status"] != "confirmed":
            continue
        siblings = groups[(table["workbook_id"], table["sheet"])]
        for other in siblings:
            if not overlapping_data(table, other):
                continue
            if all(table.get(k) == other.get(k) for k in ("ref", "header_row", "entity", "fields", "constants")):
                excluded.setdefault(table["id"], "duplicate")
            else:
                excluded[table["id"]] = excluded[other["id"]] = "conflict"
        siblings.append(table)
    return excluded


def records(store, workspace):
    with store.connection() as con:
        con.execute("BEGIN")
        excluded = legacy_overlaps(store, workspace, con)
        live = {t['id'] for t in active_tables(store,workspace,con)}
        return [{"id": r["id"], "entity": r["entity"], "product_id": r["product_id"],
                 "data": json.loads(r["data"]), "source": json.loads(r["source"])}
                for r in con.execute("SELECT * FROM records WHERE workspace=? ORDER BY rowid", (workspace,))
                if r["table_id"] not in excluded and r['table_id'] in live]


def inventory_tool(store, workspace, *, commercial_override=None):
    from .demand import demand_analysis, policy_for
    from .commercial import context_for, term_for, apply_rules
    from .models import DemandParameters
    all_records=records(store,workspace)
    policy=policy_for(store,workspace)
    plans={r["inventory_table_id"]+":"+r["product_id"]:r for r in demand_analysis(store,workspace,all_records=all_records)["products"]} if policy and policy["enabled"] else {}
    commercial=context_for(store,workspace,all_records,commercial_override)
    supplier_plans={}
    result = []
    for record in all_records:
        if record["entity"] != "inventory":
            continue
        row = dict(record["data"])
        threshold_source="source" if row.get("reorder_point") is not None else None
        plan=plans.get(record["source"]["table_id"]+":"+record["product_id"])
        term,commercial_error=term_for(commercial,row|{'source':record['source']})
        parameters=policy.get('parameters') if policy else None
        if threshold_source is None and policy and policy['enabled'] and term:
            if policy['parameters']['as_of']!=commercial['policy']['planning_date']:
                commercial_error='Supplier planning date differs from the reviewed demand/stock snapshot date. Review both settings.'
            else:
                parameters=policy['parameters']|{'lead_time_days':term['lead_time_days']}
                lead=term['lead_time_days']
                if lead not in supplier_plans:
                    supplier_plans[lead]={p['inventory_table_id']+':'+p['product_id']:p for p in demand_analysis(store,workspace,DemandParameters(**parameters),all_records)['products']}
                plan=supplier_plans[lead].get(record['source']['table_id']+':'+record['product_id'])
        planning=None
        if threshold_source is None and plan and plan["eligible"]:
            row["reorder_point"],row["target_stock"]=plan["reorder_point"],plan["target_stock"]
            threshold_source="sales_policy"
            planning={"origin":"reviewed sales-demand policy","policy_revision":policy["revision"],"parameters":parameters,
                      "stock_snapshot_confirmed":policy["stock_snapshot_confirmed"],
                      "sales_units":plan["sales_units"],"observed_days":plan["observed_days"],"daily_sales":plan["daily_sales"],
                      "window_start":plan["window_start"],"window_end":plan["window_end"],"evidence":plan["evidence"]}
        stock = Decimal(row["stock_quantity"])
        configured = row.get("reorder_point") is not None and row.get("target_stock") is not None
        threshold, target = (Decimal(row[k]) for k in ["reorder_point", "target_stock"]) if configured else (None,None)
        low = configured and stock < threshold
        suggestion = plan["suggested_quantity"] if threshold_source=="sales_policy" else str(max(Decimal(0), target-stock)) if low else "0"
        commercial_basis=None
        if term and configured and not commercial_error:
            try:suggestion,commercial_basis=apply_rules(commercial,row|{'threshold_source':threshold_source,'source':record['source']},term)
            except Problem as exc:commercial_error=str(exc)
        result.append(row | {"low_stock": low, "suggested_quantity": suggestion,
                             "replenishment_configured": configured,
                             "threshold_source":threshold_source,"planning":planning,
                             "commercial":commercial_basis,"commercial_error":commercial_error,
                             "source": record["source"]})
    return result


def sales_metrics(sales):
    revenue_by_currency = defaultdict(Decimal)
    trend, top = {}, {}
    unknown_currency = 0
    for row in sales:
        currency = row["currency"]
        if currency:
            revenue_by_currency[currency] += Decimal(row["revenue"])
        else:
            unknown_currency += 1
        key = (row["product_id"], currency or "UNSPECIFIED")
        item = top.setdefault(key, dict(product_id=row["product_id"], name=row.get("product_name") or row["product_id"],
                                       currency=currency, units=Decimal(0), revenue=Decimal(0)))
        item["units"] += Decimal(row["quantity"])
        item["revenue"] += Decimal(row["revenue"])
        if row.get("sale_date") and currency:
            trend_key = (row["sale_date"], currency)
            trend[trend_key] = trend.get(trend_key, Decimal(0)) + Decimal(row["revenue"])
    top_list = [v | {"units": str(v["units"]), "revenue": money(v["revenue"])} for v in top.values()]
    top_list.sort(key=lambda r: Decimal(r["units"]), reverse=True)
    return {
        "revenue": [{"currency": c, "amount": money(v)} for c, v in sorted(revenue_by_currency.items())],
        "units_sold": str(sum((Decimal(r["quantity"]) for r in sales), Decimal(0))) if sales else None,
        "sales_records": len(sales),
        "sales_trend": [{"date": d, "currency": c, "revenue": money(v)} for (d,c),v in sorted(trend.items())],
        "top_products": top_list[:10],
        "warnings": [f"{unknown_currency} sales records lack currency; excluded from monetary KPIs."] if unknown_currency else [],
    }


def sales_evidence(store, workspace, scope, offset=0, limit=20, summarize=False):
    store.workspace(workspace)
    clauses = ["workspace=?", "entity='sales'"]
    params = [workspace]
    for condition, value in (("product_id=?", scope.product_id), ("json_extract(data,'$.currency')=?", scope.currency),
                             ("json_extract(data,'$.sale_date')>=?", scope.date_from),
                             ("json_extract(data,'$.sale_date')<=?", scope.date_to)):
        if value is not None:
            clauses.append(condition)
            params.append(str(value))
    with store.connection() as con:
        con.execute("BEGIN")
        excluded = legacy_overlaps(store, workspace, con)
        if excluded:
            clauses.append("table_id NOT IN (SELECT value FROM json_each(?))")
            params.append(json.dumps(list(excluded)))
        where = " AND ".join(clauses)
        total = con.execute("SELECT COUNT(*) FROM records WHERE " + where, params).fetchone()[0]
        result = {"total": total, "offset": offset, "scope": scope.model_dump(mode="json", exclude_none=True)}
        if summarize:
            sales = [json.loads(row[0]) for row in con.execute("SELECT data FROM records WHERE " + where, params)]
            result.update(sales_metrics(sales))
        result["rows"] = []
        for row in con.execute("SELECT data,source FROM records WHERE " + where + " ORDER BY rowid LIMIT ? OFFSET ?",
                               [*params, limit, offset]):
            data = json.loads(row["data"])
            result["rows"].append({field: data.get(field) for field in
                ("product_id", "product_name", "quantity", "sale_date", "revenue", "currency")} |
                {"source": json.loads(row["source"])})
    return result


def dashboard(store, workspace):
    all_records = records(store, workspace)
    sales = [r for r in all_records if r["entity"] == "sales"]
    metrics = sales_metrics([r["data"] for r in sales])
    stock = inventory_tool(store, workspace)
    if legacy_overlaps(store, workspace):
        metrics["warnings"].append("Overlapping confirmed regions were found in this older workspace. Equivalent views count once. Conflicting regions are excluded. Review these ranges in Mapping review.")
    currency_gaps = defaultdict(int)
    for record in sales:
        if not record["data"].get("currency"):
            currency_gaps[record["source"]["table_id"]] += 1
    quality = store.list(workspace, "quality")
    issues = quality[0]["issues"] if quality else []
    entities = {r["entity"] for r in all_records}
    return {
        **metrics,
        "inventory_units": str(sum((Decimal(r["stock_quantity"]) for r in stock), Decimal(0))) if stock else None,
        "inventory_products": len(stock), "low_stock_count": sum(r["low_stock"] for r in stock),
        "stock": stock, "low_stock": [r for r in stock if r["low_stock"]],
        "quality_issues": issues,
        "warnings": metrics["warnings"] +
                    ([f"{sum(not r['replenishment_configured'] for r in stock)} inventory rows need a reviewed source threshold or an eligible sales-demand policy before replenishment."]
                     if any(not r["replenishment_configured"] for r in stock) else []),
        "currency_review": [{"table_id": t["id"], "sheet": t["sheet"], "affected_rows": currency_gaps[t["id"]],
                             "header_hint": currency_hint(t["columns"])}
                            for t in store.list(workspace,"table") if t["id"] in currency_gaps],
        "available_entities": sorted(entities),
        "confirmed_tables": sum(t["status"] == "confirmed" for t in active_tables(store, workspace)),
        "pending_actions": sum(a["status"] == "pending" for a in store.list(workspace, "action")),
    }
