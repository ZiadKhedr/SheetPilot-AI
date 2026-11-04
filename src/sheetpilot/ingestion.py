from hashlib import sha256
from pathlib import Path
from itertools import islice
from openpyxl.utils import range_boundaries

from excel_intelligence import AnalysisLimits, analyze_workbook
from .store import Problem, uid


UPLOAD_LIMIT = 10 * 1024 * 1024


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def columns_for(report, sheet_name, ref, header_row):
    sheet = next((s for s in report["worksheets"] if s["title"] == sheet_name), None)
    if sheet is None:
        raise Problem("Worksheet does not exist.")
    try:
        c1, r1, c2, r2 = range_boundaries(ref)
        pc1, pr1, pc2, pr2 = range_boundaries(sheet["populated_range"] or "A1:A1")
        if not (pc1 <= c1 <= c2 <= pc2 and pr1 <= r1 <= header_row < r2 <= pr2):
            raise ValueError()
    except (ValueError, TypeError):
        raise Problem("Region and header must be inside the populated worksheet and include data rows.")
    cells = {c["coordinate"]: c for c in sheet["populated_cells"]}
    from openpyxl.utils import get_column_letter
    return [{"index": c, "label": str(cells.get(f"{get_column_letter(c)}{header_row}", {}).get("value") or ""),
             "coordinate": f"{get_column_letter(c)}{header_row}",
             "samples": list(islice((cells[key]["value"] for r in range(header_row + 1, r2 + 1)
                                     if (key := f"{get_column_letter(c)}{r}") in cells), 4))}
            for c in range(c1, c2 + 1)]


def ingest(store, workspace, filename, content, previous_id=None):
    store.workspace(workspace)
    if not filename or not filename.lower().endswith(".xlsx"):
        raise Problem("Upload an .xlsx workbook.")
    if len(content) > UPLOAD_LIMIT:
        raise Problem("Workbook exceeds the 10 MiB upload limit.", 413)
    source_hash = sha256(content).hexdigest()
    identifier = uid()
    path = store.root / "originals" / f"{identifier}.xlsx"
    try:
        path.write_bytes(content)
        try:
            report = analyze_workbook(path, AnalysisLimits(
                max_file_size_bytes=UPLOAD_LIMIT, max_cells_per_sheet=100_000,
                max_total_cells=200_000, max_sheets=30, max_populated_cells_reported=100_000)).model_dump(mode="json")
        except ValueError as exc:
            raise Problem(f"Could not inspect workbook: {exc}") from None
        clean_name = filename.replace("\\", "/").split("/")[-1][:180]
        report["file_name"] = clean_name
        tables = []
        for sheet in report["worksheets"]:
            for region in sheet["tables"]:
                header = region["header_row"]
                if header is None or header >= range_boundaries(region["ref"])[3]:
                    continue  # A header without data is still visible in Structure Explorer.
                tables.append(dict(id=uid(), workbook_id=identifier, sheet=sheet["title"], ref=region["ref"],
                    header_row=header, columns=columns_for(report, sheet["title"], region["ref"], header),
                    entity="unknown", fields={}, confidence=0.0, evidence=[], status="unreviewed",
                    origin="unmapped", revision=0, structure_warnings=region["warnings"],
                    ambiguous=region["ambiguous"]))
        with store.connection(immediate=True) as con:
            previous = store.get(workspace, 'workbook', previous_id, con) if previous_id else None
            if previous and not previous.get('active', True):
                raise Problem('Upload a new snapshot of the currently active workbook version.', 409)
            if con.execute("""SELECT 1 FROM objects WHERE workspace=? AND kind='workbook'
                               AND json_extract(payload,'$.sha256')=? LIMIT 1""", (workspace, source_hash)).fetchone():
                raise Problem("This exact workbook has already been uploaded to this workspace.", 409)
            family = previous.get('logical_id', previous['id']) if previous else identifier
            version = 1 + max((w.get('version',1) for w in store.list(workspace,'workbook',con)
                               if w.get('logical_id',w['id']) == family), default=0)
            workbook = store.put(workspace, "workbook", dict(id=identifier, name=clean_name, sha256=source_hash,
                report=report, size=len(content), active=not bool(previous), logical_id=family, version=version,
                previous_workbook_id=previous_id), con)
            if previous:
                old_tables = [t for t in store.list(workspace,'table',con) if t['workbook_id']==previous_id]
                for table in tables:
                    matches = [t for t in old_tables if t['sheet']==table['sheet'] and
                               [(c['index'],c['label']) for c in t['columns']] == [(c['index'],c['label']) for c in table['columns']]]
                    if len(matches)==1 and matches[0]['status']=='confirmed':
                        old = matches[0]
                        table.update(entity=old['entity'],fields=old['fields'],constants=old.get('constants',{}),
                                     origin='version-proposal',status='suggested',
                                     evidence=['Compatible prior mapping proposed. Review this new snapshot explicitly.'])
            for table in tables:
                store.put(workspace, "table", table, con)
            store.event(workspace, "workbook.uploaded", f"Inspected {clean_name}.",
                        dict(workbook_id=identifier, sha256=source_hash, worksheets=report["sheet_count"]), con)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return workbook
