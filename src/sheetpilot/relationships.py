"""Source-evidenced joins within and across workbooks; discovery never accepts a join."""
from collections import Counter
from itertools import combinations
import unicodedata

from .mapping import identifier, source_rows
from .semantics import IDENTIFIER_FIELDS, infer_labels
from .store import Problem, uid


def _key(value):
    # Preview only: never strip punctuation, leading zeroes, or coerce text identifiers to numbers.
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _column_values(rows, column):
    return [identifier(r["values"][column]["value"]) for r in rows
            if r["values"][column]["data_type"] not in {"f", "e"}
            and identifier(r["values"][column]["value"])]


def candidates(store, workspace):
    tables = [t for t in store.list(workspace, "table") if t["status"] != "ignored"]
    if len(tables) > 100:
        raise Problem("Relationship discovery supports up to 100 active tables. Exclude unrelated regions first.")
    columns, notes = {}, []
    for table in tables:
        inferred, _, _ = infer_labels(table["columns"])
        # An explicit mapping/custom exclusion overrides label hints on confirmed tables.
        fields = table["fields"] if table["status"] == "confirmed" else {**inferred, **table["fields"]}
        rows = source_rows(store, workspace, table)
        columns[table["id"]] = {field: (col, _column_values(rows, col)) for col, field in fields.items()
                                  if field in IDENTIFIER_FIELDS}
        if not columns[table["id"]]:
            notes.append(f"{table['sheet']} {table['ref']}: no mapped or recognizable business identifier. Map an ID column first.")
    proposals, compared = [], 0
    for left, right in combinations(tables, 2):
        # Avoid proposing a self-join between overlapping regions on the same worksheet.
        if left["workbook_id"] == right["workbook_id"] and left["sheet"] == right["sheet"]:
            from openpyxl.utils import range_boundaries
            a,b,c,d = range_boundaries(left["ref"]); e,f,g,h = range_boundaries(right["ref"])
            if max(a,e) <= min(c,g) and max(b,f) <= min(d,h): continue
        for field in sorted(columns[left["id"]].keys() & columns[right["id"]].keys()):
            compared += 1
            lc, lv = columns[left["id"]][field]; rc, rv = columns[right["id"]][field]
            ls, rs = set(lv), set(rv)
            exact = ls & rs
            mode, overlap = "exact", exact
            if not exact:
                overlap = {_key(v) for v in ls} & {_key(v) for v in rs}
                mode = "normalized-preview"
            if not overlap:
                notes.append(f"{left['sheet']} ↔ {right['sheet']} ({field}): no shared values. Check the ID meanings, source ranges, and formatting.")
                continue
            if mode == "exact":
                left_counter, right_counter = Counter(lv), Counter(rv)
            else:
                left_counter, right_counter = Counter(map(_key, lv)), Counter(map(_key, rv))
            ld, rd = len(left_counter), len(right_counter)
            left_unique = all(v == 1 for v in left_counter.values())
            right_unique = all(v == 1 for v in right_counter.values())
            cardinality = ("one-to-one" if left_unique and right_unique else "one-to-many" if left_unique
                           else "many-to-one" if right_unique else "many-to-many")
            count = len(overlap)
            coverage = count / max(1, min(ld, rd))
            reviewed = all(t["status"] == "confirmed" for t in (left,right))
            mapped = left["fields"].get(lc) == right["fields"].get(rc) == field
            blockers = []
            if not reviewed or not mapped: blockers.append("Confirm both source mappings with these identifier columns first.")
            if mode != "exact": blockers.append("Only formatting-normalized matches were found. Preview only; review source IDs before an operational join.")
            strong = mode == "exact" and coverage >= .8 and count >= 2 and cardinality != "many-to-many"
            proposals.append(dict(left_table=left["id"], right_table=right["id"], field=field,
                left_column=lc, right_column=rc, overlap_count=count, left_distinct=ld, right_distinct=rd,
                left_rows=len(lv), right_rows=len(rv), left_duplicate_keys=sum(n>1 for n in left_counter.values()),
                right_duplicate_keys=sum(n>1 for n in right_counter.values()),
                left_unmatched=ld-count, right_unmatched=rd-count, left_coverage=round(count/max(1,ld),3),
                right_coverage=round(count/max(1,rd),3), coverage=round(coverage,3), cardinality=cardinality,
                match_mode=mode, matching_examples=sorted(overlap)[:5], strength="strong" if strong else "weak",
                revisions=[left["revision"],right["revision"]], status="proposed", blockers=blockers,
                evidence=f"{count} shared {field} values; {coverage:.0%} coverage of the smaller set. "
                         f"{cardinality}; {ld-count} left and {rd-count} right unmatched IDs. "
                         + ("Formatting-normalized preview, not an operational join." if mode != "exact" else "Exact source matches.")))
    return proposals, {"eligible_tables": len(tables), "compared_identifier_pairs": compared,
        "proposals": len(proposals), "notes": notes[:40],
        "message": "Review proposed links; mapping confirmation is required before accepting." if proposals else
                   "No shared business identifiers found. Review source mappings and identifier values; same-workbook sheets are supported."}


def discover(store, workspace):
    store.workspace(workspace)
    proposals, report = candidates(store, workspace)
    with store.connection(immediate=True) as con:
        existing = store.list(workspace, "relationship", con)
        tables = {t["id"]: t for t in store.list(workspace, "table", con)}
        touched = set()
        for proposal in proposals:
            if proposal["revisions"] != [tables[proposal[k]]["revision"] for k in ("left_table", "right_table")]:
                raise Problem("Mappings changed while discovering relationships; retry.", 409)
            old = next((r for r in existing if all(r.get(k) == proposal[k] for k in ("left_table","right_table","field"))), None)
            same = old and old["revisions"] == proposal["revisions"] and old.get("match_mode","exact") == proposal["match_mode"]
            proposal.update(id=old["id"] if old else uid(), status=old["status"] if same else "proposed")
            touched.add(proposal["id"])
            store.put(workspace, "relationship", proposal, con)
        for old in existing:
            if old["id"] not in touched and old["status"] != "stale":
                old["status"] = "stale"; store.put(workspace,"relationship",old,con)
        prior = store.list(workspace,"relationship_report",con)
        store.put(workspace,"relationship_report",report | {"id": prior[0]["id"] if prior else uid()},con)
        store.event(workspace, "relationships.discovered", f"Proposed {len(proposals)} evidence-based relationships.",report,con)
    return proposals
