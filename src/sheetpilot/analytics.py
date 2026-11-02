"""Deterministic normalization and calculations; no LLM arithmetic."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from openpyxl.utils import get_column_letter

from .mapping import identifier, source_rows
from .store import Problem, uid


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


def materialize(store, workspace):
    records, issues = [], []
    for table in store.list(workspace, "table"):
        if table["status"] != "confirmed":
            continue
        seen = set()
        for raw in source_rows(store, workspace, table):
            source = {"workbook_id": table["workbook_id"], "table_id": table["id"],
                      "sheet": table["sheet"], "row": raw["row"], "ref": table["ref"],
                      "cells": {field: get_column_letter(int(col)) + str(raw["row"])
                                for col, field in table["fields"].items() if field != "ignore"}}
            signature = json.dumps([(c, v["data_type"], v["value"]) for c, v in raw["values"].items()],
                                   ensure_ascii=False, sort_keys=True)
            if signature in seen:
                issues.append(source | {"severity": "warning", "code": "duplicate", "message": "Exact duplicate excluded from derived totals."})
                continue
            seen.add(signature)
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
                row["product_id"] = identifier(row.get("product_id"))
                if not row["product_id"]:
                    raise ValueError("product_id is missing")
                row["currency"] = identifier(row.get("currency")).upper() or None
                if row["currency"] is not None and (len(row["currency"]) != 3 or not row["currency"].isalpha()):
                    raise ValueError("currency must be a three-letter code")
                entity = table["entity"]
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
                    for field in ["stock_quantity", "reorder_point"]:
                        row[field] = str(decimal_value(row.get(field), field))
                    target = decimal_value(row.get("target_stock", Decimal(row["reorder_point"]) * 2), "target_stock")
                    if target < Decimal(row["reorder_point"]):
                        raise ValueError("target_stock is below reorder_point")
                    row["target_stock"] = str(target)
                    row["supplier_id"] = identifier(row.get("supplier_id"))
                elif entity == "suppliers":
                    row["supplier_id"] = identifier(row.get("supplier_id"))
                    if not row["supplier_id"] or not identifier(row.get("supplier_name")):
                        raise ValueError("Supplier identifier or name is missing")
                    row["unit_cost"] = money(decimal_value(row.get("unit_cost"), "unit_cost"))
                else:
                    continue
                row["custom_fields"] = {
                    col + ":" + next((str(c["label"]) for c in table["columns"] if str(c["index"]) == col), ""): cell["value"]
                    for col, cell in raw["values"].items() if col not in table["fields"]}
                records.append(dict(id=uid(), entity=entity, product_id=row["product_id"], data=row, source=source))
            except ValueError as exc:
                issues.append(source | {"severity": "error", "code": "invalid", "message": str(exc) + "; excluded from derived totals."})
    # Conflicting inventory identities must never result in duplicate replenishment.
    groups = defaultdict(list)
    for record in records:
        if record["entity"] == "inventory":
            groups[record["product_id"]].append(record)
    conflicting = {key for key, rows in groups.items() if len(rows) > 1}
    for record in records[:]:
        if record["entity"] == "inventory" and record["product_id"] in conflicting:
            issues.append(record["source"] | {"severity": "error", "code": "conflict",
                "message": "Multiple inventory records share this product ID; excluded until resolved."})
            records.remove(record)
    with store.connection(immediate=True) as con:
        con.execute("DELETE FROM records WHERE workspace=?", (workspace,))
        con.executemany("INSERT INTO records VALUES(?,?,?,?,?,?,?)",
            [(r["id"], workspace, r["source"]["table_id"], r["entity"], r["product_id"],
              json.dumps(r["data"], ensure_ascii=False), json.dumps(r["source"], ensure_ascii=False)) for r in records])
        old = store.list(workspace, "quality", con)
        value = {"id": old[0]["id"] if old else uid(), "issues": issues}
        store.put(workspace, "quality", value, con)
    return records, issues


def records(store, workspace):
    with store.connection() as con:
        return [{"id": r["id"], "entity": r["entity"], "product_id": r["product_id"],
                 "data": json.loads(r["data"]), "source": json.loads(r["source"])}
                for r in con.execute("SELECT * FROM records WHERE workspace=? ORDER BY rowid", (workspace,))]


def inventory_tool(store, workspace):
    result = []
    for record in records(store, workspace):
        if record["entity"] != "inventory":
            continue
        row = record["data"]
        stock, threshold, target = (Decimal(row[k]) for k in ["stock_quantity", "reorder_point", "target_stock"])
        low = stock < threshold
        result.append(row | {"low_stock": low, "suggested_quantity": str(max(Decimal(0), target-stock)) if low else "0",
                             "source": record["source"]})
    return result


def dashboard(store, workspace):
    all_records = records(store, workspace)
    sales = [r["data"] for r in all_records if r["entity"] == "sales"]
    stock = inventory_tool(store, workspace)
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
    quality = store.list(workspace, "quality")
    issues = quality[0]["issues"] if quality else []
    entities = {r["entity"] for r in all_records}
    return {
        "revenue": [{"currency": c, "amount": money(v)} for c, v in sorted(revenue_by_currency.items())],
        "units_sold": str(sum((Decimal(r["quantity"]) for r in sales), Decimal(0))) if sales else None,
        "sales_records": len(sales), "inventory_units": str(sum((Decimal(r["stock_quantity"]) for r in stock), Decimal(0))) if stock else None,
        "inventory_products": len(stock), "low_stock_count": sum(r["low_stock"] for r in stock),
        "stock": stock, "low_stock": [r for r in stock if r["low_stock"]],
        "sales_trend": [{"date": d, "currency": c, "revenue": money(v)} for (d,c),v in sorted(trend.items())],
        "top_products": top_list[:10], "quality_issues": issues,
        "warnings": ([f"{unknown_currency} sales records lack currency; excluded from monetary KPIs."] if unknown_currency else []),
        "available_entities": sorted(entities),
        "confirmed_tables": sum(t["status"] == "confirmed" for t in store.list(workspace, "table")),
        "pending_actions": sum(a["status"] == "pending" for a in store.list(workspace, "action")),
    }
