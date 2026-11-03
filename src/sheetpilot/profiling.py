"""Bounded, row-aligned source evidence for semantic proposals."""
from collections import Counter
from decimal import Decimal, InvalidOperation
from openpyxl.utils import range_boundaries

from .ingestion import columns_for
from .semantics import currency_hint, infer_labels


def table_profile(store, workspace, table, header_row=None):
    from .mapping import source_rows
    workbook = store.get(workspace, "workbook", table["workbook_id"])
    header = table["header_row"] if header_row is None else header_row
    columns = columns_for(workbook["report"], table["sheet"], table["ref"], header)
    view = table | {"header_row": header, "columns": columns}
    rows = source_rows(store, workspace, view)
    # Evenly spaced rows expose patterns beyond the first few records, without sending the workbook.
    indexes = sorted({round(i * (len(rows) - 1) / 7) for i in range(8)}) if rows else []
    sample = [rows[i] for i in indexes]
    for col in columns:
        values = [r["values"][str(col["index"])] for r in rows]
        data = [v["value"] for v in values if v["value"] is not None]
        kinds = Counter(v["data_type"] for v in values if v["value"] is not None)
        col["profile"] = {"nonempty": len(data), "missing": len(values) - len(data),
                          "distinct": len({str(v) for v in data}), "types": dict(kinds),
                          "formula_count": kinds.get("f", 0), "error_count": kinds.get("e", 0)}
        col["samples"] = list(dict.fromkeys(str(r["values"][str(col["index"])]["value"])[:120]
                                          for r in sample if r["values"][str(col["index"])]["value"] is not None))[:5]
    sheet = next(s for s in workbook["report"]["worksheets"] if s["title"] == table["sheet"])
    region = next((r for r in sheet["tables"] if r["ref"] == table["ref"]), {})
    candidates = {header, *[h["row"] for h in region.get("header_candidates", [])[:3]]}
    _, r1, _, r2 = range_boundaries(table["ref"])
    candidates = sorted(h for h in candidates if r1 <= h < r2)
    headers = [{"row": h, "labels": [c["label"][:100] for c in columns_for(workbook["report"], table["sheet"], table["ref"], h)]}
               for h in candidates]
    fields, entity, _ = infer_labels(columns)
    return {"table_id": table["id"], "file": workbook["name"], "sheet": table["sheet"], "ref": table["ref"],
            "header_row": header, "header_candidates": headers, "row_count": len(rows), "columns": columns,
            "sample_rows": [{"row": r["row"], "values": {c: str(v["value"])[:120] if v["value"] is not None else None
                for c, v in r["values"].items()}, "formulas_or_errors": [c for c, v in r["values"].items() if v["data_type"] in {"f", "e"}]}
                for r in sample],
            "label_hints": {"fields": fields, "entity": entity, "currency": currency_hint(columns)},
            "warnings": table.get("structure_warnings", [])}


def arithmetic_evidence(profile):
    """Compare selling-price candidates with observed line totals, without inventing a mapping."""
    fields = profile["label_hints"]["fields"]
    find = lambda field: next((c for c, f in fields.items() if f == field), None)
    qty, total = find("quantity"), find("revenue")
    if not qty or not total:
        return []
    evidence = []
    for field in ("unit_price", "list_unit_price"):
        price = find(field)
        if not price: continue
        checked = matched = 0
        for row in profile["sample_rows"]:
            if {qty, total, price} & set(row["formulas_or_errors"]): continue
            try:
                q, p, amount = (Decimal(row["values"][c]) for c in (qty, price, total))
                if not all(n.is_finite() for n in (q, p, amount)): continue
                if any(n.copy_abs() > Decimal("1000000000") for n in (q,p,amount)): continue
                checked += 1
                matched += abs(q * p - amount) <= Decimal("0.02")
            except (InvalidOperation, TypeError, ValueError): continue
        if checked:
            evidence.append(f"Observed quantity column {qty} × {field} column {price} matches line total column {total} in {matched}/{checked} sampled rows (0.02 tolerance).")
    return evidence
